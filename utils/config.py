import configparser
from pathlib import Path


def get_config():
    config = configparser.ConfigParser()
    if not Path('config.ini').exists():
        raise Exception('config.ini not found, please create one.')

    try:
        config.read('config.ini')  # Assuming the config file is named "config.ini"
    except configparser.Error:
        # If config file is malformed, return empty config
        # This allows the application to continue with default values
        pass

    return config
