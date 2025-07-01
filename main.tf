terraform {
  required_providers {
    aws={
        version:"~>5.9"
    }
  }
}


resource "aws_iot_thing_type" "thing_type" {
  name = "MyThingType"
}


resource "aws_iot_thing" "thing" {
  name = "cnc_machines"
  thing_type_name = aws_iot_thing_type.thing_type.name
  attributes = {
    name = "cnc_device_script"
  }
}

resource "aws_iot_certificate" "cert" {
  active = true
}


resource "aws_iot_policy" "policy" {
  name = "cnc_policy"

  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "iot:Connect",
          "iot:Publish",
          "iot:Subscribe",
          "iot:Receive"
        ],
        "Resource": "*"
      }
    ]
  })
}

resource "aws_iot_policy_attachment" "policy_attach" {
  policy      = aws_iot_policy.policy.name
  target      = aws_iot_certificate.cert.arn
}

resource "aws_iot_thing_principal_attachment" "thing_attach" {
  thing       = aws_iot_thing.thing.name
  principal   = aws_iot_certificate.cert.arn
}


resource "aws_dynamodb_table" "dynamodb_table" {
  name           = "cnc_data"
  billing_mode   = "PROVISIONED"
  read_capacity  = 20
  write_capacity = 20
  hash_key       = "machine_id"
  range_key = "timestamp"
  
  attribute {
    name = "machine_id"
    type = "S"
  }
  attribute {
    name = "timestamp"
    type = "S"
  }

  ttl {
    attribute_name = "TimeToExist"
    enabled        = true
  }

  tags = {
    Name        = "cnc-table"
    Environment = "dev"
  }
}

resource "aws_iam_role" "lambda_exec" {
  name = "lambda_exec_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = ["sts:AssumeRole"]
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_policy" "lambda_permissions" {
  name = "lambda_exec_permissions"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "dynamodb:PutItem",
          "iotsitewise:PutAssetPropertyValue"
        ],
        Effect   = "Allow",
        Resource = "*"  # Ideally, replace * with actual ARNs
      }
    ]
  })
}



resource "aws_iam_policy" "dynamodb_access" {
  name = "dynamodb-access-policy"
  description = "Policy for DB table that stores CNC machine information"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:DeleteItem"
      ],
      Effect   = "Allow",
      Resource = aws_dynamodb_table.dynamodb_table.arn
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.dynamodb_access.arn
}

resource "aws_iam_role_policy_attachment" "lambda_iotsitewise_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_permissions.arn
}

resource "aws_lambda_function" "cnc_lambda" {
  function_name = "cnc-lambda"
  role= aws_iam_role.lambda_exec.arn
  filename = "lambda.py.zip"
  handler       = "lambda.handler"      # Match the file and function name
  runtime       = "python3.11"    

   environment {
    variables = {
      DYNAMODB_CNC_TABLE = aws_dynamodb_table.dynamodb_table.name
    }
  }  
}

resource "aws_lambda_permission" "allow_iot" {
  statement_id  = "AllowIoTInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cnc_lambda.function_name
  principal     = "iot.amazonaws.com"
  source_arn    = "arn:aws:iot:us-east-1:${data.aws_caller_identity.current.account_id}:rule/cnc_iot_rule"
}

data "aws_caller_identity" "current" {}

resource "aws_iot_topic_rule" "cnc_iot_rule" {
  name        = "cnc_iot_rule"
  enabled     = true
  sql         = "SELECT * FROM 'cnc/machine/data'"  # Match the topic you're publishing to
  sql_version = "2016-03-23"

  lambda {
    function_arn = aws_lambda_function.cnc_lambda.arn
  }

  depends_on = [
    aws_lambda_permission.allow_iot
  ]
}


