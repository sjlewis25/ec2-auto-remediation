# EC2 Auto-Remediation with CloudWatch and GuardDuty

Automated incident response system that monitors EC2 instances for resource exhaustion and security threats, then automatically remediates by stopping affected instances and sending alerts.

## Problem Statement

Infrastructure teams face constant challenges monitoring and responding to system issues:

Manual monitoring requires 24/7 staffing. Response delays of 5-30 minutes are common, during which compromised instances continue consuming resources or pose security risks. Alert fatigue from monitoring tools leads to missed critical events.

Commercial monitoring solutions like Datadog or New Relic cost $15-30 per host monthly and still require manual remediation. Enterprise SIEM tools cost thousands monthly but lack automated response capabilities.

This project demonstrates AWS-native auto-remediation achieving sub-minute response times at near-zero cost ($2-3 monthly), eliminating manual intervention for common failure scenarios.

## Architecture
```
┌─────────────────────────────────────────────────────┐
│                    AWS Account                      │
│                                                     │
│  ┌──────────────┐                                  │
│  │ EC2 Instance │                                  │
│  │  (Dev/Prod)  │                                  │
│  └──────┬───────┘                                  │
│         │ CloudWatch Agent                          │
│         │ sends metrics                             │
│         ↓                                           │
│  ┌──────────────────┐                              │
│  │  CloudWatch      │                              │
│  │  Custom Metrics  │                              │
│  │  (CPU/Mem/Disk)  │                              │
│  └────────┬─────────┘                              │
│           │ threshold breach                        │
│           ↓                                         │
│  ┌──────────────────┐      ┌──────────────┐       │
│  │  CloudWatch      │      │  GuardDuty   │       │
│  │    Alarms        │      │  Detector    │       │
│  └────────┬─────────┘      └──────┬───────┘       │
│           │                        │               │
│           │ state change           │ finding       │
│           ↓                        ↓               │
│  ┌─────────────────────────────────────────┐      │
│  │         EventBridge Rules               │      │
│  │  - Alarm State Change                   │      │
│  │  - GuardDuty Finding                    │      │
│  └────────┬────────────────────────────────┘      │
│           │ triggers                               │
│           ↓                                        │
│  ┌──────────────────┐                             │
│  │  Lambda Function │                             │
│  │  (Remediation)   │                             │
│  └────────┬─────────┘                             │
│           │                                        │
│           ├──→ Stop EC2 Instance                  │
│           │                                        │
│           └──→ Publish to SNS                     │
│                      ↓                             │
│               ┌──────────────┐                    │
│               │  SNS Topic   │                    │
│               └──────┬───────┘                    │
│                      │                             │
│                      ↓                             │
│               Email Alert to Admin                 │
└─────────────────────────────────────────────────────┘
```

## Technology Stack

**Compute & Networking**
EC2 instances run Amazon Linux 2 with CloudWatch Agent for metrics collection. VPC provides network isolation with public subnets for internet access.

**Monitoring**
CloudWatch Alarms monitor CPU (>90%), memory (>80%), and disk usage (>85%) with 1-minute evaluation periods. GuardDuty detects security threats including cryptocurrency mining, port scanning, and suspicious API calls.

**Automation**
EventBridge routes alarm state changes and GuardDuty findings to Lambda. Lambda function executes remediation logic within 1-2 seconds of event detection.

**Notifications**
SNS topic delivers email alerts with instance ID and remediation action. Subscription confirmation required on first deployment.

**Infrastructure as Code**
Terraform provisions all resources with declarative configuration. State management enables reliable updates and teardown.

## Features

**Multi-Metric Monitoring**
Tracks CPU utilization, memory usage, and disk space across development and production instances. Custom CloudWatch metrics delivered every 60 seconds.

**Automated Remediation**
Lambda function stops instances automatically when alarms trigger or security findings detected. Eliminates need for on-call intervention during off-hours.

**Security Threat Detection**
GuardDuty continuously analyzes VPC flow logs, DNS logs, and CloudTrail events. Identifies 50+ threat types including compromised credentials and unauthorized access attempts.

**Real-Time Alerting**
SNS email notifications sent within seconds of remediation action. Messages include instance details and triggering condition.

**Cost Efficient**
Entire stack costs $2-3 monthly for small deployments. t3.micro instances eligible for free tier first 12 months. GuardDuty charges $0.50 per million events analyzed.

## Deployment

**Prerequisites**
AWS account with administrative access
AWS CLI configured with credentials
Terraform 1.0 or higher installed
Valid email address for SNS notifications

**Setup**

Clone repository:
```
git clone https://github.com/sjlewis25/ec2-auto-remediation.git
cd ec2-auto-remediation
```

Create terraform.tfvars:
```
alert_email = "your-email@example.com"
aws_region  = "us-east-1"
```

Initialize and deploy:
```
terraform init
terraform plan
terraform apply
```

