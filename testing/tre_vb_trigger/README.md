# Using run_batch.py

Pre-requisites:

```bash
# Setup a virtual environment
python3 -m venv .venv
. ./.venv/bin/activate

# Install 3rd party packages
pip3 install wheel
pip3 install boto3
pip3 install jsonschema

# Build and install aws_test_lib; e.g.:
( \
  cd '../../../da-transform-terraform-modules/testing/aws_test_lib' \
  && ./build.sh \
  && ./reinstall.sh \
)

# Build and install tre_event_lib; e.g.:
( \
  cd '../../../da-transform-schemas/tre_event_lib' \
  && ./build.sh \
  && pip3 --require-virtualenv install "$(find ./dist -name '*.whl')"
)
```

Execution examples:

```bash
# Example test data values
aws_profile_management='test-data-account'
aws_profile_deployment='non-prod'
environment_name='development'
test_consignment_s3_bucket='test-data-account-bucket'
test_consignment_s3_bucket='test_data_bucket'
consignment_ref='FOO-2042-ABC'
test_consignment_archive_s3_path="consignments/judgment/${consignment_ref}.tar.gz"
test_consignment_checksum_s3_path="consignments/judgment/${consignment_ref}.tar.gz.sha256"
message_count=3


# To execute tre-vb-trigger handler locally:
tre_state_machine_arn="arn:aws:states:region:000000000000:stateMachine:${environment_name}-tre-validate-bagit"

export PYTHONPATH='../../lambda_functions/tre-vb-trigger'
export TRE_STATE_MACHINE_ARN="${tre_state_machine_arn}"
export TRE_CONSIGNMENT_KEY_PATH='parameters.bagit-available.reference'

AWS_PROFILE="${aws_profile_deployment}" ./run_batch.py \
  --aws_profile_management "${aws_profile_management}" \
  --aws_profile_deployment "${aws_profile_deployment}" \
  --environment_name "${environment_name}" \
  --test_consignment_s3_bucket "${test_data_bucket_name}" \
  --test_consignment_archive_s3_path "${test_consignment_archive_s3_path}" \
  --test_consignment_checksum_s3_path "${test_consignment_checksum_s3_path}" \
  --test_consignment_type "${consignment_type}" \
  --test_consignment_ref "${consignment_ref}" \
  --message_count "${message_count}"

# To execute via sns (i.e. ${environment_name}-tre-in SNS topic):
./run_batch.py \
  --aws_profile_management "${aws_profile_management}" \
  --aws_profile_deployment "${aws_profile_deployment}" \
  --environment_name "${environment_name}" \
  --test_consignment_s3_bucket "${test_data_bucket_name}" \
  --test_consignment_archive_s3_path "${test_consignment_archive_s3_path}" \
  --test_consignment_checksum_s3_path "${test_consignment_checksum_s3_path}" \
  --test_consignment_type "${consignment_type}" \
  --test_consignment_ref "${consignment_ref}" \
  --message_count "${message_count}" \
  --sns
```

# Using run.sh/run.py

To generate a sample input message and run the step function trigger locally
to then run the Step Function in AWS:

```
# e.g. dev, test, etc...
environment_name='development'
state_machine_name="${environment_name}-tre-validate-bagit"

./run.sh "${state_machine_name}" \
  "${s3_bucket_source}"
  "${s3_object_bagit}"
  "${s3_object_sha}"
  "${consignment_reference}"
  "${consignment_type}"
  "${number_of_retries}"
  "${aws_profile_source}"
  "${aws_profile_target}"
```

To remove test consignment output data from the output S3 bucket:

```
aws --profile "${aws_profile_target}" \
  s3 rm --recursive \
  "s3://${s3_bucket_target}/consignments/${consignment_type}/${consignment_reference}/"
```

> Where `s3_bucket_target` is the S3 bucket name configured against the
  triggered Step Function's Lambda Function(s)
