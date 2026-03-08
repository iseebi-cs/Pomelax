# pomelax

低スペック Linux 端末（例：ポメラ DM250 上の Debian）で、Slack をブラウザ無しで軽量に扱い、テキストを送受信してローカルに保存できるアプリです。原本はローカルに保存し、Slack は配送路として扱います。

## できること

- **送信**: ローカルの .txt / .md ファイルを Incoming Webhook で Slack に投稿
- **受信**: Slack チャンネルからメッセージ・添付ファイル（text/plain, text/markdown）を取得してローカルに保存
- **設定**: 設定画面で Token / Webhook / フォルダを設定。接続テストで動作確認
- テキストのみ扱い、画像・PDF 等は非対応（軽量性のため）

## 対応環境

- Linux 専用（低スペック Linux 端末全般 - ポメラ DM250、Raspberry Pi 等）
- Python 3.9 以上
- Windows 版の配布・サポートは対象外

## 導入の流れ

**推奨フロー（外部マシン経由）**：

1. 外部マシン（Windows/Mac 等）で [Slack App を作成](#slack-app-準備)しトークンを取得
2. `config.json` にトークン・`channel_id`・Webhook URL を記入（最終配置先: `~/.config/pomelax/config.json`）
3. pomelax フォルダごと SD カードにコピー
4. ポメラ（または対象の Linux 端末）に SD を挿して `bash install.sh` を実行

Wi-Fi 経由での git clone も可能ですが、config.json へのトークン記入が手間なため、外部マシンで準備してから SD カード経由で転送する方法を推奨します。

## 前提パッケージ

pomelax の実行には以下が必要です：

| パッケージ | 用途 | インストール方法 |
|-----------|------|-----------------|
| python3 | Python 実行環境（3.9 以上 / Debian bullseye 想定） | `sudo apt install python3` |
| python3-pip | Python パッケージマネージャー | `sudo apt install python3-pip` |
| python3-tk | tkinter（GUI ライブラリ） | `sudo apt install python3-tk` |
| requests | Slack API 通信（pip でインストール） | `python3 -m pip install --user requests` |

**インストール済みか確認**:

```bash
python3 --version          # Python のバージョン確認
python3 -m pip --version   # pip の存在確認
python3 -c "import tkinter"  # tkinter の存在確認
python3 -c "import requests" # requests の存在確認
```

## セットアップ

### 1. 依存のインストール

```bash
python3 -m pip install -r requirements.txt
```

（tkinter は Python 標準ライブラリのため不要。Linux では `python3-tk` パッケージが必要な場合あり）

**Debian bullseye 等で `--break-system-packages` が使えない場合**：

```bash
# --user オプションで個別にインストール
python3 -m pip install --user requests
```

### 2. 設定

`config.example.json` を参考に、`~/.config/pomelax/config.json` を作成してください。初回起動時はディレクトリが自動作成される場合があります。

```bash
mkdir -p ~/.config/pomelax
cp config.example.json ~/.config/pomelax/config.json
# エディタで Token, Webhook URL, Channel ID などを設定
```

### 3. 起動

```bash
python main.py
```

### 4. キー操作

| キー | 動作 |
|------|------|
| ↑↓ | 一覧の項目移動 |
| Enter | 選択・プレビュー表示 |
| S | 送信（送信タブ）または 保存（受信タブ） |
| R | 一覧更新 |
| Q | 終了 |

設定は「設定」ボタンから。送信元フォルダは「フォルダ」ボタンで選択できます。

## Slack App 準備

### 必要な権限（Bot Token）

- `channels:history` … チャンネル履歴の取得
- `files:read` … 添付ファイルの取得

送信は Incoming Webhook を使うため、`chat:write` は不要です。最小限のスコープで運用できます。

### 手順

1. [Slack API](https://api.slack.com/apps) でアプリを作成
2. Bot Token を発行（OAuth & Permissions）
3. 上記スコープを追加
4. **重要**: 受信対象チャンネルに Bot を招待
   - チャンネルで `/invite @アプリ名` を実行
   - 招待しないと履歴取得に失敗します
5. Incoming Webhooks を有効化し、送信用の Webhook URL を取得

### channel_id の確認方法

設定に必要な `channel_id` は、チャンネル名ではなく `C` から始まる ID です：

- **方法 1**: チャンネルの URL 末尾に表示されます
  - 例: `https://app.slack.com/client/T12345678/C98765432` の `C98765432` 部分
- **方法 2**: チャンネル詳細の一番下に表示されます
  - チャンネル名をクリック → 「詳細を表示」→ 下部にある「チャンネル ID」

## 対応 / 非対応形式

| 形式 | 対応 |
|------|------|
| .txt | 送信・受信ともに対応 |
| .md（text/markdown） | 送信・受信ともに対応 |
| text/plain | 受信対応 |
| image/*, PDF, zip, docx 等 | **非対応**（一覧に表示されません） |

## セキュリティ

- **トークン（Bot Token、Webhook URL）を Git にコミットしないでください。**
- `config.json` は `.gitignore` に含まれています。
- 環境変数 `POMELAX_BOT_TOKEN`, `POMELAX_WEBHOOK_URL`, `POMELAX_CHANNEL_ID` で上書き可能（CI や自動化向け）。

## アンインストール

### Linux の場合

SD 内の `install.sh` を使用してアンインストールできます：

```bash
# 本体のみ削除（設定ファイルは保持）
bash install.sh --uninstall

# 完全削除（設定ファイルも削除）
bash install.sh --uninstall --purge
```

または手動で削除：

```bash
rm -rf ~/Apps/pomelax
rm -f ~/.local/share/applications/pomelax.desktop
rm -f "$(xdg-user-dir DESKTOP 2>/dev/null || echo ~/Desktop)/pomelax.desktop"
# 設定も削除する場合
rm -rf ~/.config/pomelax
rm -rf ~/.local/share/pomelax
```

## ライセンス

CC BY-NC 4.0（非営利限定）

詳細は [LICENSE](LICENSE) ファイルを参照してください。
