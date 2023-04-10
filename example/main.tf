terraform {
  required_version = ">= 1.4"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {}

locals {
  name = "manetheren"
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}
