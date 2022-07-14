# Testing

* [Testing Code Deployed To AWS](#testing-code-deployed-to-aws)
    * [Manual Testing](#manual-testing)
    * [Automated Testing](#automated-testing)
* [Testing Code Locally](#testing-code-locally)
* [Appendices](#appendices)
    * [Creating An Example Input Message](#creating-an-example-input-message)
    * [Breaking A Bagit Archive For Testing](#breaking-a-bagit-archive-for-testing)

# Testing Code Deployed To AWS

## Manual Testing

1. Copy a Bagit `.tar.gz` file and a corresponding `.tar.gz.sha256` file to an
    arbitrary s3 location
    > To test checksum validation failure see
        [Breaking A Bagit Archive For Testing](#breaking-a-bagit-archive-for-testing)
        below
2. Generate an input JSON message for the above files; see
    [Creating An Example Input Message](#creating-an-example-input-message)
    below
3. Submit the generated JSON message to your environment's respective input
    queue (e.g. `non-prod` `dev-tre-tdr-in`)
4. Observe execution in the AWS console at `Step Functions -> State machines`
    for the environment being tested (e.g. `non-prod` `dev-tre-state-machine`)

## Automated Testing

* [tre_module_test/README.md](tre_module_test/README.md)

# Testing Code Locally

* [tre_editorial_integration/README.md](te_editorial_integration/README.md)
* [tre_bagit_then_files/README.md](te_bagit_then_files/README.md)

# Appendices

## Creating An Example Input Message

The pipeline's input is a JSON payload that includes pre-shared URLs for the
input files it will process.

To create an example JSON payload, with new temporary pre-shared URLs for the
s3 input files, run the following script with at least the s3 bucket and input
object names (Bagit `tar.gz` and `tar.gz.sha256` files) passed as arguments:

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

## Breaking A Bagit Archive For Testing

```bash
# Unpack an existing archive
tar -xvf "${bagit}.tar.gz"

# Make a "-bad" copy
cp -r "${bagit}" "${bagit}-bad"

# Break some checksum value(s); e.g.:
vi "${bagit}-bad/manifest-sha256.txt"
vi "${bagit}-bad/tagmanifest-sha256.txt"

# Create a new tar.gz archive (use COPYFILE_DISABLE=1 on macOS):
COPYFILE_DISABLE=1 tar -czvf "${bagit}-bad.tar.gz" "${bagit}-bad"

# Verify new archive:
tar -tvf "${bagit}-bad.tar.gz"

# Generate a new good main archive manifest (which can be broken, if required):
shasum -a 256 "${bagit}-bad.tar.gz" > "${bagit}-bad.tar.gz.sha256"
```
