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
        default = {"nvd_api_key": "", "use_local_db": False, "local_db_path": ""}
        if not os.path.exists(CONFIG_PATH):
            return default
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                # ensure default keys exist
                for k, v in default.items():
                    data.setdefault(k, v)
                return data
        except Exception as e:
            logger.warning("Cannot load config: %s", e)
            return default

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
