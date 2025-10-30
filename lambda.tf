data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_src"
  output_path = "${path.module}/lambda_src/remediation.zip"
}

resource "aws_iam_role" "lambda_exec" {
  name = "ec2-remediation-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  role = aws_iam_role.lambda_exec.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = [
        "ec2:StopInstances",
        "ec2:DescribeInstances",
        "sns:Publish",
        "logs:*"
      ],
      Resource = "*"
    }]
  })
}

resource "aws_lambda_function" "remediation" {
  filename         = data.archive_file.lambda_zip.output_path
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
}
