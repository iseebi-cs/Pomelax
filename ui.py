"""
ui.py - tkinter UI、イベント処理
メイン画面: 送信/受信タブ、2ペイン構成、キーバインド
通信はワーカースレッドで実行、UI更新は after() でメインスレッドへ（仕様 9）
"""

import threading
import os
from pathlib import Path
from typing import Callable, Optional

import tkinter as tk
from tkinter import ttk, filedialog

from config import save_config, get_config_path
from storage import (
    load_state,
    save_state,
    list_files,
    save_message,
    save_attachment,
    get_state_path,
)
from slack_client import (
    send_webhook,
    get_channel_history,
    get_file_content,
    get_file_info,
    auth_test,
)


def _open_settings(
    parent: tk.Tk,
    cfg: dict,
    set_status: Callable[[str], None],
    on_send_refresh: Callable[[], None],
    on_recv_refresh: Callable[[], None],
) -> None:
    """設定ダイアログを開く（仕様 7.1/7.2）"""
    dlg = tk.Toplevel(parent)
    dlg.title("設定")
    dlg.geometry("520x400")
    dlg.transient(parent)
    dlg.grab_set()

    frm = ttk.Frame(dlg, padding=8)
    frm.pack(fill=tk.BOTH, expand=True)
    row = 0

    def add_row(label: str, key: str, password: bool = False) -> ttk.Entry:
        nonlocal row
        ttk.Label(frm, text=label).grid(row=row, column=0, sticky=tk.W, pady=2)
        entry_kwargs = {"width": 50}
        if password:
            entry_kwargs["show"] = "*"
        e = ttk.Entry(frm, **entry_kwargs)
        e.insert(0, str(cfg.get(key, "")))
        e.grid(row=row, column=1, sticky=tk.EW, pady=2)
        row += 1
        return e

    def add_row_plain(label: str, key: str) -> ttk.Entry:
        return add_row(label, key, password=False)

    e_token = add_row("Slack Bot Token", "slack_bot_token", password=True)
    e_channel = add_row_plain("受信チャンネルID", "channel_id")
    e_webhook = add_row("Incoming Webhook URL", "incoming_webhook_url", password=True)
    e_recv_folder = add_row_plain("受信保存先フォルダ", "receive_folder")
    e_send_folder = add_row_plain("送信元フォルダ", "send_folder")
    e_fetch = add_row_plain("取得件数", "fetch_count")
    e_ext = add_row_plain("拡張子 (.txt,.md)", "extensions")

    def ext_get() -> str:
        exts = cfg.get("extensions", [".txt", ".md"])
        if isinstance(exts, list):
            return ",".join(exts)
        return str(exts)

    def ext_set(val: str) -> list:
        return [x.strip() for x in val.replace(" ", "").split(",") if x]

    e_ext.delete(0, tk.END)
    e_ext.insert(0, ext_get())

    # 保存場所表示（仕様 7.2）
    row += 1
    ttk.Label(frm, text="config:").grid(row=row, column=0, sticky=tk.W, pady=4)
    ttk.Label(frm, text=get_config_path(), font=("Consolas", 8)).grid(
        row=row, column=1, sticky=tk.W, pady=4
    )
    row += 1
    ttk.Label(frm, text="state:").grid(row=row, column=0, sticky=tk.W, pady=2)
    ttk.Label(frm, text=get_state_path(), font=("Consolas", 8)).grid(
        row=row, column=1, sticky=tk.W, pady=2
    )
    row += 1

    test_msg = tk.StringVar(value="")

    def on_test() -> None:
        token = e_token.get().strip()
        ch = e_channel.get().strip()
        if not token:
            test_msg.set("Token を入力してください")
            return
        test_msg.set("接続テスト中...")

        def _test_worker() -> None:
            try:
                ok, msg = auth_test(token)
                if not ok:
                    dlg.after(0, lambda: test_msg.set(f"auth.test 失敗: {msg}"))
                    return
                if not ch:
                    dlg.after(0, lambda: test_msg.set("auth.test OK（チャンネル未設定）"))
                    return
                ok2, err2, _ = get_channel_history(token, ch, 2)
                if ok2:
                    dlg.after(0, lambda: test_msg.set("接続OK（auth.test + history 取得成功）"))
                else:
                    dlg.after(0, lambda: test_msg.set(f"history 取得失敗: {err2}"))
            except Exception as e:
                dlg.after(0, lambda: test_msg.set(f"エラー: {e}"))

        threading.Thread(target=_test_worker, daemon=True).start()

    ttk.Button(frm, text="接続テスト", command=on_test).grid(
        row=row, column=0, columnspan=2, pady=8
    )
    row += 1
    ttk.Label(frm, textvariable=test_msg, foreground="blue").grid(
        row=row, column=0, columnspan=2, sticky=tk.W
    )
    row += 1

    def on_save() -> None:
        cfg["slack_bot_token"] = e_token.get().strip()
        cfg["channel_id"] = e_channel.get().strip()
        cfg["incoming_webhook_url"] = e_webhook.get().strip()
        cfg["receive_folder"] = e_recv_folder.get().strip()
        cfg["send_folder"] = e_send_folder.get().strip()
        try:
            cfg["fetch_count"] = int(e_fetch.get().strip() or "50")
        except ValueError:
            cfg["fetch_count"] = 50
        cfg["extensions"] = ext_set(e_ext.get()) or [".txt", ".md"]
        if save_config(cfg):
            set_status("設定を保存しました")
            on_send_refresh()
            on_recv_refresh()
            dlg.destroy()
        else:
            set_status("設定の保存に失敗しました")
            test_msg.set("保存失敗")

    def on_cancel() -> None:
        dlg.destroy()

    btn_frm = ttk.Frame(frm)
    btn_frm.grid(row=row, column=0, columnspan=2, pady=12)
    ttk.Button(btn_frm, text="保存", command=on_save).pack(side=tk.LEFT, padx=4)
    ttk.Button(btn_frm, text="キャンセル", command=on_cancel).pack(side=tk.LEFT, padx=4)

    frm.columnconfigure(1, weight=1)


