"""
storage.py - 保存、衝突回避、state管理
仕様: state ~/.local/share/pomelax/state.json
"""

import json
import re
from datetime import datetime
from pathlib import Path


STATE_DIR = Path.home() / ".local" / "share" / "pomelax"
STATE_PATH = STATE_DIR / "state.json"


def _ensure_state_dir() -> None:
    """state用ディレクトリが存在することを保証"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def load_state() -> dict:
    """state.json を読み込む"""
    try:
        if STATE_PATH.exists():
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return {"saved_message_ts": [], "saved_file_ids": [], "last_send_folder": ""}


def save_state(state: dict) -> bool:
    """state.json を保存する"""
    try:
        _ensure_state_dir()
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


def ensure_folder(path: str) -> bool:
    """保存先フォルダが存在することを保証。自動作成を試みる"""
    try:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return True
    except OSError:
        return False


def get_state_path() -> str:
    """stateの保存場所を返す（UI表示用）"""
    return str(STATE_PATH)


def _sanitize_filename(name: str) -> str:
    """制御文字・危険文字を除去"""
    s = re.sub(r"[\x00-\x1f\x7f]", "", name)
    return s.strip() or "unknown"


def save_message(
    folder: str, ts: str, text: str, saved_ts: set[str]
) -> tuple[bool, str, str]:
    """
    メッセージを YYYYMMDD-HHMMSS_slack.txt 形式で保存。
    ts（Slackタイムスタンプ）からファイル名を生成する。
    Returns: (success, error_message, file_path)
    """
    if ts in saved_ts:
        return False, "既に保存済みです", ""
    if not ensure_folder(folder):
        return False, "フォルダを作成できません", ""
    try:
        # Slack の ts (例: "1234567890.123456") から datetime を生成
        try:
            ts_float = float(ts)
            dt = datetime.fromtimestamp(ts_float)
        except (ValueError, OSError):
            # ts が不正な場合は現在時刻を使用
            dt = datetime.now()

        base = Path(folder) / (dt.strftime("%Y%m%d-%H%M%S") + "_slack.txt")
        path = base
        n = 1
        while path.exists():
            path = base.parent / f"{base.stem}_{n}{base.suffix}"
            n += 1
        path.write_text(text or "", encoding="utf-8")
        return True, "", str(path)
    except OSError as e:
        return False, str(e), ""


def save_attachment(
    folder: str, file_id: str, name: str, content: str, saved_ids: set[str]
) -> tuple[bool, str, str]:
    """
    添付ファイルを保存。衝突時は連番付与。
    Returns: (success, error_message, file_path)
    """
    if file_id in saved_ids:
        return False, "既に保存済みです", ""
    if not ensure_folder(folder):
        return False, "フォルダを作成できません", ""
    safe_name = _sanitize_filename(name)
    if not safe_name:
        safe_name = "unknown"
    try:
        base = Path(folder) / safe_name
        path = base
        n = 1
        while path.exists():
            stem = base.stem
            suffix = base.suffix
            path = base.parent / f"{stem}_{n}{suffix}"
            n += 1
        path.write_text(content or "", encoding="utf-8")
        return True, "", str(path)
    except OSError as e:
        return False, str(e), ""


def list_files(folder: str, extensions: list[str]) -> list[Path]:
    """指定フォルダから拡張子に一致するファイル一覧を返す（更新日時降順）"""
    if not folder:
        return []
    try:
        p = Path(folder)
        if not p.is_dir():
            return []
        result = []
        for ext in extensions:
            result.extend(p.glob(f"*{ext}"))
        return sorted(result, key=lambda f: f.stat().st_mtime, reverse=True)
    except OSError:
        return []
