# EC2 Auto-Remediation with GuardDuty and CloudWatch

## Overview
This project builds an AWS-based auto-remediation system for EC2 monitoring and threat response using Terraform. It provisions a VPC, subnets, security groups, EC2 instances, CloudWatch Alarms, SNS for notifications, Lambda for remediation, EventBridge for automation triggers, and GuardDuty for threat detection.

## What the Project Does
- Creates a secure VPC with public subnets and internet access
- Launches two Amazon Linux EC2 instances (Dev and Prod)
- Installs and configures CloudWatch Agent to collect system metrics
- Defines CloudWatch Alarms for:
  - CPU usage > 70%
  - Memory usage > 80%
  - Disk usage > 80%
- Sets up EventBridge rules to detect alarm state changes
- Triggers a Lambda function to auto-remediate by stopping the affected instance
- Subscribes an email to an SNS topic for real-time alerting
- Enables AWS GuardDuty to detect security threats
- Links GuardDuty findings to EventBridge, which also invokes the remediation Lambda

## Outcomes
- 2 EC2 instances monitored for CPU, memory, and disk usage
- 6 CloudWatch alarms auto-triggering remediation and alerts
- <1 minute response time from threshold breach to remediation
- Email alerts delivered instantly via SNS
- Automatic EC2 instance shutdown on:
  - High resource usage
  - GuardDuty security finding (e.g., crypto mining, port scan)
- Zero manual intervention required once deployed

## Technologies Used
AWS EC2, VPC, CloudWatch, Lambda, SNS, IAM, GuardDuty, EventBridge, Terraform

## Setup Instructions
1. Clone the repo
2. Configure AWS credentials
3. Run `terraform init`
4. Run `terraform apply`
5. Confirm the SNS email subscription

## Teardown
Run `terraform destroy` to remove all infrastructure

## Author
Steven Lewis
