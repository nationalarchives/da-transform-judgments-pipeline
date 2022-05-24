# Testing

To execute the parser test script:

1. Enable a Python virtual environment; e.g. if one is configured in the
    project's root directory (e.g. `python3 -m venv .venv`) run:

    ```bash
    . ../../.venv/bin/activate
    ```

2. Ensure required packages are installed (e.g. `pip3 install boto3`)

3. Identify the location of test documents in S3; e.g.:

    ```bash
    % aws s3 ls "${PARSER_TEST_S3_BUCKET}/parser/"
        PRE fail/
        PRE ok/
    %
    ```

4. Set values for the following environment variables:

    ```bash
    export PARSER_TEST_S3_BUCKET=''
    export PARSER_TEST_S3_PATH_DATA_OK='parser/ok/'
    export PARSER_TEST_S3_PATH_DATA_FAIL='parser/fail/'
    export PARSER_TEST_S3_PATH_OUTPUT='parser/output-tmp/'
    export PARSER_TEST_TESTDATA_SUFFIX='.docx'
    export PARSER_TEST_LAMBDA='test_judgment_parser'
    ```

5. Ensure your AWS CLI environment is configured to access your S3 test data
    (e.g. `export AWS_PROFILE='...'`)

6. Run the tests:

    ```bash
    python3 test_parser_lambda_fn.py
    ```

    This will exit with status 0 on success. It will fail if a document in the
    "ok" directory has a parser error, or a document in the "fail" directory
    does not have a parser error. 

Parser outputs for each test run are grouped under a timestamped directory;
for example, here are 4 test run folders:

```bash
$ aws s3 ls "${PARSER_TEST_S3_BUCKET}/parser/output-tmp/"
      PRE 2022-05-24T07:34:00.741705+00:00/
% aws s3 ls "${PARSER_TEST_S3_BUCKET}/parser/output-tmp/2022-05-24T07:34:00.741705+00:00/" 
      PRE 2022-05-24T07:34:01.792037+00:00-19972208-e54d-4595-9d7a-a6e990913833/
      PRE 2022-05-24T07:34:06.211549+00:00-cfec61f5-7e8b-478e-a693-1a7cf63f7beb/
      PRE 2022-05-24T07:34:06.848889+00:00-35902e29-5106-4827-8850-ea7bd958a949/
      PRE 2022-05-24T07:34:07.631693+00:00-222b6848-8287-4c8b-9362-24dd86dbc2fa/
      PRE 2022-05-24T07:34:08.716847+00:00-76016832-7d0c-4a6b-b233-5b19e97673f9/
      PRE 2022-05-24T07:34:09.341091+00:00-9bec390b-84a6-4cf0-9c35-723b7253fe8e/
      PRE 2022-05-24T07:34:11.263554+00:00-fe8252a5-bce4-4425-b92c-99e180babd65/
      PRE 2022-05-24T07:34:14.175297+00:00-4eff5003-c420-442f-a666-368c31c7ab0c/
% aws s3 ls "${PARSER_TEST_S3_BUCKET}/parser/output-tmp/2022-05-24T07:34:00.741705+00:00/2022-05-24T07:34:14.175297+00:00-4eff5003-c420-442f-a666-368c31c7ab0c/"
2022-05-24 08:34:15     122513 2022-05-24T07:34:14.175297+00:00-4eff5003-c420-442f-a666-368c31c7ab0c.xml
2022-05-24 08:34:16       8003 image1.png
2022-05-24 08:34:16        182 metadata.json
2022-05-24 08:34:16       1415 parser.log
%
```
