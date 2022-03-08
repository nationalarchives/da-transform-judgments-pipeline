# lambda_functions

## Building

Pre-requisistes:

* If the deploy to ECR option is used, the `aws` CLI must be configured and
  `${AWS_PROFILE}` must point to the correct target environment

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

3. Ensure the version numbers are correct in the following files:

* For the build function: `./${function_dir}/versions.sh`
* For the support library: [`../s3_lib/version.sh`](../s3_lib/version.sh)

4. To build:

For a local-only build (with no ECR tag and push), run the following:

* `./build.sh "${function_dir}"`

To also tag and push the local build to ECR, specify the target AWS_REGION argument:

* `./build.sh "${function_dir}" "${AWS_REGION}"`
