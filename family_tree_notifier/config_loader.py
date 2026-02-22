import os

DEFAULT_CONFIG = {
    "PERSON_ID": "",
    "LANGUAGE": "he",
    "DIRECT_MARKER": "⭐",
    "MAX_DISTANCE_DIRECT": "0",
    "MAX_DISTANCE_BLOOD": "10",
    "MAX_DISTANCE_MARRIAGE": "5",
    "SHOW_PATH_DISTANCE_DIRECT": "5",
    "SHOW_PATH_DISTANCE_BLOOD": "3",
    "SHOW_PATH_DISTANCE_MARRIAGE": "1",
}

def load_config(config_path="config.txt"):
    """
    Loads configuration from a simple text file and environment variables.
    Environment variables take precedence over the config file.

    File format:
    KEY=VALUE
    # comment
    """
    config = DEFAULT_CONFIG.copy()

    # 1. Load from file if it exists
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip().upper()] = value.strip()

    # 2. Override with environment variables
    for key in config:
        env_val = os.environ.get(key)
        if env_val:
            config[key] = env_val

    # Compatibility with previous environment variable names
    if os.environ.get("PERSONID"):
        config["PERSON_ID"] = os.environ.get("PERSONID")

    if os.environ.get("DISTANCE_THRESHOLD"):
        dt = os.environ.get("DISTANCE_THRESHOLD")
        # If the old threshold is set, use it for all SHOW_PATH distances
        # unless they were specifically overridden in env or config file
        # To check if it was overridden, we can compare with DEFAULT_CONFIG or check the file/env again.
        # But it's easier to just apply it if the specific env vars are not present.
        for key in ["SHOW_PATH_DISTANCE_DIRECT", "SHOW_PATH_DISTANCE_BLOOD", "SHOW_PATH_DISTANCE_MARRIAGE"]:
            if key not in os.environ:
                config[key] = dt

    return config
