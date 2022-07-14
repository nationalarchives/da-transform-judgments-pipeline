# Testing

To run step `tre-bagit-checksum-validation` then `tre-files-checksum-validation`:

1. Enable a Python virtual environment; e.g. if configured in project root use:

    ```bash
    . ../../.venv/bin/activate
    ```

2. Ensure required packages are installed (e.g. `pip3 install requests`)
3. Ensure a Bagit `.tar.gz` file and a corresponding `.tar.gz.sha256` file
    has been copied to an arbitrary s3 bucket
4. Identify an arbitrary s3 bucket for the process output    
5. Using the bucket and object names above, run the following script:

    ```bash
    ./run.sh \
        "${s3_bucket_in}" \
        "${s3_key_bagit}" \
        "${s3_key_manifest}" \
        "${consignment_reference}" \
        "${consignment_type}" \
        "${number_of_retries}" \
        "${preshared_url_timeout}" \
        "${s3_bucket_out}"
    ```

To test checksum validation failure see
[../README.md#Breaking A Bagit Archive For Testing](../README.md#breaking-a-bagit-archive-for-testing)
