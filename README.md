# EC2 Auto-Remediation with CloudWatch and GuardDuty

Automated incident response system that monitors EC2 instances for resource exhaustion and security threats, then automatically remediates by rebooting or stopping affected instances and sending alerts.

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
│           │ threshold breach (3 consecutive mins)   │
│           ↓                                         │
│  ┌──────────────────┐      ┌──────────────┐       │
│  │  CloudWatch      │      │  GuardDuty   │       │
│  │    Alarms        │      │  Detector    │       │
│  └────────┬─────────┘      └──────┬───────┘       │
│           │                        │               │
│           │ state change           │ HIGH/CRITICAL │
│           ↓                        │ finding only  │
│  ┌─────────────────────────────────────────┐      │
│  │         EventBridge Rules               │      │
│  │  - Alarm State Change (scoped prefix)   │      │
│  │  - GuardDuty Finding (severity >= 7)    │      │
│  └────────┬────────────────────────────────┘      │
│           │ triggers                               │
│           ↓                                        │
│  ┌──────────────────┐      ┌──────────────┐      │
│  │  Lambda Function │─────→│  SQS (DLQ)   │      │
│  │  (Remediation)   │      │              │      │
│  └────────┬─────────┘      └──────────────┘      │
│           │                                        │
│           ├──→ Reboot (resource alarm)            │
│           ├──→ Stop (security threat)             │
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
CloudWatch Alarms monitor CPU (>90%), memory (>80%), and disk usage (>85%) with 3 consecutive evaluation periods required before triggering. GuardDuty detects security threats including cryptocurrency mining, port scanning, and suspicious API calls.

**Automation**
EventBridge routes alarm state changes and GuardDuty findings to Lambda. Lambda function executes remediation logic within 1-2 seconds of event detection. A SQS dead-letter queue captures any failed invocations for investigation.

**Notifications**
SNS topic delivers email alerts with instance ID and remediation action taken. Subscription confirmation required on first deployment.

**Infrastructure as Code**
Terraform provisions all resources with declarative configuration. State management enables reliable updates and teardown.

## Features

**Multi-Metric Monitoring**
Tracks CPU utilization, memory usage, and disk space across development and production instances. Custom CloudWatch metrics delivered every 60 seconds. Alarms require 3 consecutive breaches before triggering to eliminate false positives from transient spikes.

**Graduated Remediation**
Lambda applies different responses based on the trigger source. Resource alarms (CPU/memory/disk) reboot the instance first, giving it a chance to recover without data loss. GuardDuty security findings stop the instance immediately to contain the threat.

**Idempotent Execution**
Lambda checks the current instance state before acting. Stops and reboots are skipped if the instance is already stopped, stopping, or terminated, preventing errors from duplicate event deliveries.

**Scoped Event Routing**
EventBridge rules filter precisely: the CloudWatch rule matches only alarms prefixed `ec2-remediation-`, and the GuardDuty rule matches only findings with severity >= 7 (HIGH or CRITICAL). Informational findings and unrelated alarms in the account do not trigger remediation.

**Security Threat Detection**
GuardDuty continuously analyzes VPC flow logs, DNS logs, and CloudTrail events. Identifies 50+ threat types including compromised credentials and unauthorized access attempts.

**Real-Time Alerting**
SNS email notifications sent within seconds of remediation action. Messages include instance ID, action taken, and the triggering source.

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

Check dead-letter queue for any failed invocations:
```
aws sqs get-queue-attributes \
  --queue-url $(aws sqs get-queue-url --queue-name ec2-remediation-dlq --query QueueUrl --output text) \
  --attribute-names ApproximateNumberOfMessages
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
| SQS (DLQ) | minimal | $0 |
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

**Challenge: Alarm Sensitivity and False Positives**
Initial evaluation period of 1 triggered instance reboots on transient CPU spikes from normal operations like package updates. Raised to 3 consecutive evaluation periods (3 minutes) to confirm sustained resource pressure before acting. Reinforced that automated remediation requires conservative thresholds to avoid unnecessary disruption.

**Skills Developed**
Gained hands-on experience with event-driven automation patterns on AWS. Learned CloudWatch Agent configuration for custom metrics beyond default EC2 metrics. Developed proficiency in EventBridge pattern matching and rule configuration. Improved Terraform skills through for_each meta-arguments and locals for DRY configuration. Deepened understanding of IAM least-privilege scoping per resource. Practiced idempotent automation design to handle duplicate and out-of-order events.

## Security Considerations

**IAM Permissions**
Lambda execution role scoped to specific actions: EC2 stop/reboot/describe, SNS publish to the project topic only, CloudWatch Logs write to the project log group only, and SQS send to the DLQ only. CloudWatch Agent uses managed policy with read-only access to SSM for configuration. No IAM user credentials stored in code or configuration.

**Network Security**
Security group allows SSH from all sources (0.0.0.0/0) for demonstration purposes. Production deployments should restrict to specific IP ranges or bastion hosts. Instances in public subnets for simplicity - production should use private subnets with NAT gateways.

**GuardDuty Findings**
Only HIGH and CRITICAL severity findings (severity >= 7) trigger auto-remediation. Lower severity findings are logged by GuardDuty but do not cause instance stops. Auto-stopping instances provides containment but not root cause analysis. Production environments need complementary forensics capabilities.

**Event Scoping**
EventBridge rules are scoped to prevent other alarms or GuardDuty findings in the account from triggering unintended remediation. CloudWatch rule matches only alarms prefixed `ec2-remediation-`.

## Future Enhancements

Add AWS Systems Manager Session Manager for SSH-less instance access. Create CloudWatch dashboard visualizing metrics and alarm states. Add Slack integration via SNS for team notifications. Implement DynamoDB table tracking remediation history with timestamps and actions taken. Configure CloudWatch Insights queries for pattern analysis. Add automated EBS snapshots before stopping instances for forensics. Integrate with AWS Security Hub for centralized security findings. Implement second-stage stop after reboot if CloudWatch alarm re-triggers within a configurable window.

## Production Readiness Checklist

**Implemented**
- Multi-instance monitoring across environments
- Automated remediation with sub-minute response time
- Graduated response: reboot for resource alarms, stop for security threats
- Idempotent execution with instance state checks
- Security threat detection with GuardDuty (HIGH/CRITICAL only)
- Scoped EventBridge rules to prevent cross-account alarm interference
- Email alerting via SNS with action and source details
- SQS dead-letter queue for failed Lambda invocations
- CloudWatch log group with 30-day retention
- IAM least privilege scoped per resource ARN
- Infrastructure as code with Terraform

**Required for Production**
- Private subnets with NAT gateway for instance isolation
- Restricted security group rules for SSH access
- Automated backup and disaster recovery procedures
- Runbook documentation for manual intervention scenarios
- Load testing to validate alarm thresholds
- Integration with enterprise monitoring platforms
- Compliance and audit logging configuration
- Second-stage stop logic after reboot for persistent resource alarms

## License

MIT License

## Author

Steve Lewis
AWS Solutions Architect Associate
AWS Cloud Practitioner
GitHub: github.com/sjlewis25
