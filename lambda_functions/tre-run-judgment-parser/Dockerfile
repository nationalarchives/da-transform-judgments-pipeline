FROM public.ecr.aws/lambda/dotnet:7 AS base

WORKDIR /var/task

FROM mcr.microsoft.com/dotnet/sdk:7.0 AS build-env

WORKDIR /src

COPY . ./

RUN ls

RUN dotnet restore TRE/TRE.csproj

RUN ls

# RUN dotnet build *.csproj -c Release -o /var/task

FROM build-env AS publish

RUN dotnet publish TRE/TRE.csproj -c Release -o /src --no-restore

FROM base AS final 

RUN yum -y update && yum clean all

WORKDIR /var/task

COPY --from=publish /src ${LAMBDA_TASK_ROOT}

CMD [ "TRE::UK.Gov.NationalArchives.CaseLaw.TRE.Lambda::FunctionHandler" ]