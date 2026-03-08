import json

DATA_PATH = r"C:\Support Bot v1\Data\Data.json"

def load_config():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

_config = load_config()

TOKEN = _config["TOKEN"]
OWNER_ID = _config["OWNER_ID"]