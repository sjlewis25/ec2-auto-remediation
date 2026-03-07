import boto3
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2 = boto3.client('ec2')
sns = boto3.client('sns')


def get_instance_state(instance_id):
    resp = ec2.describe_instances(InstanceIds=[instance_id])
    return resp['Reservations'][0]['Instances'][0]['State']['Name']


def lambda_handler(event, context):
    logger.info("Received event: %s", event)
    detail = event.get('detail', {})
    source = event.get('source', '')
    instance_id = None

    # CloudWatch Alarm event
    if 'AlarmName' in detail:
        metrics = detail.get("configuration", {}).get("metrics", [])
        if metrics:
            instance_id = (
                metrics[0]
                .get("metricStat", {})
                .get("metric", {})
                .get("dimensions", {})
                .get("InstanceId")
            )

    # GuardDuty Finding event
    if 'resource' in detail and 'instanceDetails' in detail.get('resource', {}):
        instance_id = detail['resource']['instanceDetails']['instanceId']

    if not instance_id:
        logger.warning("Could not extract instance ID from event: %s", event)
        return {"status": "no_instance_id"}

    state = get_instance_state(instance_id)
    logger.info("Instance %s is currently in state: %s", instance_id, state)

    if source == 'aws.guardduty':
        # Security threat: stop immediately
        if state in ('stopped', 'stopping', 'terminated', 'shutting-down'):
            logger.info("Instance %s already %s, skipping stop", instance_id, state)
            action = f"already {state}, no action taken"
        else:
            logger.info("GuardDuty threat detected. Stopping instance %s", instance_id)
            ec2.stop_instances(InstanceIds=[instance_id])
            action = "stopped (security threat)"
    else:
        # Resource alarm: reboot first as graduated response
        if state == 'running':
            logger.info("Resource alarm triggered. Rebooting instance %s", instance_id)
            ec2.reboot_instances(InstanceIds=[instance_id])
            action = "rebooted (resource alarm)"
        else:
            logger.info("Instance %s in state %s, skipping reboot", instance_id, state)
            action = f"in state {state}, no action taken"

    sns.publish(
        TopicArn=os.environ['SNS_TOPIC_ARN'],
        Subject="EC2 Auto-Remediation Triggered",
        Message=f"Instance {instance_id}: {action}.\nTriggering source: {source}",
    )

    logger.info("Remediation complete for %s: %s", instance_id, action)
    return {"status": "done", "instance_id": instance_id, "action": action}
