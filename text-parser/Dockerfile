# This COPY command copies the .NET Lambda project's build artifacts from the host machine into the image. 
# The source of the COPY should match where the .NET Lambda project publishes its build artifacts. If the Lambda function is being built 
# with the AWS .NET Lambda Tooling, the `--docker-host-build-output-dir` switch controls where the .NET Lambda project
# will be built. The .NET Lambda project templates default to having `--docker-host-build-output-dir`
# set in the aws-lambda-tools-defaults.json file to "bin/Release/net5.0/linux-x64/publish".
#
# Alternatively Docker multi-stage build could be used to build the .NET Lambda project inside the image.
# For more information on this approach checkout the project's README.md file.

FROM public.ecr.aws/lambda/dotnet:5.0 AS base

FROM mcr.microsoft.com/dotnet/sdk:5.0 AS build-env

WORKDIR /var/task

COPY *.csproj ./

RUN dotnet restore

COPY . ./

FROM build-env

RUN dotnet publish -o bin/Release/lambda-publish/ --no-restore

FROM base AS final

COPY "bin/Release/lambda-publish/*" ${LAMBDA_TASK_ROOT}

CMD [ "AWS::UK.Gov.NationalArchives.Judgments.Api.Lambda::FunctionHandler" ]