resource "aws_sns_topic" "alerts" {
  name = "ec2-remediation-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email 
}
