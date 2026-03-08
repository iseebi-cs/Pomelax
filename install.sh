#!/bin/bash
# pomelax インストールスクリプト
# 用途: SD から Linux 環境へ本体をコピーし、デスクトップ統合を行う

set -e

# Root実行ガード
if [ "$EUID" -eq 0 ]; then
  echo "[ERROR] このスクリプトは root で実行しないでください。"
  echo "通常ユーザーで実行してください。"
  exit 1
fi

print_usage() {
  echo "使用法:"
  echo "  インストール: $0 [--install-deps]"
  echo "  アンインストール: $0 --uninstall [--purge]"
  echo ""
  echo "オプション:"
  echo "  --install-deps  依存パッケージを自動インストール"
  echo "  --uninstall     pomelax をアンインストール"
  echo "  --purge         設定ファイルも含めて完全削除（--uninstall と併用）"
}

# オプション解析
INSTALL_DEPS=false
UNINSTALL=false
PURGE=false

for arg in "$@"; do
  case "$arg" in
    --install-deps)
      INSTALL_DEPS=true
      ;;
    --uninstall)
      UNINSTALL=true
      ;;
    --purge)
      PURGE=true
      ;;
    *)
      echo "不明なオプション: $arg"
      echo ""
      print_usage
      exit 1
      ;;
  esac
done

if [ "$PURGE" = true ] && [ "$UNINSTALL" != true ]; then
  echo "エラー: --purge は --uninstall と併用してください。"
  echo ""
  print_usage
  exit 1
fi

if [ "$UNINSTALL" = true ] && [ "$INSTALL_DEPS" = true ]; then
  echo "エラー: --install-deps と --uninstall は同時に指定できません。"
  echo ""
  print_usage
  exit 1
fi

# root 実行禁止（/root 配下への誤インストール防止）
if [ "$EUID" -eq 0 ]; then
  echo "[ERROR] root では実行しないでください。通常ユーザーで実行してください。"
  exit 1
fi

# アンインストールモード
if [ "$UNINSTALL" = true ]; then
  echo "============================================"
  echo " pomelax アンインストーラー"
  echo "============================================"
  echo ""

  INSTALL_DIR="$HOME/Apps/pomelax"
  CONFIG_DIR="$HOME/.config/pomelax"
  STATE_DIR="$HOME/.local/share/pomelax"
  DESKTOP_FILE="$HOME/.local/share/applications/pomelax.desktop"

  if [ "$PURGE" = true ]; then
    echo "[PURGE モード] 設定ファイルも含めて完全削除します"
  else
    echo "[通常モード] 本体のみ削除、設定ファイルは保持します"
    echo "完全削除する場合: $0 --uninstall --purge"
  fi
  echo ""

  # 削除確認
  read -p "本当にアンインストールしますか？ [y/N]: " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "アンインストールをキャンセルしました。"
    exit 0
  fi

  echo ""

  # 本体削除
  if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
    echo "[削除] $INSTALL_DIR"
  else
    echo "[スキップ] インストールディレクトリが見つかりません: $INSTALL_DIR"
  fi

  # .desktop ファイル削除
  if [ -f "$DESKTOP_FILE" ]; then
    rm -f "$DESKTOP_FILE"
    echo "[削除] $DESKTOP_FILE"
  else
    echo "[スキップ] desktop ファイルが見つかりません: $DESKTOP_FILE"
  fi

  # デスクトップのアイコンも削除（XDG優先、なければ ~/Desktop）
  DESKTOP_DIR="$HOME/Desktop"
  if command -v xdg-user-dir >/dev/null 2>&1; then
    XDG_DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
    if [ -n "$XDG_DESKTOP_DIR" ]; then
      DESKTOP_DIR="$XDG_DESKTOP_DIR"
    fi
  fi
  DESKTOP_ICON="$DESKTOP_DIR/pomelax.desktop"
  if [ -f "$DESKTOP_ICON" ]; then
    rm -f "$DESKTOP_ICON"
    echo "[削除] $DESKTOP_ICON"
  fi

  # --purge の場合は設定と状態も削除
  if [ "$PURGE" = true ]; then
    if [ -d "$CONFIG_DIR" ]; then
      rm -rf "$CONFIG_DIR"
      echo "[削除] $CONFIG_DIR"
    else
      echo "[スキップ] 設定ディレクトリが見つかりません: $CONFIG_DIR"
    fi

    if [ -d "$STATE_DIR" ]; then
      rm -rf "$STATE_DIR"
      echo "[削除] $STATE_DIR"
    else
      echo "[スキップ] 状態ディレクトリが見つかりません: $STATE_DIR"
    fi
  else
    echo "[保持] 設定: $CONFIG_DIR"
    echo "[保持] 状態: $STATE_DIR"
  fi

  echo ""
  echo "============================================"
  echo " アンインストール完了"
  echo "============================================"

  if [ "$PURGE" != true ]; then
    echo ""
    echo "設定ファイルを手動で削除する場合："
    echo "  rm -rf $CONFIG_DIR"
    echo "  rm -rf $STATE_DIR"
  fi

  exit 0
