# Testing

To run `test-bagit-to-dri sip` locally you need to follow these steps:

1.  Enable a Python virtual environment; e.g. if one is configured
    in the project's root directory use:

    ```bash
    . ../../.venv/bin/activate
    ```

    > Virtual environments can be created with: `python3 -m venv .venv`

2. Ensure this Lambda Function's support libraries have been built. A guide to this can 
   be found [here](../../lambda_functions/README.md) 

3. you can check if the required libraries are installed into your virtual environment
    using the command `pip list` you are looking for the following package : `tre-event-lib`

3. Run the the following command with the following parameters from the test directory
   (located in the same location as this readme)

    ```bash
    ./run.sh <expected_data_s3_bucket> <s3_bucket_in> <s3_bucket_out> <consignment_type> <timeout> <AWS_MANAGEMENT_PROFILE_NAME>
    
   Example Command
    
   ./run.sh dev-te-data dev-tre-common-data dev-tre-dpsg-out TDR-2022-NQ3 standard 60 tna-acc-manag-admin
    ```
