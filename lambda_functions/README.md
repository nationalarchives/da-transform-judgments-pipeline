# lambda_functions

## Building

At the time of writing, these steps apply to:

* [./te-bagit-checksum-validation](./te-bagit-checksum-validation)
* [./te-files-checksum-validation](./te-files-checksum-validation)

Pre-requisistes:

* Ensure `aws` CLI access to the target environment is configured

Steps:

1. If a Python virtual environment does not exist, create one (this could be
  done from the project's root directory):

```
python3 -m venv .venv
```

2. Activate the Python virtual environment:

```
# e.g. for above virtual environment name:
. .venv/bin/activate
```

3. Change into the Lambda function's directory (e.g.
  [./te-bagit-checksum-validation](./te-bagit-checksum-validation))

4. Ensure the versions numbers are correct in the following files:

* For the Docker image: `vars.sh`
* For the support library: [`../s3_lib/version.sh`](../s3_lib/version.sh)

5. To build and package into a local Docker image run the following:

* `./build.sh`

6. If the AWS ECR repository is not already created, create it by running:

```
. ./vars.sh
ecr_repository_name="lambda_functions/${docker_image_name}"
printf 'Creating ECR repository "%s"\n' "${ecr_repository_name}"

aws ecr create-repository \
    --repository-name "${ecr_repository_name}" \
    --image-scanning-configuration \
    scanOnPush=true
```

7. Obtain the target ECR `repository_uri` from either:

* The output of the above step
* The following command:

```
repository_uri=$(aws ecr \
  describe-repositories \
  --repository-names "${ecr_repository_name}" | \
    python3 -c "import json,sys;print(json.load(sys.stdin)['repositories'][0]['repositoryUri'])"
)
```

8. Create local image tags by running the following:

```
./docker_tag.sh "${repository_uri}"
```

9. Login to ECR with:

```
aws ecr \
  get-login-password | docker login \
    --username AWS \
    --password-stdin \
    "${repository_uri}"
```

10. Push the tagged images

```
./docker_push.sh "${repository_uri}"
```
