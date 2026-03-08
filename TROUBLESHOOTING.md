# TROUBLESHOOTING

pomelax の使用中に発生する可能性のある問題と解決方法をまとめています。

---

## pip 関連

### `--break-system-packages` が使えない

**症状**: `pip install` 時に `--break-system-packages` オプションがエラーになる

**原因**: Debian bullseye など古いバージョンの pip ではこのオプションが未対応

**解決策**: `--user` オプションを使用してユーザー領域にインストール

```bash
python3 -m pip install --user requests
```

または requirements.txt 全体をインストール：

```bash
python3 -m pip install --user -r requirements.txt
```

---

## Slack 設定関連

### channel_id をチャンネル名で入れてしまった

**症状**: メッセージ取得時にエラーが発生する

**原因**: `channel_id` には `#general` のようなチャンネル名ではなく、`C` から始まる ID が必要

**解決策**:

1. チャンネルの URL 末尾を確認：`https://app.slack.com/client/T12345678/C98765432` の `C98765432` 部分
2. またはチャンネル詳細の一番下にある「チャンネル ID」をコピー
3. `config.json` の `channel_id` に正しい ID を記入

---

### Bot をチャンネルに招待し忘れた

**症状**: 履歴取得時に「チャンネルが見つかりません」または「権限がありません」エラー

**原因**: Bot がチャンネルのメンバーになっていない

**解決策**: 対象チャンネルで以下を実行

```
/invite @アプリ名
```

Bot がチャンネルに参加すると、過去のメッセージも取得できるようになります。

---

## SD カード・インストール関連

### install.sh が実行できない（Permission denied）

**症状**: `./install.sh` を実行すると Permission denied エラーが出る

**原因**: SD カードが vfat でマウントされており、noexec オプションが有効

**解決策**: bash コマンド経由で実行

```bash
bash install.sh
```

または：

```bash
bash install.sh --install-deps
```

---

### root で install.sh を実行してしまった

**症状**: `/root` 配下にインストールされてしまい、通常ユーザーで起動できない

**原因**: root 権限で実行したため、`$HOME` が `/root` になった

**解決策**:

1. root でインストールされたファイルを削除：

```bash
sudo rm -rf /root/Apps/pomelax
sudo rm -rf /root/.config/pomelax
sudo rm -f /root/.local/share/applications/pomelax.desktop
```

2. 通常ユーザーで再インストール：

```bash
bash install.sh --install-deps
```

または、ファイルの所有権を修正（非推奨）：

```bash
sudo chown -R $USER:$USER ~/Apps/pomelax
sudo chown -R $USER:$USER ~/.config/pomelax
```

---

## UI・表示関連

### ウィンドウサイズが画面に収まらない

**症状**: ポメラ DM250 など解像度が低い端末でウィンドウが画面からはみ出す

**原因**: デフォルトのウィンドウサイズが大きすぎる

**解決策**: `dev/ui.py` のウィンドウサイズを調整

`ui.py` の該当箇所（ウィンドウ生成部分）で幅・高さを小さくする：

```python
# 例：1024x600 → 800x480 に変更
self.root.geometry("800x480")
```

編集後、アプリを再起動してください。

---

## その他

### 動作が遅い・固まる

**症状**: メッセージ取得や送信時に固まる、または非常に遅い

**原因**:
- ネットワーク接続が不安定
- Slack API のレート制限に引っかかっている
- 大量のメッセージ・ファイルを一度に取得しようとしている

**解決策**:
- Wi-Fi 接続を確認
- しばらく時間を置いてから再試行
- 必要に応じて取得するメッセージ数を制限

---

### 添付ファイルがダウンロードできない

**症状**: テキストファイル以外の添付ファイルが表示されない

**原因**: pomelax はテキストファイル（.txt / .md / text/plain / text/markdown）のみ対応

**解決策**: 画像・PDF・ZIP 等は非対応です。これらのファイルは Slack Web またはモバイルアプリから確認してください。

---

## サポート

上記で解決しない場合は、GitHub の Issues でお問い合わせください：
[https://github.com/[ユーザー名]/pomelax/issues](https://github.com/[ユーザー名]/pomelax/issues)

報告時は以下の情報を含めてください：
- OS・ディストリビューション（例：Debian bullseye、Raspberry Pi OS 等）
- Python バージョン（`python3 --version`）
- エラーメッセージの全文
