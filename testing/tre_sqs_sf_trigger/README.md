Creates a test message and runs the Lambda handler function locally to execute
the specified Step Function (State Machine).

```bash
./run.sh \
  "${state_machine_name}" \
  "${provider_name} \
  "${event_name} \
  "${consignment_type}" \
  "${message_parameters}" \
  "${consignment_ref_key_path}" \
  "${aws_profile_target}"

# Given the following value for message_parameters:
message_parameters='"a": {"b": {"c": "cr-2032"}}'

# This consignment_ref_key_path would locate value cr-2032:
consignment_ref_key_path='parameters.a.b.c'
```
