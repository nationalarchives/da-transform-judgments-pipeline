FROM public.ecr.aws/lambda/python:3.8

# Copy function code
COPY prepare_parser_input.py ${LAMBDA_TASK_ROOT}

# Install the function's dependencies using file requirements.txt
COPY "*.whl" .
COPY tmp-build-requirements.txt ./requirements.txt
RUN  yum -y update \ 
    && yum clean all \
    && pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "prepare_parser_input.handler" ]
