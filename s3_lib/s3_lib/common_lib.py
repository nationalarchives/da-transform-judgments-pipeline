#!/usr/bin/env python3
import logging
import os

# Set global logging options; AWS environment may override this though
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_env_var(env_var_name, must_exist=True, must_have_value=True):
    """
    Return the value of the environment variable named in `env_var_name`.
    
    Will raise a ValueError if:
    * `must_exist` is True and the variable does not exist in the environment
    * `must_have_value` is True and the length of the variable's value is 0
    """
    logger.info('get_env_var start')
    if must_exist and env_var_name not in os.environ:
        raise ValueError(f'Environment variable {env_var_name} not set')
    value=''
    if env_var_name in os.environ:
        value = os.environ[env_var_name]
    if must_have_value and len(value) == 0:
        raise ValueError(f'Environment variable {env_var_name} is length 0')
    logger.debug(f'{env_var_name}={value}')
    logger.info('get_env_var return')
    return value
