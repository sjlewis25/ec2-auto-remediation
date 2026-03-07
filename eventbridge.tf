resource "aws_cloudwatch_event_rule" "alarm_trigger" {
  name        = "cloudwatch-alarm-remediation"
  description = "Trigger Lambda when a project alarm state changes to ALARM"
  event_pattern = jsonencode({
    source      = ["aws.cloudwatch"]
    detail-type = ["CloudWatch Alarm State Change"]
    detail = {
      state = {
        value = ["ALARM"]
      }
      alarmName = [{
        prefix = "ec2-remediation-"
      }]
    }
  })
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.alarm_trigger.name
  target_id = "EC2RemediationLambda"
  arn       = aws_lambda_function.remediation.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.remediation.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.alarm_trigger.arn
}

resource "aws_cloudwatch_event_rule" "guardduty_findings" {
  name        = "guardduty-threat-detection"
  description = "Trigger Lambda on high-severity GuardDuty findings"
  event_pattern = jsonencode({
    source      = ["aws.guardduty"]
    detail-type = ["GuardDuty Finding"]
    detail = {
      severity = [{ numeric = [">=", 7] }]
    }
  })
}

resource "aws_cloudwatch_event_target" "guardduty_lambda" {
  rule      = aws_cloudwatch_event_rule.guardduty_findings.name
  target_id = "EC2RemediationOnThreat"
  arn       = aws_lambda_function.remediation.arn
}

resource "aws_lambda_permission" "allow_guardduty" {
  statement_id  = "AllowGuardDutyToTriggerLambda"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.remediation.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.guardduty_findings.arn
}
