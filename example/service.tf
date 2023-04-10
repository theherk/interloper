resource "aws_ecs_cluster" "this" {
  name = "borderlands"
}

resource "aws_security_group" "service" {
  name_prefix = "${local.name}-svc"
  vpc_id      = var.vpc_id

  egress {
    description      = "Open egress."
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  ingress {
    description = "Get image."
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow connection to the service."
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = [for _, subnet in data.aws_subnet.this : subnet.cidr_block]
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_ecs_service" "this" {
  name                   = local.name
  cluster                = aws_ecs_cluster.this.arn
  desired_count          = 1
  enable_execute_command = true
  launch_type            = "FARGATE"
  task_definition        = aws_ecs_task_definition.this.arn

  deployment_controller {
    type = "ECS"
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.this.arn
    container_name   = local.name
    container_port   = 8080
  }

  network_configuration {
    assign_public_ip = true
    subnets          = data.aws_subnets.this.ids
    security_groups  = [aws_security_group.service.id]
  }
}

resource "aws_cloudwatch_log_group" "this" {
  name = "/ecs/${local.name}"
}

module "container" {
  source          = "cloudposse/ecs-container-definition/aws"
  version         = "0.58.2"
  container_name  = local.name
  container_image = "ealen/echo-server"

  linux_parameters = {
    capabilities       = null
    devices            = null
    initProcessEnabled = true
    maxSwap            = null
    sharedMemorySize   = null
    swappiness         = null
    tmpfs              = null
  }

  log_configuration = {
    logDriver = "awslogs"

    options = {
      "awslogs-group"         = aws_cloudwatch_log_group.this.name
      "awslogs-region"        = data.aws_region.current.name
      "awslogs-stream-prefix" = "ecs"
    }
  }

  map_environment = {
    "PORT" = 8080
  }

  port_mappings = [
    {
      containerPort = 8080
      hostPort      = 8080
      protocol      = "tcp"
    }
  ]
}

resource "aws_ecs_task_definition" "this" {
  family                   = local.name
  container_definitions    = module.container.json_map_encoded_list
  cpu                      = 256
  memory                   = 512
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]

  execution_role_arn = aws_iam_role.exec_role.arn
  task_role_arn      = aws_iam_role.task_role.arn
}

data "aws_iam_policy_document" "task_assume_role_policy_document" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

data "aws_iam_policy" "exec_policy_managed" {
  arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "exec_role" {
  name_prefix        = local.name
  assume_role_policy = data.aws_iam_policy_document.task_assume_role_policy_document.json
}

resource "aws_iam_role_policy_attachment" "exec_role_managed" {
  role       = aws_iam_role.exec_role.name
  policy_arn = data.aws_iam_policy.exec_policy_managed.arn
}

data "aws_iam_policy_document" "task_policy" {
  statement {
    actions = [
      "logs:CreateLogStream",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents"
    ]

    resources = ["${aws_cloudwatch_log_group.this.arn}:*"]
  }

  statement {
    actions = [
      "ssmmessages:CreateControlChannel",
      "ssmmessages:CreateDataChannel",
      "ssmmessages:OpenControlChannel",
      "ssmmessages:OpenDataChannel"
    ]

    resources = ["*"]
  }
}

resource "aws_iam_policy" "task_policy" {
  name_prefix = local.name
  policy      = data.aws_iam_policy_document.task_policy.json
}

resource "aws_iam_role" "task_role" {
  name_prefix        = local.name
  assume_role_policy = data.aws_iam_policy_document.task_assume_role_policy_document.json
}

resource "aws_iam_role_policy_attachment" "task_role" {
  role       = aws_iam_role.task_role.name
  policy_arn = aws_iam_policy.task_policy.arn
}
