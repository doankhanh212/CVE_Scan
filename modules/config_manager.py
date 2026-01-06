# config_manager.py
import json
import os
import stat
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Use config directory in project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_PATH = CONFIG_DIR / "web_config.json"

class ConfigManager:
    @staticmethod
    def load():
        default = {"nvd_api_key": "", "use_local_db": False, "local_db_path": ""}
        if not CONFIG_PATH.exists():
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
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            tmp = str(CONFIG_PATH) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            os.replace(tmp, str(CONFIG_PATH))
            try:
                os.chmod(str(CONFIG_PATH), stat.S_IRUSR | stat.S_IWUSR)
            except Exception:
                pass
            return True
        except Exception as e:
            logger.error("Cannot save config: %s", e)
            return False