Confirm SNS subscription by clicking link in email.

**Verification**

Check CloudWatch Alarms:
```
aws cloudwatch describe-alarms
```

View GuardDuty detector:
```
aws guardduty list-detectors
```

Test Lambda function:
```
aws lambda invoke --function-name ec2-auto-remediation output.json
```

**Teardown**

Remove all infrastructure:
```
terraform destroy
```

## Cost Analysis

**Monthly Operating Costs**

| Component | Configuration | Monthly Cost |
|-----------|--------------|--------------|
| EC2 (2x t3.micro) | 730 hours | $0 (free tier) or $15 |
| CloudWatch Alarms | 6 alarms | $0.60 |
| Lambda | ~100 invocations | $0 |
| SNS | ~100 notifications | $0 |
| GuardDuty | ~1M events | $0.50 |
| Total | | $1.10 - $16.10 |

**Cost Optimization**
Free tier covers first 12 months of t3.micro usage. Lambda free tier includes 1M requests monthly. CloudWatch free tier includes 10 custom metrics and 10 alarms. Disable GuardDuty in non-production to reduce costs.

## What I Learned

**Challenge: CloudWatch Agent Permissions**
EC2 instances initially failed to send custom metrics to CloudWatch. Metrics appeared in local agent logs but not in CloudWatch console. Root cause was missing IAM instance profile granting CloudWatchAgentServerPolicy. Created dedicated IAM role with proper permissions and attached to instances via instance profile. This experience reinforced the principle of least privilege - instances need explicit permission for every AWS service interaction.

**Challenge: EventBridge Pattern Matching**
First iteration used CloudWatch Alarms as direct SNS targets. This created notification spam without remediation. Refactored to use EventBridge rules filtering alarm state changes. Required understanding JSON event patterns and proper targeting of Lambda functions. Learned that event-driven architecture provides more flexibility than direct service integrations.

**Challenge: Lambda Timeout Configuration**
Initial Lambda timeout of 3 seconds caused intermittent failures during EC2 StopInstances API calls. CloudWatch Logs showed timeout errors during peak usage. Increased timeout to 30 seconds and added retry logic. Discovered that AWS API calls can take 5-15 seconds during service degradation, necessitating generous timeout values.

**Challenge: GuardDuty Finding Structure**
GuardDuty events have deeply nested JSON structure different from CloudWatch events. Lambda initially failed parsing instance IDs from GuardDuty findings. Examined CloudTrail logs to understand event schema. Implemented conditional logic handling both CloudWatch and GuardDuty event formats. Highlighted importance of testing with actual event payloads rather than assuming structure.

**Skills Developed**
Gained hands-on experience with event-driven automation patterns on AWS. Learned CloudWatch Agent configuration for custom metrics beyond default EC2 metrics. Developed proficiency in EventBridge pattern matching and rule configuration. Improved Terraform skills through modular resource organization. Deepened understanding of IAM roles, policies, and service-to-service authentication. Practiced incident response automation design applicable to production environments.

## Security Considerations

**IAM Permissions**
Lambda execution role limited to EC2 stop operations and SNS publish. CloudWatch Agent uses managed policy with read-only access to SSM for configuration. No IAM user credentials stored in code or configuration.

**Network Security**
Security group allows SSH from all sources (0.0.0.0/0) for demonstration purposes. Production deployments should restrict to specific IP ranges or bastion hosts. Instances in public subnets for simplicity - production should use private subnets with NAT gateways.

**GuardDuty Findings**
Findings indicate potential security issues requiring investigation. Auto-stopping instances provides containment but not root cause analysis. Production environments need complementary forensics capabilities.

## Future Enhancements

Add AWS Systems Manager Session Manager for SSH-less instance access. Implement graduated response - restart instance before stopping for transient issues. Create CloudWatch dashboard visualizing metrics and alarm states. Add Slack integration via SNS for team notifications. Implement DynamoDB table tracking remediation history. Configure CloudWatch Insights queries for pattern analysis. Add automated snapshots before stopping instances for forensics. Integrate with AWS Security Hub for centralized security findings.

## Production Readiness Checklist

**Implemented**
Multi-instance monitoring across environments
Automated remediation with sub-minute response time
Security threat detection with GuardDuty
Email alerting via SNS
Infrastructure as code with Terraform
IAM least privilege access

**Required for Production**
Private subnets with NAT gateway for instance isolation
Restricted security group rules for SSH access
CloudWatch Logs retention policies
Automated backup and disaster recovery procedures
Runbook documentation for manual intervention scenarios
Load testing to validate alarm thresholds
Integration with enterprise monitoring platforms
Compliance and audit logging configuration

## License

MIT License

## Author

Steve Lewis
AWS Solutions Architect Associate
AWS Cloud Practitioner
GitHub: github.com/sjlewis25
