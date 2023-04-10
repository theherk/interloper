data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "lambda" {
  statement {
    actions   = ["ecs:ExecuteCommand"]
    resources = ["*"]
  }

  statement {
    actions   = ["sts:*"]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "lambda" {
  name_prefix = "interloper"
  policy      = data.aws_iam_policy_document.lambda.json
}

resource "aws_iam_role" "lambda" {
  name_prefix        = "interloper"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "lambda" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.lambda.arn
}

data "aws_iam_policy" "managed_lambda_vpc" {
  arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy_attachment" "managed_lambda_vpc" {
  role       = aws_iam_role.lambda.name
  policy_arn = data.aws_iam_policy.managed_lambda_vpc.arn
}

resource "aws_lambda_function" "cmd" {
  description      = "Interloper example lambda to run commands."
  filename         = "${path.module}/dist/lambda.zip"
  function_name    = "interloper-cmd"
  handler          = "example.cmd_handler"
  memory_size      = 256
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.9"
  source_code_hash = filebase64sha256("${path.module}/dist/lambda.zip")
  timeout          = 10
}

resource "aws_lambda_function" "script" {
  description      = "Interloper example lambda to run interloper.sh script."
  filename         = "${path.module}/dist/lambda.zip"
  function_name    = "interloper-script"
  handler          = "example.script_handler"
  memory_size      = 256
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.9"
  source_code_hash = filebase64sha256("${path.module}/dist/lambda.zip")
  timeout          = 60
}
