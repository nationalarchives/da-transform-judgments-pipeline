# Running test_local.py

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
export PYTHONPATH=../../lambda_functions/tre-forward
export TRE_OUT_TOPIC_ARN="${tre_out_sns_arn}"

AWS_PROFILE="${aws_profile_deployment}" ./test_local.py \
  --aws_profile_management "${aws_profile_management}" \
  --environment_name "${environment_name}" \
  --test_consignment_s3_bucket "${test_data_bucket_name}" \
  --test_consignment_archive_s3_path "${test_consignment_archive_s3_path}" \
  --test_consignment_checksum_s3_path "${test_consignment_checksum_s3_path}" \
  --test_consignment_type "${consignment_type}" \
  --test_consignment_ref "${consignment_ref}" \
  --message_count "${message_count}"
```

The following arguments can also be used:

* `--empty_event` : sends an empty TRE event instead of a valid one
* `--omit_message_attributes` : does not forward SNS Message Attributes
