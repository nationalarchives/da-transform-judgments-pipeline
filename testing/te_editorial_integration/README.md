# Testing

To run step `te-editorial-integration`:

1. Enable a Python virtual environment; e.g. if configured in project root use:

    ```bash
    . ../../.venv/bin/activate
    ```

2. Ensure required packages are installed (e.g. `pip3 install requests`)
3. Ensure the sample test data is uploaded to a specific `s3_bucket` (this is
    used to mimick the parser step's output bucket) using:

    ```bash
    ./upload_test_data_to_s3.sh "${s3_bucket}"
    ```

4. Run the following script to execute the `te-editorial-integration` step
    locally to process the test data uploaded in step 3 above (ensure the same
    value is used for the `s3_bucket` variable):

    ```bash
    s3_bucket=
    consignment_reference='ABC-123'
    consignment_type='judgment'
    number_of_retries='0'
    preshared_url_timeout='60'
    ./run.sh \
        "${s3_bucket}" \
        "${consignment_reference}" \
        "${consignment_type}" \
        "${number_of_retries}" \
        "${preshared_url_timeout}"
    ```

The output includes the s3 pre-shared URL that can be used to download the
generated `tar.gz` package.
