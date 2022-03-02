# Testing

To generate an example input payload:

```bash
# Mandatory inputs:
s3_bucket=
s3_object_bagit=
s3_object_sha=

# Optional inputs:
presign_url_expiry_secs=
consignment_type=
number_of_retries=

printf '{
  "consignment-reference": "%s",
  "s3-bagit-url": "%s",
  "s3-sha-url": "%s",
  "consignment-type": "%s",
  "number-of-retries": %s
}\n' \
    "TDR-2021-CF6L" \
    "$(aws s3 presign "s3://${s3_bucket}/${s3_object_bagit}" --expires-in ${presign_url_expiry_secs:-60})" \
    "$(aws s3 presign "s3://${s3_bucket}/${s3_object_sha}" --expires-in ${presign_url_expiry_secs:-60})" \
    "${consignment_type:-judgement}" \
    ${number_of_retries:-0} \
| tee >(pbcopy)
```
