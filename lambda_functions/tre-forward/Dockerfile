FROM public.ecr.aws/lambda/python:3.8

RUN yum -y update \
    && yum clean all

# Copy function code
COPY tre_forward.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "tre_forward.lambda_handler" ]
