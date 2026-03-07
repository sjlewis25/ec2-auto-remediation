locals {
  monitored_instances = {
    dev  = aws_instance.dev.id
    prod = aws_instance.prod.id
  }

  alarm_configs = {
    cpu    = { metric_name = "CPUUtilization",    namespace = "AWS/EC2", threshold = 90, description = "CPU usage over 90%" }
    memory = { metric_name = "mem_used_percent",  namespace = "CWAgent", threshold = 80, description = "Memory usage over 80%" }
    disk   = { metric_name = "disk_used_percent", namespace = "CWAgent", threshold = 85, description = "Disk usage over 85%" }
  }
}

resource "aws_cloudwatch_metric_alarm" "resource_high" {
  for_each = {
    for pair in setproduct(keys(local.monitored_instances), keys(local.alarm_configs)) :
    "${pair[0]}-${pair[1]}" => {
      env         = pair[0]
      instance_id = local.monitored_instances[pair[0]]
      cfg         = local.alarm_configs[pair[1]]
    }
  }

  alarm_name          = "ec2-remediation-${each.key}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = each.value.cfg.metric_name
  namespace           = each.value.cfg.namespace
  period              = 60
  statistic           = "Average"
  threshold           = each.value.cfg.threshold
  alarm_description   = each.value.cfg.description

  dimensions = {
    InstanceId = each.value.instance_id
  }
}
