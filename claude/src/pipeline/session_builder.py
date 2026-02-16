"""
セッションビルダー: CaptureRecord のストリームを Session に区切る

【使用方法】
from pipeline.session_builder import SessionBuilder
from pipeline.models import CaptureRecord

builder = SessionBuilder(gap_seconds=300, max_records=50)
for record in records:
    session = builder.add_record(record)
    if session:
        process(session)
# 残りのバッファをフラッシュ
last = builder.flush()
if last:
    process(last)

【処理内容】
CaptureRecord を順次受け取り、以下の条件でセッション区切りを判定:
  1. 前回レコードから gap_seconds 以上の時間経過
  2. アプリ名が変化
  3. バッファ内レコード数が max_records に到達
区切り検出時、バッファ内レコードを Session にまとめて返す。

【依存】
pipeline.models (CaptureRecord, Session)
Python 標準ライブラリ (datetime, uuid)
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pipeline.models import CaptureRecord, Session


class SessionBuilder:
    def __init__(self, gap_seconds: int = 300, max_records: int = 50):
        self._gap_seconds = gap_seconds
        self._max_records = max_records
        self._buffer: List[CaptureRecord] = []
        self._last_app: Optional[str] = None

    def add_record(self, record: CaptureRecord) -> Optional[Session]:
        current_app = record.app.get("name", "")
        result = None

        if self._buffer:
            should_split = False

            # 時間gap チェック
            try:
                prev_ts = _parse_timestamp(self._buffer[-1].timestamp)
                curr_ts = _parse_timestamp(record.timestamp)
                if (curr_ts - prev_ts).total_seconds() >= self._gap_seconds:
                    should_split = True
            except (ValueError, TypeError):
                pass

            # アプリ変化チェック
            if current_app != self._last_app:
                should_split = True

            # 最大件数チェック
            if len(self._buffer) >= self._max_records:
                should_split = True

            if should_split:
                result = self._build_session(self._buffer)
                self._buffer = []

        self._buffer.append(record)
        self._last_app = current_app
        return result

    def flush(self) -> Optional[Session]:
        if not self._buffer:
            return None
        session = self._build_session(self._buffer)
        self._buffer = []
        self._last_app = None
        return session

    def _build_session(self, records: List[CaptureRecord]) -> Session:
        app_name = records[0].app.get("name", "unknown")
        return Session(
            session_id=str(uuid.uuid4()),
            app_name=app_name,
            records=list(records),
            start_time=records[0].timestamp,
            end_time=records[-1].timestamp,
        )


def _parse_timestamp(ts: str) -> datetime:
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    return datetime.fromisoformat(ts)
