# Interloper Example

Here is a terraform resource setup for a simple interloper implementation.

This assumes you have an existing VPC with at least one public subnet. You can set this several ways. For example, in fish:

    set -Ux TF_VAR_vpc_id (aws ec2 describe-vpcs | jq -r .Vpcs[0].VpcId)

Then you can apply the terraform.

    cd example # this directory
    terraform init
    terraform plan
    terraform apply

Don't forget to destroy when you are done. *This is not free.*

    terraform destroy

## Invoking the Lambdas

First, you need `TASK_ID`. One option is to get it via cli:

    export TASK_ID=$(aws ecs list-tasks --cluster borderlands | jq -r .taskArns[0] | rev | cut -d"/" -f1 | rev)

## Invoking the Command Handler

``` sh
aws lambda invoke --function-name interloper-cmd \
    --cli-binary-format raw-in-base64-out \
    --payload '{
    "cluster": "borderlands",
    "task": "'$TASK_ID'",
    "cmd": "echo Tai\'Shar Manetheren"
    }' response.json
```

## Invoking the Script Handler

``` sh
aws lambda invoke --function-name interloper-script \
    --cli-binary-format raw-in-base64-out \
    --payload '{
    "cluster": "borderlands",
    "task": "'$TASK_ID'"
    }' response.json
```
