# Testing

* [Creating An Example Input Message](#creating-an-example-input-message)
* [Local Testing](#local-testing)
* [Breaking A Bagit Archive For Testing](#breaking-a-bagit-archive-for-testing)

## Creating An Example Input Message

The pipeline's input is a JSON payload that includes pre-shared URLs for the
input files it will process.

To create an example JSON payload, with new temporary pre-shared URLs for the
s3 input files, run the following script with at least the s3 bucket and
object names passed as arguments:

* [./create_preshared_url_msg.sh](./create_preshared_url_msg.sh)

Argument list:

```bash
% ./create_preshared_url_msg.sh 
Usage: s3_bucket s3_object_bagit s3_object_sha [consignment_reference] [consignment_type] [number_of_retries] [presign_url_expiry_secs]
% 
```

Example input:

```bash
# To output to terminal and macOS clipboard (using pbcopy):
./create_preshared_url_msg.sh \
    "${s3_bucket}" \
    "${s3_key_bagit}" \
    "${s3_key_manifest}" \
    "${consignment_reference}" \
    "${consignment_type:-judgement}" \
    "${number_of_retries:-0}" \
    "${preshared_url_timeout:-60}"
| tee >(pbcopy)
```

Example output:

```json
{
    "consignment-reference": "...",
    "s3-bagit-url": "https://---.s3.region.amazonaws.com/---.tar.gz?X-...",
    "s3-sha-url": "https://---.s3.region.amazonaws.com/---.tar.gz.sha256?X-...",
    "consignment-type": "...",
    "number-of-retries": 0
}
```

## Local Testing

To run local code against test data in an arbitrary s3 bucket:

```bash
./test-steps-bagit-then-files.sh \
    "${s3_bucket_in}" \
    "${s3_key_bagit}" \
    "${s3_key_manifest}" \
    "${consignment_reference}" \
    "${consignment_type}" \
    "${number_of_retries}" \
    "${preshared_url_timeout}" \
    "${s3_bucket_out}"
```

## Breaking A Bagit Archive For Testing

```bash
# Unpack an existing archive
tar -xvf "${bagit}.tar.gz"

# Make a "-bad" copy
cp -r "${bagit}" "${bagit}-bad"

# Break some checksum value(s); e.g.:
vi "${bagit}-bad/manifest-sha256.txt"
vi "${bagit}-bad/tagmanifest-sha256.txt"

# Create a new tar.gz archive:
tar -czvf "${bagit}-bad.tar.gz" "${bagit}-bad"

# Verify new archive:
tar -tvf "${bagit}-bad.tar.gz"

# Generate a new good main archive manifest (which can be broken, if required):
shasum -a 256 "${bagit}-bad.tar.gz" > "${bagit}-bad.tar.gz.sha256"
```
