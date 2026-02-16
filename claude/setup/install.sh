#!/bin/bash
# スクリーンショットデーモン 初回セットアップスクリプト
#
# 処理内容:
#   依存パッケージのインストール（pyobjc含む）、ディレクトリ作成、LaunchAgent plistの配置
#
# 使用方法:
#   ./claude/setup/install.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
LABEL="com.user.screenshot_daemon"
PLIST_SRC="$SCRIPT_DIR/com.user.screenshot_daemon.plist"
PLIST_DST="$HOME/Library/LaunchAgents/${LABEL}.plist"

echo "=== Screenshot Daemon Installer ==="
echo "Project directory: $PROJECT_DIR"
echo ""

# 1. Python依存パッケージのインストール（pyobjcフレームワーク含む）
echo "[1/4] Installing Python dependencies..."
pip install -r "$SCRIPT_DIR/requirements.txt"
echo ""

# 2. ディレクトリ作成
echo "[2/4] Creating directories..."
mkdir -p "$PROJECT_DIR/claude/10_raw/screenshots"
mkdir -p "$PROJECT_DIR/claude/10_raw/analysis"
mkdir -p "$PROJECT_DIR/claude/98_tmp"
echo "  Created: claude/10_raw/screenshots/"
echo "  Created: claude/10_raw/analysis/"
echo "  Created: claude/98_tmp/"
echo ""

# 3. .envファイルの確認
echo "[3/4] Checking .env configuration..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "  WARNING: .env file not found!"
    echo "  Create $PROJECT_DIR/.env with:"
    echo "    OPENAI_API_KEY=sk-your-key-here"
    echo ""
else
    if grep -q "OPENAI_API_KEY" "$PROJECT_DIR/.env"; then
        echo "  .env found with OPENAI_API_KEY"
    else
        echo "  WARNING: OPENAI_API_KEY not found in .env"
    fi
fi
echo ""

# 4. LaunchAgent plistの配置
echo "[4/4] Installing LaunchAgent plist..."
PYTHON_PATH=$(which python3)
mkdir -p "$HOME/Library/LaunchAgents"

sed -e "s|__PYTHON_PATH__|${PYTHON_PATH}|g" \
    -e "s|__PROJECT_DIR__|${PROJECT_DIR}|g" \
    "$PLIST_SRC" > "$PLIST_DST"

echo "  Installed: $PLIST_DST"
echo "  Python: $PYTHON_PATH"
echo ""

# 制御スクリプトに実行権限付与
chmod +x "$SCRIPT_DIR/screenshot_ctl.sh"

echo "=== Installation complete ==="
echo ""
echo "Next steps:"
echo "  1. Ensure .env has OPENAI_API_KEY set"
echo "  2. Grant Screen Recording permission to Terminal/iTerm"
echo "     (System Settings > Privacy & Security > Screen Recording)"
echo "  3. Grant Accessibility permission to Terminal/iTerm"
echo "     (System Settings > Privacy & Security > Accessibility)"
echo "  4. Start daemon: ./claude/setup/screenshot_ctl.sh start"
echo "  5. Check status: ./claude/setup/screenshot_ctl.sh status"
echo "  6. View logs:    ./claude/setup/screenshot_ctl.sh logs"