fi

# SD_PATH の決定（install.sh の配置場所から特定）
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
SD_PATH=$(cd "$SCRIPT_DIR/.." && pwd)
DELETE_TARGET="$SCRIPT_DIR"  # 削除対象は install.sh が存在するディレクトリそのもの

echo "============================================"
echo " pomelax インストーラー"
echo "============================================"
echo "SD パス: $DELETE_TARGET"
echo ""

# 誤爆防止チェック（強化版）
# 1. 基本チェック: 空・/・/home でないこと
if [ -z "$DELETE_TARGET" ] || [ "$DELETE_TARGET" = "/" ] || [ "$DELETE_TARGET" = "/home" ]; then
  echo "[ERROR] DELETE_TARGET が不正です（基本チェック失敗）。"
  exit 1
fi

# 2. install.sh の存在確認
if [ ! -f "$DELETE_TARGET/install.sh" ]; then
  echo "[ERROR] DELETE_TARGET に install.sh が見つかりません。"
  echo "予期しない場所で実行されている可能性があります。"
  exit 1
fi

# 3. ディレクトリ名が 'pomelax' と完全一致するか確認
if [ "$(basename "$DELETE_TARGET")" != "pomelax" ]; then
  echo "[ERROR] DELETE_TARGET のパス末尾が 'pomelax' ではありません。"
  echo "実際のパス: $DELETE_TARGET"
  exit 1
fi

# 4. pomelax 本体ディレクトリらしさを検証
if [ ! -f "$DELETE_TARGET/main.py" ] || [ ! -f "$DELETE_TARGET/run.sh" ] || [ ! -f "$DELETE_TARGET/requirements.txt" ]; then
  echo "[ERROR] DELETE_TARGET が pomelax 本体ディレクトリではない可能性があります。"
  echo "必要ファイル(main.py/run.sh/requirements.txt)が揃っていません。"
  exit 1
fi

# 5. readlink で正規化して危険域チェック
REAL_PATH=$(readlink -f "$DELETE_TARGET" 2>/dev/null || echo "$DELETE_TARGET")
if [[ "$REAL_PATH" == "/" ]] || [[ "$REAL_PATH" == "/home" ]] || \
   [[ "$REAL_PATH" == "/usr" ]] || [[ "$REAL_PATH" == "/etc" ]] || \
   [[ "$REAL_PATH" == "/bin" ]] || [[ "$REAL_PATH" == "/sbin" ]]; then
  echo "[ERROR] DELETE_TARGET が危険な領域です: $REAL_PATH"
  exit 1
fi

# インストール先
INSTALL_DIR="$HOME/Apps/pomelax"
CONFIG_DIR="$HOME/.config/pomelax"
DESKTOP_FILE="$HOME/.local/share/applications/pomelax.desktop"

# 1. 本体ディレクトリ作成
echo "[1/6] インストールディレクトリを作成中..."
mkdir -p "$INSTALL_DIR"

# 2. ファイルをコピー
echo "[2/6] ファイルをコピー中..."
# tests/ ディレクトリやその他全てのファイルを含めてコピー
cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"
# install.sh 自体はインストール先に不要なので削除
rm -f "$INSTALL_DIR/install.sh"

# 3. run.sh に実行権限付与
echo "[3/6] run.sh に実行権限を付与中..."
chmod +x "$INSTALL_DIR/run.sh"

# 4. config ディレクトリ作成
echo "[4/6] config ディレクトリを作成中..."
mkdir -p "$CONFIG_DIR"

# 5. .desktop ファイル生成（絶対パスで）
echo "[5/6] デスクトップエントリを作成中..."
mkdir -p "$(dirname "$DESKTOP_FILE")"

ICON_PATH="$INSTALL_DIR/icon.png"
if [ ! -f "$ICON_PATH" ]; then
  ICON_PATH="utilities-terminal"  # デフォルトアイコン
fi

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=pomelax
Comment=Slack client for low-spec Linux
Exec=$INSTALL_DIR/run.sh
Terminal=false
Type=Application
Icon=$ICON_PATH
Categories=Utility;Network;
EOF

chmod +x "$DESKTOP_FILE"

# デスクトップにもアイコンを配置（XDG優先、なければ ~/Desktop）
DESKTOP_DIR="$HOME/Desktop"
if command -v xdg-user-dir >/dev/null 2>&1; then
  XDG_DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
  if [ -n "$XDG_DESKTOP_DIR" ]; then
    DESKTOP_DIR="$XDG_DESKTOP_DIR"
  fi
