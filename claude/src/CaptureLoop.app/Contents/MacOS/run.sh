#!/bin/bash
LOGDIR="/Users/kazuyaegusa/KEWORK/8891_screen_shot/claude/src/logs"
cd /Users/kazuyaegusa/KEWORK/8891_screen_shot/claude/src
exec /usr/bin/python3 -u capture_loop.py --trigger event --auto-learn \
    >> "$LOGDIR/capture_loop_stdout.log" \
    2>> "$LOGDIR/capture_loop_stderr.log"
