# Testing

To run `tre-validate-bagit` then `tre-validate-bagit-files` locally:

1. Optionally enable a Python virtual environment; e.g. if one is configured
    in the project's root directory use:

    ```bash
    . ../../.venv/bin/activate
    ```

    > Virtual environments can be created with: `python3 -m venv .venv`

2. Ensure this Lambda Function's support libraries have been built and the
    required `tmp-build-requirements.txt` files have been created; then
    install the required libraries; eg.:

    ```bash
    pip3 uninstall --yes tre_event_lib
    pip3 uninstall --yes s3_lib

    # Omit AWS region in build.sh calls to avoid ECR push. The Docker build is
    # not really needed, just the generated tmp-build-requirements.txt files:
    (cd ../../lambda_functions && ./build.sh tre-vb-validate-bagit)
    (cd ../../lambda_functions/tre-vb-validate-bagit && \
        pip3 install --requirement tmp-build-requirements.txt)

    (cd ../../lambda_functions && ./build.sh tre-vb-validate-bagit-files)
    (cd ../../lambda_functions/tre-vb-validate-bagit-files && \
        pip3 install --requirement tmp-build-requirements.txt)
    ```

4. Ensure a Bagit `.tar.gz` file and a corresponding `.tar.gz.sha256` file
    has been copied to an arbitrary s3 bucket (`"${s3_bucket_in}"`)

5. Identify an arbitrary s3 bucket for the process output (`"${s3_bucket_out}"`)

6. Using the bucket and object names above, run the following script:

    ```bash
    ./run.sh \
        "${s3_bucket_in}" \
        "${s3_key_bagit}" \
        "${s3_key_bagit_checksum}" \
        "${consignment_reference}" \
        "${consignment_type}" \
        "${number_of_retries}" \
        "${s3_bucket_out}" \
        "${aws_profile_for_s3_bucket_in}" \
        "${aws_profile_for_s3_bucket_out}"
    ```
