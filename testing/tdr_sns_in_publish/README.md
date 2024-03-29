Generate a sample TDR input message and publish this to the SNS input topic:

```
./run.sh "${sns_arn}" \
  "${s3_bucket_source}"
  "${s3_object_bagit}"
  "${s3_object_sha}"
  "${consignment_reference}"
  "${consignment_type}"
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
