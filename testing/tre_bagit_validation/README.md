To generate a sample input message and run the step function handler locally:

```
./run.sh 'dev-tre-receive-and-process-bag' \
  "${s3_bucket_source}"
  "${s3_object_bagit}"
  "${s3_object_sha}"
  "${consignment_reference}"
  "${consignment_type}"
  "${number_of_retries}"
  "${aws_profile_source}"
  "${aws_profile_target}"
```
