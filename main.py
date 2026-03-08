#!/usr/bin/env python3
"""
main.py - エントリポイント
pomelax: 低スペック Linux 向け Slack テキスト送受信アプリ
"""

import sys


def _show_error_gui(message: str) -> bool:
    """GUI でエラー表示を試みる。成功時 True、失敗時 False を返す"""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("依存パッケージエラー", message)
        root.destroy()
        return True
    except ImportError:
        # tkinter が無い
        return False
    except tk.TclError:
        # ヘッドレス環境等で Tk 初期化失敗
        return False


def main() -> int:
    # requests の依存チェック（起動時点でエラーハンドリング）
    try:
        import requests  # noqa: F401
    except ImportError:
        message = (
            "requests パッケージが見つかりません。\n\n"
            "以下を実行してください：\n"
            "  python3 -m pip install --user requests\n\n"
            "または：\n"
            "  python3 -m pip install --break-system-packages requests"
        )

        # GUI で表示を試み、失敗したら CLI にフォールバック
        if not _show_error_gui(message):
            print("[pomelax] 依存パッケージエラー")
            print("requests パッケージが見つかりません。")
            print()
            print("以下を実行してください：")
            print("  python3 -m pip install --user requests")
            print("または：")
            print("  python3 -m pip install --break-system-packages requests")
        return 1

    # 依存チェック完了後に本体を起動
    from config import load_config
    from ui import run

    config, corrupted = load_config()
    run(config, corrupted)
    return 0


if __name__ == "__main__":
    sys.exit(main())
