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
