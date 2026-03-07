data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda_src/remediation.py"
  output_path = "${path.module}/lambda_src/remediation.zip"
}

resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/ec2-auto-remediation"
  retention_in_days = 30
}

resource "aws_sqs_queue" "lambda_dlq" {
  name = "ec2-remediation-dlq"
}

resource "aws_iam_role" "lambda_exec" {
  name = "ec2-remediation-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  role = aws_iam_role.lambda_exec.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:StopInstances",
          "ec2:RebootInstances",
          "ec2:DescribeInstances",
        ]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["sns:Publish"]
        Resource = aws_sns_topic.alerts.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "${aws_cloudwatch_log_group.lambda_logs.arn}:*"
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:SendMessage"]
        Resource = aws_sqs_queue.lambda_dlq.arn
      },
    ]
  })
}

resource "aws_lambda_function" "remediation" {
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  function_name    = "ec2-auto-remediation"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "remediation.lambda_handler"
  runtime          = "python3.11"
  timeout          = 30

  environment {
    variables = {
      SNS_TOPIC_ARN = aws_sns_topic.alerts.arn
    }
  }

  dead_letter_config {
    target_arn = aws_sqs_queue.lambda_dlq.arn
  }

  depends_on = [aws_cloudwatch_log_group.lambda_logs]
}
