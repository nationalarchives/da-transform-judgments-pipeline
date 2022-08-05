import os
import setuptools

tre_lib_version = os.environ['TRE_LIB_VERSION']

setuptools.setup(
    name='tre_lib',
    version=tre_lib_version,
    description='TRE Python code library',
    packages=setuptools.find_packages(exclude=['tests']),
    python_requires='>=3.8'
)
