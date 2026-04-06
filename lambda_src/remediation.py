import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2 = boto3.client('ec2')
sns = boto3.client('sns')


def log(level, action, **kwargs):
    logger.log(level, json.dumps({"action": action, **kwargs}))


def get_instance_state(instance_id):
    resp = ec2.describe_instances(InstanceIds=[instance_id])
    return resp['Reservations'][0]['Instances'][0]['State']['Name']


def lambda_handler(event, context):
    log(logging.INFO, "event_received", event=event)

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
        log(logging.WARNING, "no_instance_id", event=event)
        return {"status": "no_instance_id"}

    try:
        state = get_instance_state(instance_id)
    except ClientError as e:
        log(logging.ERROR, "describe_instances_failed",
            instance_id=instance_id, error=str(e))
        raise

    log(logging.INFO, "instance_state_checked", instance_id=instance_id, state=state)

    try:
        if source == 'aws.guardduty':
            if state in ('stopped', 'stopping', 'terminated', 'shutting-down'):
                outcome = f"already_{state}_no_action"
                log(logging.INFO, "guardduty_skip", instance_id=instance_id, state=state)
            else:
                ec2.stop_instances(InstanceIds=[instance_id])
                outcome = "stopped_security_threat"
                log(logging.INFO, "instance_stopped", instance_id=instance_id, source=source)
        else:
            if state == 'running':
                ec2.reboot_instances(InstanceIds=[instance_id])
                outcome = "rebooted_resource_alarm"
                log(logging.INFO, "instance_rebooted", instance_id=instance_id, source=source)
            else:
                outcome = f"in_state_{state}_no_action"
                log(logging.INFO, "remediation_skip", instance_id=instance_id, state=state)
    except ClientError as e:
        log(logging.ERROR, "remediation_failed",
            instance_id=instance_id, source=source, error=str(e))
        raise

    try:
        sns.publish(
            TopicArn=os.environ['SNS_TOPIC_ARN'],
            Subject="EC2 Auto-Remediation Triggered",
            Message=json.dumps({
                "instance_id":  instance_id,
                "outcome":      outcome,
                "source":       source,
                "state_before": state,
            }),
        )
    except ClientError as e:
        # SNS failure should not fail the remediation — log and continue
        log(logging.ERROR, "sns_publish_failed", instance_id=instance_id, error=str(e))

    log(logging.INFO, "remediation_complete", instance_id=instance_id, outcome=outcome)
    return {"status": "done", "instance_id": instance_id, "action": outcome}
