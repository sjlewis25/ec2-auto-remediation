variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "alert_email" {
  description = "Email to receive alert notifications"
  type        = string
}

variable "cpu_threshold" {
  description = "CPU utilization % that triggers remediation"
  type        = number
  default     = 90
}

variable "memory_threshold" {
  description = "Memory utilization % that triggers remediation"
  type        = number
  default     = 80
}

variable "disk_threshold" {
  description = "Disk utilization % that triggers remediation"
  type        = number
  default     = 85
}
