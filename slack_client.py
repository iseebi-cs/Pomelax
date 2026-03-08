"""
slack_client.py - Slack API / Webhook 通信
送信: Incoming Webhook
受信: Slack Web API (Bot Token) - conversations.history, files.info
"""

import requests

# API ベース
SLACK_API_BASE = "https://slack.com/api"


def auth_test(token: str) -> tuple[bool, str]:
    """
    auth.test でトークン検証。
    Returns: (success, message)
    """
    try:
        r = requests.post(
            f"{SLACK_API_BASE}/auth.test",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        data = r.json()
        if data.get("ok"):
            return True, data.get("user", "OK")
        return False, data.get("error", "Unknown error")
    except requests.RequestException as e:
        return False, str(e)


def get_channel_history(token: str, channel_id: str, limit: int = 50) -> tuple[bool, str, list]:
    """
    チャンネルの履歴を取得。
    Returns: (success, error_message, messages)
    """
    try:
        r = requests.get(
            f"{SLACK_API_BASE}/conversations.history",
            params={"channel": channel_id, "limit": limit},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        data = r.json()
        if not data.get("ok"):
            return False, data.get("error", "Unknown error"), []
        return True, "", data.get("messages", [])
    except requests.RequestException as e:
        return False, str(e), []


def get_file_info(token: str, file_id: str) -> tuple[bool, str, dict]:
    """
    files.info でファイル詳細取得。url_private を取得するため。
    Returns: (success, error_message, file_object)
    """
    try:
        r = requests.get(
            f"{SLACK_API_BASE}/files.info",
            params={"file": file_id},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        data = r.json()
        if not data.get("ok"):
            return False, data.get("error", "Unknown error"), {}
        return True, "", data.get("file", {})
    except requests.RequestException as e:
        return False, str(e), {}


def get_file_content(token: str, url: str) -> tuple[bool, str, str]:
    """
    添付ファイルの内容を取得（url_private 用）。
    Returns: (success, error_message, content)
    """
    try:
        r = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if r.status_code == 200:
            return True, "", r.text
        return False, f"HTTP {r.status_code}", ""
    except requests.RequestException as e:
        return False, str(e), ""


def send_webhook(webhook_url: str, text: str, filename: str = "") -> tuple[bool, str]:
    """
    Incoming Webhook で送信。
    Returns: (success, error_message)
    """
    try:
        if filename:
            payload = {"text": f"*[{filename}]*\n\n{text}"}
        else:
            payload = {"text": text}
        r = requests.post(webhook_url, json=payload, timeout=15)
        if r.status_code == 200:
            return True, ""
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except requests.RequestException as e:
        return False, str(e)
