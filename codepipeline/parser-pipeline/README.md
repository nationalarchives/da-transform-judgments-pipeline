# To Test

1. Create a temporary test variable in AWS Parameter Store:

    For example, to copy an existing parameter:

    ```bash
    source_parameter_name='source-tfvars'
    new_parameter_name="tmp-tfvars-${USER}"

    source_parameter_value="$(
    aws ssm get-parameter \
        --name "${source_parameter_name}" \
        --with-decryption \
        --query Parameter.Value \
        --output text
    )"

    printf '%s\n' "${source_parameter_value}"

    aws ssm put-parameter \
      --name "${new_parameter_name}" \
      --type 'SecureString' \
      --value "${source_parameter_value}"
    ```

2. Choose a new parser version to test updating to and run the script:

    For example, to upgrade to version 'v0.0.0' (which should fail):

    ```bash
    ./set_env_parser_version.sh \
      "${new_parameter_name}" \
      'v0.0.0'
    ```