def _set_preview(text_widget: tk.Text, content: str, enabled: bool = True) -> None:
    """右ペインのプレビューを更新"""
    text_widget.config(state=tk.NORMAL)
    text_widget.delete("1.0", tk.END)
    text_widget.insert(tk.END, content or "(内容なし)")
    text_widget.config(state=tk.DISABLED if not enabled else tk.NORMAL)


def run(config: dict, config_corrupted: bool = False) -> None:
    """UIを起動"""
    state = load_state()
    cfg = config.copy()

    root = tk.Tk()
    root.title("pomelax")
    root.minsize(640, 350)
    root.geometry("800x420")

    # アイコン設定
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
    if os.path.exists(icon_path):
        try:
            icon = tk.PhotoImage(file=icon_path)
            root.iconphoto(False, icon)
        except Exception:
            pass  # アイコン読み込み失敗時は無視

    # config破損時の警告表示（仕様 8: エラーハンドリング）
    if config_corrupted:
        def show_warning():
            from tkinter import messagebox
            messagebox.showwarning(
                "設定ファイル読み込みエラー",
                "config.json が壊れているか読み込めませんでした。\n"
                "デフォルト設定で起動しています。\n\n"
                "設定画面から再度設定を保存してください。"
            )
        root.after(100, show_warning)

    # ステータス（全アクションで更新）
    status_var = tk.StringVar(value="準備完了")

    def set_status(msg: str) -> None:
        status_var.set(msg)

    # ノートブック
    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    # ---- 送信タブ ----
    send_frame = ttk.Frame(notebook, padding=4)
    notebook.add(send_frame, text="送信")

    send_paned = ttk.PanedWindow(send_frame, orient=tk.HORIZONTAL)
    send_paned.pack(fill=tk.BOTH, expand=True)

    send_list_frame = ttk.Frame(send_paned)
    send_listbox = tk.Listbox(send_list_frame, font=("Consolas", 10), width=30)
    send_listbox.pack(fill=tk.BOTH, expand=True)
    send_paned.add(send_list_frame, weight=1)

    send_prev_frame = ttk.Frame(send_paned)
    send_preview = tk.Text(send_prev_frame, font=("Consolas", 10), wrap=tk.WORD)
    send_scroll = ttk.Scrollbar(send_prev_frame, command=send_preview.yview)
    send_preview.configure(yscrollcommand=send_scroll.set)
    send_preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    send_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    send_paned.add(send_prev_frame, weight=2)

    send_paths: list[Path] = []

    def on_send_select(_event) -> None:
        sel = send_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if 0 <= idx < len(send_paths):
            try:
                content = send_paths[idx].read_text(encoding="utf-8")
            except OSError:
                content = "(読み込み失敗)"
            _set_preview(send_preview, content, enabled=False)

    def on_send_folder_select() -> None:
        """送信元フォルダを選択（仕様 5.1）"""
        initial = cfg.get("send_folder") or state.get("last_send_folder") or ""
        folder = filedialog.askdirectory(title="送信元フォルダを選択", initialdir=initial or None)
        if folder:
            cfg["send_folder"] = folder
            state["last_send_folder"] = folder
            save_config(cfg)
            save_state(state)
            set_status(f"フォルダ設定: {folder}")
            on_send_refresh()

    def on_send_refresh() -> None:
        set_status("取得中...")
        folder = cfg.get("send_folder") or state.get("last_send_folder") or ""
        exts = cfg.get("extensions", [".txt", ".md"])
        if not folder:
            set_status("送信フォルダが未設定です")
            send_listbox.delete(0, tk.END)
            send_paths.clear()
            return
        files = list_files(folder, exts)
        send_listbox.delete(0, tk.END)
        send_paths.clear()
        for f in files:
            send_listbox.insert(tk.END, f.name)
            send_paths.append(f)
        set_status(f"一覧更新完了（{len(files)}件）")

    def on_send_send() -> None:
        sel = send_listbox.curselection()
        if not sel:
            set_status("送信するファイルを選択してください")
            return
        idx = sel[0]
        if idx >= len(send_paths):
            return
        path = send_paths[idx]
        webhook = cfg.get("incoming_webhook_url", "").strip()
        if not webhook:
            set_status("Webhook URL が未設定です")
            return
        set_status("送信中...")

        def _send_worker() -> None:
            try:
                content = path.read_text(encoding="utf-8")
                ok, err = send_webhook(webhook, content, path.name)
                if ok:
                    state["last_send_folder"] = str(path.parent)
                    save_state(state)
                    root.after(0, lambda: set_status("送信完了"))
                else:
                    root.after(0, lambda: set_status(f"送信失敗: {err}"))
            except OSError as e:
                root.after(0, lambda: set_status(f"読み込み失敗: {e}"))
            except Exception as e:
                root.after(0, lambda: set_status(f"エラー: {e}"))

        threading.Thread(target=_send_worker, daemon=True).start()

    send_listbox.bind("<<ListboxSelect>>", on_send_select)

    # ---- 受信タブ ----
    recv_frame = ttk.Frame(notebook, padding=4)
    notebook.add(recv_frame, text="受信")

    recv_paned = ttk.PanedWindow(recv_frame, orient=tk.HORIZONTAL)
    recv_paned.pack(fill=tk.BOTH, expand=True)

    recv_list_frame = ttk.Frame(recv_paned)
    recv_listbox = tk.Listbox(recv_list_frame, font=("Consolas", 10), width=30)
    recv_listbox.pack(fill=tk.BOTH, expand=True)
    recv_paned.add(recv_list_frame, weight=1)

    recv_prev_frame = ttk.Frame(recv_paned)
    recv_preview = tk.Text(recv_prev_frame, font=("Consolas", 10), wrap=tk.WORD)
    recv_scroll = ttk.Scrollbar(recv_prev_frame, command=recv_preview.yview)
    recv_preview.configure(yscrollcommand=recv_scroll.set)
    recv_preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    recv_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    recv_paned.add(recv_prev_frame, weight=2)

    recv_items: list[dict] = []

    def on_recv_select(_event) -> None:
        sel = recv_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if 0 <= idx < len(recv_items):
            item = recv_items[idx]
            if item.get("type") == "msg":
                _set_preview(recv_preview, item.get("text", ""), enabled=False)
            else:
                _set_preview(recv_preview, "(添付・保存ボタンで取得)", enabled=False)

    def on_recv_refresh() -> None:
        token = cfg.get("slack_bot_token", "").strip()
        ch = cfg.get("channel_id", "").strip()
        limit = cfg.get("fetch_count", 50)
        if not token or not ch:
            set_status("Bot Token または チャンネルID が未設定です")
            recv_listbox.delete(0, tk.END)
            recv_items.clear()
            return
        set_status("取得中...")

        def _fetch_worker() -> None:
            try:
                ok, err, messages = get_channel_history(token, ch, limit)
                items = []
                for msg in messages:
                    text = (msg.get("text") or "").strip()
                    if text:
                        label = f"MSG: {text[:30]}{'...' if len(text) > 30 else ''}"
                        items.append((label, {"type": "msg", "text": text, "ts": msg.get("ts"), "msg": msg}))
                    for f in msg.get("files", []) or []:
                        mt = (f.get("mimetype") or "").lower()
                        if "text/plain" in mt or "text/markdown" in mt:
                            name = f.get("name", "unknown")
                            items.append((f"FILE: {name}", {"type": "file", "file": f, "name": name}))
                def _apply() -> None:
                    recv_listbox.delete(0, tk.END)
                    recv_items.clear()
                    if not ok:
                        set_status(f"取得失敗: {err}")
                        return
                    for label, it in items:
                        recv_listbox.insert(tk.END, label)
                        recv_items.append(it)
                    set_status(f"取得完了（{len(recv_items)}件）")
                root.after(0, _apply)
            except Exception as e:
                root.after(0, lambda: set_status(f"エラー: {e}"))

        threading.Thread(target=_fetch_worker, daemon=True).start()

    def on_recv_save() -> None:
        sel = recv_listbox.curselection()
        if not sel:
            set_status("保存する項目を選択してください")
            return
        idx = sel[0]
        if idx >= len(recv_items):
            return
        item = recv_items[idx]
        folder = cfg.get("receive_folder", "").strip()
        if not folder:
            set_status("受信保存先フォルダが未設定です")
            return
        saved_ts = set(state.get("saved_message_ts", []))
        saved_ids = set(state.get("saved_file_ids", []))

        if item.get("type") == "msg":
            ts = item.get("ts", "")
            text = item.get("text", "")
            try:
                ok, err, path = save_message(folder, ts, text, saved_ts)
                if ok:
                    state.setdefault("saved_message_ts", []).append(ts)
                    save_state(state)
                    set_status(f"保存完了: {path}")
                else:
                    set_status(err)
            except Exception as e:
                set_status(f"エラー: {e}")
            return

        # 添付: 取得＋保存をスレッドで実行
        f = item.get("file", {})
        file_id = f.get("id", "")
        name = f.get("name", "unknown")
        url = f.get("url_private", "")
        token = cfg.get("slack_bot_token", "").strip()

        set_status("取得中...")

        def _save_file_worker() -> None:
            try:
                # URLが無い場合はスレッド内で取得（UIブロック回避）
                nonlocal url, name
                if not url and file_id:
                    ok_info, err_info, finfo = get_file_info(token, file_id)
                    if ok_info:
                        url = finfo.get("url_private", "")
                        name = finfo.get("name", name)

                if not url:
                    root.after(0, lambda: set_status("添付のURLを取得できません"))
                    return

                ok_fetch, err_fetch, content = get_file_content(token, url)
                if not ok_fetch:
                    root.after(0, lambda: set_status(f"取得失敗: {err_fetch}"))
                    return
                ok, err, path = save_attachment(
                    folder, file_id, name, content, saved_ids
                )
                if ok:
                    state.setdefault("saved_file_ids", []).append(file_id)
                    save_state(state)
                    root.after(0, lambda: set_status(f"保存完了: {path}"))
                else:
                    root.after(0, lambda: set_status(err))
            except Exception as e:
                root.after(0, lambda: set_status(f"エラー: {e}"))

        threading.Thread(target=_save_file_worker, daemon=True).start()

    recv_listbox.bind("<<ListboxSelect>>", on_recv_select)

    # ---- 下部×　上部に移動: ボタン（タブで切り替え） ----
    bottom = ttk.Frame(root, padding=4)
    bottom.pack(fill=tk.X, before=notebook)

    btn_primary = ttk.Button(bottom, text="送信")
    btn_primary.pack(side=tk.LEFT, padx=2)
    btn_secondary = ttk.Button(bottom, text="更新")
    btn_secondary.pack(side=tk.LEFT, padx=2)
    btn_folder = ttk.Button(bottom, text="フォルダ", command=on_send_folder_select)
    btn_folder.pack(side=tk.LEFT, padx=2)
    ttk.Label(bottom, textvariable=status_var).pack(side=tk.LEFT, padx=8)
    btn_settings = ttk.Button(bottom, text="設定", command=lambda: _open_settings(root, cfg, set_status, on_send_refresh, on_recv_refresh))
    btn_settings.pack(side=tk.RIGHT, padx=2)

    def update_buttons() -> None:
        idx = notebook.index(notebook.select())
        if idx == 0:
            btn_primary.config(text="送信", command=on_send_send)
            btn_secondary.config(text="更新", command=on_send_refresh)
            btn_folder.config(state=tk.NORMAL)
        else:
            btn_primary.config(text="保存", command=on_recv_save)
            btn_secondary.config(text="更新", command=on_recv_refresh)
            btn_folder.config(state=tk.DISABLED)

    notebook.bind("<<NotebookTabChanged>>", lambda e: update_buttons())
    update_buttons()

    # ---- キーバインド（仕様 4.2） ----
    def get_active_listbox() -> Optional[tk.Listbox]:
        idx = notebook.index(notebook.select())
        return send_listbox if idx == 0 else recv_listbox

    def on_key(event) -> None:
        k = event.keysym
        if k in ("q", "Q"):
            root.quit()
            return
        lb = get_active_listbox()
        if not lb:
            return
        cur = lb.curselection()
        count = lb.size()
        if k in ("Up", "Down"):
            if count == 0:
                return
            next_idx = (cur[0] if cur else 0) + (-1 if k == "Up" else 1)
            next_idx = max(0, min(next_idx, count - 1))
            lb.selection_clear(0, tk.END)
            lb.selection_set(next_idx)
            lb.see(next_idx)
            lb.event_generate("<<ListboxSelect>>")
        elif k == "Return":
            if cur:
                idx = notebook.index(notebook.select())
                if idx == 0:
                    on_send_select(event)
                else:
                    on_recv_select(event)
        elif k in ("s", "S"):
            idx = notebook.index(notebook.select())
            if idx == 0:
                on_send_send()
            else:
                on_recv_save()
        elif k in ("r", "R"):
            idx = notebook.index(notebook.select())
            if idx == 0:
                on_send_refresh()
            else:
                on_recv_refresh()

    root.bind("<KeyPress>", on_key)

    # 初回: 送信タブの一覧をロード試行
    on_send_refresh()

    # 初回セットアップウィザード（必須項目が未入力の場合）
    if not config_corrupted:
        token = cfg.get("slack_bot_token", "").strip()
        webhook = cfg.get("incoming_webhook_url", "").strip()
        if not token or not webhook:
            def show_setup_wizard():
                from tkinter import messagebox
                result = messagebox.askokcancel(
                    "初回セットアップ",
                    "Slack の接続情報が未設定です。\n\n"
                    "設定画面を開いて、Bot Token と Webhook URL を設定してください。\n\n"
                    "設定画面を開きますか？"
                )
                if result:
                    _open_settings(root, cfg, set_status, on_send_refresh, on_recv_refresh)
            root.after(300, show_setup_wizard)

    root.mainloop()
