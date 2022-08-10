import os
import setuptools

tre_lib_version = os.environ['TRE_LIB_VERSION']

setuptools.setup(
    name='tre_lib',
    version=tre_lib_version,
    description='TRE Python code library',
    packages={'tre_lib'},
    package_dir={'tre_lib': 'tre_lib'},
    package_data={'tre_lib': ['schema*.json']},
    python_requires='>=3.8'
)
