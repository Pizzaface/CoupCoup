import configparser
from pathlib import Path


def get_config():
    config = configparser.ConfigParser()
    if not Path('config.ini').exists():
        raise Exception('config.ini not found, please create one.')

    config.read('config.ini')  # Assuming the config file is named "config.ini"

    return config
