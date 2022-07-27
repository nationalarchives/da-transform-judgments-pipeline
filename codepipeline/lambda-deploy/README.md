# Lambda Deploy

Scripts to automate Step Function Lambda Function deployment.

There are 2 parts:

1. Detecting, building and deploying new Docker image versions to ECR
2. Updating the Docker image version(s) used by Step Function Lambda Functions

# Prerequisites

## Python Libraries

To install the required libraries ([`requirements.txt`](requirements.txt)):

```bash
# Optionally setup a virtual environment (run deactivate to deactivate it)
python3 -m venv .venv
. ./.venv/bin/activate

# Install the required libraries
pip install -r codepipeline/lambda-deploy/requirements.txt
```

# Deploying new Docker images to ECR

Run the following to build and deploy to ECR any Docker images that have a
name and version (in their corresponding `version.sh` file) that is not in
ECR:

```bash
# Set for the target environment
export AWS_PROFILE=
AWS_ECR_REGION=

cd codepipeline/lambda-deploy
deploy_images_to_ecr.sh "${AWS_ECR_REGION}"
```

> Script [`deploy_images_to_ecr.sh`](deploy_images_to_ecr.sh) calls script
  [`ecr_version_filter.py`](ecr_version_filter.py).

# Updating Step-Function Lambda-Function Docker image versions

Run the following to update the Lambda Function Docker image versions for a
set of Step Functions:

```bash
# Set these for your environment
export AWS_PROFILE=
SF_TF_VAR_KEY_NAME='step-function-tfvar-version-keys-list'
TARGET_PARAMETER='target-env-tfvars'
LAMBDA_FUNCTION_DIR='../../lambda_functions'

# Get list of Step Functions to update from Parameter Store
SF_TF_VAR_KEY_LIST="$(
  aws ssm get-parameter \
    --name "${SF_TF_VAR_KEY_NAME}" \
    --with-decryption \
    --query 'Parameter.Value' \
    --output text \
)"

./update_step_functions.sh \
  "${SF_TF_VAR_KEY_LIST}" \
  "${TARGET_PARAMETER}" \
  "${LAMBDA_FUNCTION_DIR}"
```

The records in Parameter Store parameter `SF_TF_VAR_KEY_NAME` define the
Terraform variable keys used to auto update 1 or more Step-Function
Lambda-Function Docker image versions.

The following format must be used, with 1 record per line:

```
sf-version-key-name-1,sf-lambda-version-dict-name-1
sf-version-key-name-n,sf-lambda-version-dict-name-n
```

Where `sf-version-key-name` specifies a Step Function version variable name
(holding a string version value) and `sf-lambda-version-dict-name` specifies a
Step Function Lambda Function Docker image version variable (which returns a
dictionary of Lambda Function Docker image versions).