fi
if [ -d "$DESKTOP_DIR" ]; then
  cp "$DESKTOP_FILE" "$DESKTOP_DIR/pomelax.desktop"
  chmod +x "$DESKTOP_DIR/pomelax.desktop"
  echo "[INFO] デスクトップにアイコンを配置しました: $DESKTOP_DIR/pomelax.desktop"
else
  echo "[INFO] デスクトップディレクトリが見つかりません。スキップします。"
fi

# 6. 依存パッケージ確認
echo "[6/6] 依存パッケージを確認中..."

if ! python3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)"; then
  echo "[ERROR] Python 3.9 以上が必要です。現在: $(python3 --version 2>&1)"
  exit 1
fi

check_python_package() {
  python3 -c "import $1" 2>/dev/null
}

if ! check_python_package "requests"; then
  if [ "$INSTALL_DEPS" = true ]; then
    echo "[INFO] requests パッケージをインストール中..."

    # pip の存在確認
    if ! python3 -m pip --version &>/dev/null; then
      echo "[ERROR] pip が見つかりません。"
      echo ""
      echo "pip をインストールしてください："
      echo "  sudo apt install python3-pip"
      echo "または："
      echo "  curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py"
      echo "  python3 get-pip.py --user"
    elif python3 -m pip install --user requests; then
      echo "[OK] 依存パッケージのインストールが完了しました。"
    else
      echo "[WARNING] pip install に失敗しました。以下を手動で実行してください："
      echo "  python3 -m pip install --user -r $INSTALL_DIR/requirements.txt"
    fi
  else
    echo "[WARNING] 依存パッケージが不足しています。"
    echo "以下を実行してください："
    echo "  python3 -m pip install --user -r $INSTALL_DIR/requirements.txt"
    echo "または："
    echo "  python3 -m pip install --break-system-packages -r $INSTALL_DIR/requirements.txt"
    echo ""
    echo "または --install-deps オプション付きで再実行してください："
    echo "  $0 --install-deps"
  fi
fi

# インストール完了確認
if [ -d "$INSTALL_DIR" ] && [ -d "$CONFIG_DIR" ] && [ -f "$DESKTOP_FILE" ]; then
  echo ""
  echo "============================================"
  echo " インストール完了"
  echo "============================================"
  echo "本体: $INSTALL_DIR"
  echo "設定: $CONFIG_DIR"
  echo ".desktop: $DESKTOP_FILE"
  echo ""

  # SD 削除確認
  if [ -d "$DELETE_TARGET" ]; then
    echo "SD 内の pomelax ディレクトリを削除しますか？"
    echo "削除対象: $DELETE_TARGET"
    read -p "[y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      # 再度誤爆防止チェック（起動時と同じ厳格な検証）
      SAFE_TO_DELETE=true

      # 基本チェック
      if [ "$DELETE_TARGET" = "/" ] || [ "$DELETE_TARGET" = "/home" ]; then
        SAFE_TO_DELETE=false
      fi

      # install.sh 存在確認（削除前なので存在するはず）
      if [ ! -f "$DELETE_TARGET/install.sh" ]; then
        SAFE_TO_DELETE=false
      fi

      # ディレクトリ名チェック
      if [ "$(basename "$DELETE_TARGET")" != "pomelax" ]; then
        SAFE_TO_DELETE=false
      fi

      # pomelax 本体ディレクトリらしさを検証
      if [ ! -f "$DELETE_TARGET/main.py" ] || [ ! -f "$DELETE_TARGET/run.sh" ] || [ ! -f "$DELETE_TARGET/requirements.txt" ]; then
        SAFE_TO_DELETE=false
      fi

      # 危険域チェック
      REAL_PATH=$(readlink -f "$DELETE_TARGET" 2>/dev/null || echo "$DELETE_TARGET")
      if [[ "$REAL_PATH" == "/" ]] || [[ "$REAL_PATH" == "/home" ]] || \
         [[ "$REAL_PATH" == "/usr" ]] || [[ "$REAL_PATH" == "/etc" ]]; then
        SAFE_TO_DELETE=false
      fi

      if [ "$SAFE_TO_DELETE" = true ]; then
        rm -rf "$DELETE_TARGET"
        echo "[OK] SD から削除しました。"
      else
        echo "[ERROR] 安全性チェックに失敗したため、削除を中断しました。"
        echo "pomelax 本体ディレクトリと確認できた場合のみ手動削除してください。"
        echo "手動で削除する場合: rm -rf $DELETE_TARGET"
      fi
    else
      echo "[INFO] SD はそのままにします。後で手動で削除できます。"
    fi
  fi

  echo ""
  echo "デスクトップアイコンから pomelax を起動して動作確認してください。"
  echo ""
else
  echo "[ERROR] インストールに失敗しました。"
  exit 1
fi
