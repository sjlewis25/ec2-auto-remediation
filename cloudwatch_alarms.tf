# CPU Alarm - Dev
resource "aws_cloudwatch_metric_alarm" "cpu_high_dev" {
  alarm_name          = "dev-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Average"
  threshold           = 90
  alarm_description   = "CPU usage over 90%"
  dimensions = {
    InstanceId = aws_instance.dev.id
  }
}

# Memory Alarm - Dev
resource "aws_cloudwatch_metric_alarm" "memory_high_dev" {
  alarm_name          = "dev-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "mem_used_percent"
  namespace           = "CWAgent"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Memory usage over 80%"
  dimensions = {
    InstanceId = aws_instance.dev.id
  }
}

# Disk Alarm - Dev
resource "aws_cloudwatch_metric_alarm" "disk_high_dev" {
  alarm_name          = "dev-disk-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "disk_used_percent"
  namespace           = "CWAgent"
  period              = 60
  statistic           = "Average"
  threshold           = 85
  alarm_description   = "Disk usage over 85%"
  dimensions = {
    InstanceId = aws_instance.dev.id
  }
}

# Repeat for Prod
resource "aws_cloudwatch_metric_alarm" "cpu_high_prod" {
  alarm_name          = "prod-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Average"
  threshold           = 90
  alarm_description   = "CPU usage over 90%"
  dimensions = {
    InstanceId = aws_instance.prod.id
  }
}

resource "aws_cloudwatch_metric_alarm" "memory_high_prod" {
  alarm_name          = "prod-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "mem_used_percent"
  namespace           = "CWAgent"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Memory usage over 80%"
  dimensions = {
    InstanceId = aws_instance.prod.id
  }
}

resource "aws_cloudwatch_metric_alarm" "disk_high_prod" {
  alarm_name          = "prod-disk-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "disk_used_percent"
  namespace           = "CWAgent"
  period              = 60
  statistic           = "Average"
  threshold           = 85
  alarm_description   = "Disk usage over 85%"
  dimensions = {
    InstanceId = aws_instance.prod.id
  }
}
