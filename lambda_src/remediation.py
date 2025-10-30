import boto3
import os

ec2 = boto3.client('ec2')
sns = boto3.client('sns')

def lambda_handler(event, context):
    detail = event.get('detail', {})
    instance_id = None

    # CloudWatch Alarm event
    if 'AlarmName' in detail:
        metrics = detail.get("configuration", {}).get("metrics", [])
        if metrics:
            instance_id = metrics[0].get("metricStat", {}).get("metric", {}).get("dimensions", {}).get("InstanceId")

    # GuardDuty Finding event
    if 'resource' in detail and 'instanceDetails' in detail['resource']:
        instance_id = detail['resource']['instanceDetails']['instanceId']

    if instance_id:
        ec2.stop_instances(InstanceIds=[instance_id])
        sns.publish(
            TopicArn=os.environ['SNS_TOPIC_ARN'],
            Subject="EC2 Auto-Remediation Triggered",
            Message=f"Instance {instance_id} stopped due to detected issue."
        )

    return {"status": "done"}
