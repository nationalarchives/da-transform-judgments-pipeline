import os
import setuptools

env_s3_lib_version = os.environ['S3_LIB_VERSION']

setuptools.setup(
    name='s3_lib',
    version=env_s3_lib_version,
    description='APIs for managing AWS s3 content',
    packages=setuptools.find_packages(exclude=['tests']),
    python_requires='>=3.8'
)
