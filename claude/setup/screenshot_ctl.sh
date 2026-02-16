#!/bin/bash
# スクリーンショットデーモン 制御スクリプト
#
# 処理内容:
#   LaunchAgentを使ったデーモンのstart/stop/restart/status/logs制御
#
# 使用方法:
#   ./claude/setup/screenshot_ctl.sh start    # デーモン起動
#   ./claude/setup/screenshot_ctl.sh stop     # デーモン停止
#   ./claude/setup/screenshot_ctl.sh restart  # デーモン再起動
#   ./claude/setup/screenshot_ctl.sh status   # 状態確認
#   ./claude/setup/screenshot_ctl.sh logs     # ログ表示

set -euo pipefail

LABEL="com.user.screenshot_daemon"
PLIST_SRC="$(cd "$(dirname "$0")" && pwd)/com.user.screenshot_daemon.plist"
PLIST_DST="$HOME/Library/LaunchAgents/${LABEL}.plist"
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
LOG_FILE="${PROJECT_DIR}/claude/98_tmp/daemon.log"

ensure_plist() {
    if [ ! -f "$PLIST_DST" ]; then
        echo "Error: plist not installed. Run install.sh first."
        exit 1
    fi
}

case "${1:-help}" in
    start)
        ensure_plist
        if launchctl list "$LABEL" &>/dev/null; then
            echo "Daemon is already running."
        else
            launchctl load "$PLIST_DST"
            echo "Daemon started."
        fi
        ;;
    stop)
        ensure_plist
        if launchctl list "$LABEL" &>/dev/null; then
            launchctl unload "$PLIST_DST"
            echo "Daemon stopped."
        else
            echo "Daemon is not running."
        fi
        ;;
    restart)
        "$0" stop
        sleep 1
        "$0" start
        ;;
    status)
        if launchctl list "$LABEL" &>/dev/null; then
            echo "Daemon is RUNNING"
            launchctl list "$LABEL"
        else
            echo "Daemon is NOT running"
        fi

        # スクリーンショット数
        SS_DIR="${PROJECT_DIR}/claude/10_raw/screenshots"
        if [ -d "$SS_DIR" ]; then
            SS_COUNT=$(ls "$SS_DIR"/screenshot_*.png 2>/dev/null | wc -l | tr -d ' ')
            echo "Screenshots: ${SS_COUNT} files"
        fi

        # 解析ファイル
        AN_DIR="${PROJECT_DIR}/claude/10_raw/analysis"
        if [ -d "$AN_DIR" ]; then
            AN_COUNT=$(ls "$AN_DIR"/analysis_*.jsonl 2>/dev/null | wc -l | tr -d ' ')
            echo "Analysis files: ${AN_COUNT} files"
        fi
        ;;
    logs)
        if [ -f "$LOG_FILE" ]; then
            tail -f "$LOG_FILE"
        else
            echo "No log file found at: $LOG_FILE"
        fi
        ;;
    help|*)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the screenshot daemon"
        echo "  stop     - Stop the screenshot daemon"
        echo "  restart  - Restart the screenshot daemon"
        echo "  status   - Show daemon status and file counts"
        echo "  logs     - Tail the daemon log file"
        ;;
esac
