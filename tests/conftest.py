import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda_src"))

os.environ.setdefault("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:test-topic")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")


def cloudwatch_event(instance_id, alarm_name="ec2-remediation-dev-cpu"):
    return {
        "source": "aws.cloudwatch",
        "detail": {
            "AlarmName": alarm_name,
            "configuration": {
                "metrics": [{
                    "metricStat": {
                        "metric": {
                            "dimensions": {"InstanceId": instance_id}
                        }
                    }
                }]
            }
        }
    }


def guardduty_event(instance_id):
    return {
        "source": "aws.guardduty",
        "detail": {
            "resource": {
                "instanceDetails": {
                    "instanceId": instance_id
                }
            }
        }
    }
