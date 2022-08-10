FROM public.ecr.aws/lambda/python:3.8

# Copy function code
COPY tre_validate_bagit.py ${LAMBDA_TASK_ROOT}

# Install the function's dependencies using file requirements.txt
COPY "*.whl" .
COPY tmp-build-requirements.txt .
RUN  pip3 install -r tmp-build-requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "tre_validate_bagit.handler" ]
