"""
config.py - config読み書き、環境変数上書き
仕様: ~/.config/pomelax/config.json
環境変数 POMELAX_BOT_TOKEN, POMELAX_WEBHOOK_URL, POMELAX_CHANNEL_ID が config より優先
"""

import json
import os
from pathlib import Path


CONFIG_DIR = Path.home() / ".config" / "pomelax"
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "slack_bot_token": "",
    "channel_id": "",
    "incoming_webhook_url": "",
    "receive_folder": "",  # 空文字列でも許容（Windows で Secrets だけ先に設定する運用を可能にする）
    "send_folder": "",     # 空文字列でも許容（同上）
    "fetch_count": 50,
    "extensions": [".txt", ".md"],
}


def _apply_env_overrides(config: dict) -> dict:
    """環境変数が設定されている場合は config より優先"""
    result = config.copy()
    if os.environ.get("POMELAX_BOT_TOKEN"):
        result["slack_bot_token"] = os.environ["POMELAX_BOT_TOKEN"]
    if os.environ.get("POMELAX_WEBHOOK_URL"):
        result["incoming_webhook_url"] = os.environ["POMELAX_WEBHOOK_URL"]
    if os.environ.get("POMELAX_CHANNEL_ID"):
        result["channel_id"] = os.environ["POMELAX_CHANNEL_ID"]
    return result


def load_config() -> tuple[dict, bool]:
    """設定を読み込む。壊れている場合はデフォルト値を返す

    Returns:
        tuple[dict, bool]: (config辞書, 破損検出フラグ)
        破損検出フラグがTrueの場合、config.jsonが壊れていたことを示す
    """
    corrupted = False
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = {**DEFAULT_CONFIG, **data}
            return _apply_env_overrides(merged), False
    except (json.JSONDecodeError, OSError):
        corrupted = True
    return _apply_env_overrides(DEFAULT_CONFIG.copy()), corrupted


def save_config(config: dict) -> bool:
    """設定を保存する"""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


def get_config_path() -> str:
    """設定の保存場所を返す（UI表示用）"""
    return str(CONFIG_PATH)
