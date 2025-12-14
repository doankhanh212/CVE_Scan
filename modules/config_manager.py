# config_manager.py
import json
import os
import stat
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

CONFIG_DIR = os.path.expanduser("~/.cvescanner")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

class ConfigManager:
    @staticmethod
    def load():
        if not os.path.exists(CONFIG_PATH):
            return {"nvd_api_key": ""}
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Cannot load config: %s", e)
            return {"nvd_api_key": ""}

    @staticmethod
    def save(data: dict):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            tmp = CONFIG_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            os.replace(tmp, CONFIG_PATH)
            try:
                os.chmod(CONFIG_PATH, stat.S_IRUSR | stat.S_IWUSR)
            except Exception:
                pass
            return True
        except Exception as e:
            logger.error("Cannot save config: %s", e)
            return False
