# Testing

To run tests for `tre-validate-bag`:

1. Optionally enable a Python virtual environment; e.g. if one is configured
    in the project's root directory use:

    ```bash
    . ../../../.venv/bin/activate
    ```

    > Virtual environments can be created with: `python3 -m venv .venv`

2. Ensure this Lambda Function's support libraries have been built and the
    `tmp-build-requirements.txt` file has been created, as per
    [../../README.md](../../README.md) (the push to ECR step may be optional).

3. Install any required packages:

    ```bash
    (cd ../../../lib/tre_lib && ./build.sh) && \
    pip3 uninstall --yes tre_lib && \
    (cd ../.. && ./build.sh tre-validate-bagit); \
    (cd .. && pip3 install --requirement tmp-build-requirements.txt)
    ```
    > The Docker build script (`../../build.sh`) is used here to update the
        tmp-build-requirements.txt file (we don't need the Docker image it
        builds here). For this example, any script error (e.g. not deploying
        to ECR) is ignored (hence `;` not `&&` before last command group).

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
