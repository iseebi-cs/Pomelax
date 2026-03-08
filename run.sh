#!/bin/bash
# pomelax 起動スクリプト
# 依存確認 -> Python 起動

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

# 依存パッケージ確認
check_python_package() {
  python3 -c "import $1" 2>/dev/null
}

if ! check_python_package "requests"; then
  # GUI 環境であれば zenity で通知
  if command -v zenity &> /dev/null; then
    zenity --error --title="pomelax - 依存エラー" \
      --text="依存パッケージが不足しています。\n\n以下を実行してください：\n  python3 -m pip install --user -r $SCRIPT_DIR/requirements.txt\n\nまたは：\n  python3 -m pip install --break-system-packages -r $SCRIPT_DIR/requirements.txt" \
      --width=400
  else
    # ターミナルで通知
    echo "[pomelax] 依存パッケージが不足しています。"
    echo "以下を実行してください："
    echo "  python3 -m pip install --user -r $SCRIPT_DIR/requirements.txt"
    echo "または："
    echo "  python3 -m pip install --break-system-packages -r $SCRIPT_DIR/requirements.txt"
  fi
  exit 1
fi

# tkinter 確認（Python 標準だが、Linux では別パッケージの場合がある）
if ! check_python_package "tkinter"; then
  if command -v zenity &> /dev/null; then
    zenity --error --title="pomelax - 依存エラー" \
      --text="tkinter が見つかりません。\n\n以下を実行してください：\n  sudo apt install python3-tk" \
      --width=400
  else
    echo "[pomelax] tkinter が見つかりません。"
    echo "以下を実行してください："
    echo "  sudo apt install python3-tk"
  fi
  exit 1
fi

# pomelax 起動
cd "$SCRIPT_DIR"
exec python3 main.py
