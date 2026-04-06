import json
import pytest
import boto3
from moto import mock_aws
from unittest.mock import patch
from conftest import cloudwatch_event, guardduty_event

import remediation


REGION = "us-east-1"
ACCOUNT = "123456789012"
SNS_ARN = f"arn:aws:sns:{REGION}:{ACCOUNT}:test-topic"


@pytest.fixture
def aws():
    with mock_aws():
        yield


@pytest.fixture
def ec2_instance(aws):
    ec2 = boto3.resource("ec2", region_name=REGION)
    instances = ec2.create_instances(
        ImageId="ami-00000000",
        MinCount=1,
        MaxCount=1,
        InstanceType="t3.micro",
    )
    instance = instances[0]
    instance.wait_until_running()
    return instance.id


@pytest.fixture
def sns_topic(aws):
    sns = boto3.client("sns", region_name=REGION)
    resp = sns.create_topic(Name="test-topic")
    arn = resp["TopicArn"]
    remediation.sns = boto3.client("sns", region_name=REGION)
    return arn


@pytest.fixture
def patched_clients(aws, ec2_instance, sns_topic):
    remediation.ec2 = boto3.client("ec2", region_name=REGION)
    return ec2_instance


# ─── CloudWatch alarm events ──────────────────────────────────────────────────

class TestCloudWatchAlarm:
    def test_reboots_running_instance(self, patched_clients):
        instance_id = patched_clients
        resp = remediation.lambda_handler(cloudwatch_event(instance_id), {})
        assert resp["status"] == "done"
        assert resp["action"] == "rebooted_resource_alarm"

    def test_skips_stopped_instance(self, patched_clients, aws):
        instance_id = patched_clients
        boto3.client("ec2", region_name=REGION).stop_instances(InstanceIds=[instance_id])
        boto3.client("ec2", region_name=REGION).get_waiter("instance_stopped").wait(InstanceIds=[instance_id])
        resp = remediation.lambda_handler(cloudwatch_event(instance_id), {})
        assert resp["status"] == "done"
        assert "no_action" in resp["action"]

    def test_returns_no_instance_id_when_missing(self, patched_clients):
        event = {"source": "aws.cloudwatch", "detail": {}}
        resp = remediation.lambda_handler(event, {})
        assert resp["status"] == "no_instance_id"

    def test_returns_no_instance_id_for_empty_metrics(self, patched_clients):
        event = {
            "source": "aws.cloudwatch",
            "detail": {
                "AlarmName": "test",
                "configuration": {"metrics": []}
            }
        }
        resp = remediation.lambda_handler(event, {})
        assert resp["status"] == "no_instance_id"


# ─── GuardDuty events ─────────────────────────────────────────────────────────

class TestGuardDuty:
    def test_stops_running_instance(self, patched_clients):
        instance_id = patched_clients
        resp = remediation.lambda_handler(guardduty_event(instance_id), {})
        assert resp["status"] == "done"
        assert resp["action"] == "stopped_security_threat"

    def test_skips_already_stopped_instance(self, patched_clients, aws):
        instance_id = patched_clients
        boto3.client("ec2", region_name=REGION).stop_instances(InstanceIds=[instance_id])
        boto3.client("ec2", region_name=REGION).get_waiter("instance_stopped").wait(InstanceIds=[instance_id])
        resp = remediation.lambda_handler(guardduty_event(instance_id), {})
        assert resp["status"] == "done"
        assert "no_action" in resp["action"]

    def test_skips_terminated_state(self, patched_clients, aws):
        instance_id = patched_clients
        boto3.client("ec2", region_name=REGION).terminate_instances(InstanceIds=[instance_id])
        boto3.client("ec2", region_name=REGION).get_waiter("instance_terminated").wait(InstanceIds=[instance_id])
        resp = remediation.lambda_handler(guardduty_event(instance_id), {})
        assert resp["status"] == "done"
        assert "no_action" in resp["action"]


# ─── Error handling ───────────────────────────────────────────────────────────

class TestErrorHandling:
    def test_ec2_api_failure_raises(self, patched_clients):
        """EC2 failures should propagate so Lambda retries and DLQ catches them."""
        from botocore.exceptions import ClientError
        with patch.object(remediation.ec2, "reboot_instances",
                          side_effect=ClientError({"Error": {"Code": "InvalidInstanceID", "Message": "Not found"}}, "RebootInstances")):
            with pytest.raises(ClientError):
                remediation.lambda_handler(cloudwatch_event(patched_clients), {})

    def test_sns_failure_does_not_raise(self, patched_clients):
        """SNS publish failure should be logged but not fail the remediation."""
        from botocore.exceptions import ClientError
        with patch.object(remediation.sns, "publish",
                          side_effect=ClientError({"Error": {"Code": "TopicNotFound", "Message": "Not found"}}, "Publish")):
            resp = remediation.lambda_handler(cloudwatch_event(patched_clients), {})
        assert resp["status"] == "done"

    def test_describe_instances_failure_raises(self, patched_clients):
        from botocore.exceptions import ClientError
        with patch.object(remediation.ec2, "describe_instances",
                          side_effect=ClientError({"Error": {"Code": "InvalidInstanceID", "Message": "Not found"}}, "DescribeInstances")):
            with pytest.raises(ClientError):
                remediation.lambda_handler(cloudwatch_event(patched_clients), {})


# ─── Structured logging ───────────────────────────────────────────────────────

class TestStructuredLogging:
    def test_logs_are_json(self, patched_clients, caplog):
        import logging
        with caplog.at_level(logging.INFO):
            remediation.lambda_handler(cloudwatch_event(patched_clients), {})
        json_logs = [r.message for r in caplog.records]
        for log_line in json_logs:
            parsed = json.loads(log_line)
            assert "action" in parsed

    def test_remediation_complete_logged(self, patched_clients, caplog):
        import logging
        with caplog.at_level(logging.INFO):
            remediation.lambda_handler(cloudwatch_event(patched_clients), {})
        actions = [json.loads(r.message).get("action") for r in caplog.records]
        assert "remediation_complete" in actions
