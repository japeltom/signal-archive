import json, os, sys

def get_config():
    try:
        config_file_name = sys.argv[1]
    except IndexError:
        raise SystemExit("Please provide a JSON config file name as a command line paramater.")

    if not os.path.exists(config_file_name):
        raise SystemExit("File '{}' does not exist.".format(config_file_name))

    with open(config_file_name) as f:
        config = json.load(f)

    return config

