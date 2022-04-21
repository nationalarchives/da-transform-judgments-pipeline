FROM public.ecr.aws/lambda/python:3.8
ARG s3_lib_whl

# Copy function code
COPY te_editorial_integration.py ${LAMBDA_TASK_ROOT}

# Install the function's dependencies using file requirements.txt
COPY "${s3_lib_whl}" .
COPY tmp-build-requirements.txt ./requirements.txt
RUN yum -y update \
    && yum clean all \
    && pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "tre_editorial_integration.handler" ]
