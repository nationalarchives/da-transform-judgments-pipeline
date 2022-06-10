# Testing

To run step `tre-step-function-trigger`:

1. Enable a Python virtual environment; e.g. if configured in project root use:

    ```bash
    . ../../.venv/bin/activate
    ```

2. Ensure required packages are installed (e.g. `pip3 install requests`)
3. Ensure a Bagit `.tar.gz` file and a corresponding `.tar.gz.sha256` file
    has been copied to an arbitrary s3 bucket
4. Identify an arbitrary s3 bucket for the process output    
5. Using the bucket and object names above plus the STATE_MACHINE_ARN - run the following script:

    ```bash
    ./run.sh \
        "${s3_bucket_in}" \
        "${s3_key_bagit}" \
        "${s3_key_manifest}" \
        "${consignment_reference}" \
        "${consignment_type}" \
        "${number_of_retries}" \
        "${preshared_url_timeout}" \
        "${s3_bucket_out}" \
        "${sfn_arn}"
    ```
