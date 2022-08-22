To generate a sample input message and run the step function trigger locally
to then run the Step Function in AWS:

```
state_machine_name='dev-tre-validate-bagit'

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
