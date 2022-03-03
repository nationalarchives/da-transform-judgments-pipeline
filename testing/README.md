# Testing

# Step Function Example Input

A test JSON input payload (with new s3 object pre-shared URLs) can be created
for the main step function by running the following script:

* [./create_preshared_url_msg.sh](./create_preshared_url_msg.sh)

Usage:

```bash
% ./create_preshared_url_msg.sh 
Usage: s3_bucket s3_object_bagit s3_object_sha [consignment_reference] [consignment_type] [number_of_retries] [presign_url_expiry_secs]
% 
```

Example:

```bash
# To output to terminal and macOS clipboard (using pbcopy):
./create_preshared_url_msg.sh \
  'aws-bucket-name' \
  'INPUT_FILE.tar.gz' \
  'INPUT_FILE.tar.gz.sha256' \
  'INPUT_FILE' \
  'judgement' \
  '0' \
  '600' \
| tee >(pbcopy)
```

Example output:

```json
{
    "consignment-reference": "INPUT_FILE",
    "s3-bagit-url": "https://aws-bucket-name.s3.region.amazonaws.com/INPUT_FILE.tar.gz?X-Amz-Alg...",
    "s3-sha-url": "https://aws-bucket-name.s3.eu-west-2.amazonaws.com/INPUT_FILE.tar.gz.sha256?X-Amz-Alg...",
    "consignment-type": "judgement",
    "number-of-retries": 0
}
```
