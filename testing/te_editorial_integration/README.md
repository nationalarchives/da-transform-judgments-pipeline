# Testing

To run step `te-editorial-integration`:

1. Enable a Python virtual environment; e.g. if this is configured at the
    project's root (e.g. with `python3 -m venv .venv`) use:

    ```bash
    . ../../.venv/bin/activate
    ```

2. Ensure required packages are installed (e.g. `pip3 install requests`)

3. Ensure the sample test data is uploaded to a specific `s3_bucket` (this is
    used to mimic the parser step's output bucket) using:

    ```bash
    ./upload_test_data_to_s3.sh "${s3_bucket}"
    ```

4. The following scripts execute the `te-editorial-integration` step locally
    to process the test data uploaded in step 3 above (ensure the same value
    is used for the `s3_bucket` variable).

    1. Define input argument values; for example:

        ```bash
        s3_bucket=
        s3_path_prefix='te_editorial_integration_test_data/parser_output/'
        consignment_reference='ABC-123'
        consignment_type='judgment'
        presigned_url_timeout='60'
        number_of_retries='0'
        ```

    2. To simulate triggering via the step function's Parser execution path:

        ```bash        
        ./run.sh \
            "${s3_bucket}" \
            "${s3_path_prefix}" \
            "${consignment_reference}" \
            "${consignment_type}" \
            "${number_of_retries}" \
            "${presigned_url_timeout}" \
            'function_input.json'
        ```

    3. To simulate triggering via the step function's editorial retry path:

        ```bash
        ./run.sh \
            "${s3_bucket}" \
            "${s3_path_prefix}" \
            "${consignment_reference}" \
            "${consignment_type}" \
            "${number_of_retries}" \
            "${presigned_url_timeout}" \
            'function_input_retry.json'
        ```

The output includes the s3 pre-shared URL that can be used to download the
generated `tar.gz` package.
