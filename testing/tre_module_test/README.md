# Automated TRE Module Test

In the [tre_module_test](../tre_module_test/) directory:

1. Create a valid environment configuration file (e.g. `config/env_config_dev.json`):

    1. Make a copy of [example_config/example_env_config.json](example_config/example_env_config.json)
    2. Set the `name` key to your environment's name (e.g. `dev`)
    3. Set the `url` and `arn` keys for the environment

2. Create a valid test consignment config file (e.g. `config/test_consignments.json`):

    1. Make a copy of [example_config/example_test_consignments.json](example_config/example_test_consignments.json)
    2. Make sure each test scenario has the correct key values

3. To run the module test:

    1. Enable a Python virtual environment; e.g. if this is configured at
        the project's root (e.g. with `python3 -m venv .venv`) use:

        ```bash
        . ../../.venv/bin/activate
        ```

    2. Run the script with arguments for your environment:

        ```bash
        s3_test_data_bucket='dev-te-testdata'
        env_config_file='config/env_config_dev.json'
        test_consignments='config/test_consignments.json'
        aws_profile_for_data_access=''
        aws_profile_for_test_env_access=''

        python3 tre_module_test.py \
            "${s3_test_data_bucket}" \
            "${env_config_file}" \
            "${test_consignments}" \
            "${aws_profile_for_data_access}" \
            "${aws_profile_for_test_env_access}"
        ```
