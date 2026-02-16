"""
プライバシー保護フィルタ: パスワード・機密情報の記録防止

【使用方法】
from common.privacy_guard import PrivacyGuard, PrivacyLevel

# デフォルト（standard）: パスワードフィールドのみフィルタ
guard = PrivacyGuard()

# strict: 全テキスト入力をマスク
guard = PrivacyGuard(PrivacyLevel.STRICT)

# off: フィルタなし
guard = PrivacyGuard(PrivacyLevel.OFF)

# 各メソッド:
guard.is_secure_field("AXSecureTextField")          # True
guard.filter_text_input("password123", is_secure=True)  # None（記録しない）
guard.sanitize_url("https://x.com?token=abc")       # "https://x.com?token=[MASKED]"
guard.mask_value("secret", "AXSecureTextField")      # "[MASKED]"
guard.should_skip_capture("AXSecureTextField", focused=True)  # True
guard.redact_sensitive_patterns("sk-abc123...")       # "[API_KEY]"

【処理内容】
1. PrivacyLevel: standard / strict / off の3段階
2. AXSecureTextField / role_description に "password" を含むフィールドを検出
3. URL のトークン・APIキーパラメータをマスク
4. テキスト内のクレジットカード番号・APIキーパターンを除去
5. secureフィールドフォーカス中のスクリーンショットをスキップ

【依存】
Python標準ライブラリのみ (re, enum, urllib.parse)
"""

import re
from enum import Enum
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


class PrivacyLevel(Enum):
    STANDARD = "standard"
    STRICT = "strict"
    OFF = "off"


# URL内のマスク対象パラメータ名
_SENSITIVE_URL_PARAMS = {
    "token", "access_token", "api_key", "apikey", "api-key",
    "password", "passwd", "secret", "session", "session_id",
    "jwt", "auth", "authorization", "key", "private_key",
    "client_secret", "refresh_token", "id_token",
}

# テキスト内の機密パターン（正規表現）
_SENSITIVE_PATTERNS = [
    # クレジットカード番号（4桁×4、スペースorハイフン区切り）
    (re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'), "[CARD_NUMBER]"),
    # OpenAI APIキー
    (re.compile(r'sk-[A-Za-z0-9]{20,}'), "[API_KEY]"),
    # GitHub トークン
    (re.compile(r'gh[ps]_[A-Za-z0-9]{36,}'), "[API_KEY]"),
    # Slack トークン
    (re.compile(r'xox[bpras]-[A-Za-z0-9\-]{10,}'), "[API_KEY]"),
    # Google APIキー
    (re.compile(r'AIza[A-Za-z0-9\-_]{35}'), "[API_KEY]"),
    # AWS アクセスキー
    (re.compile(r'AKIA[A-Z0-9]{16}'), "[API_KEY]"),
    # 汎用 Bearer トークン
    (re.compile(r'Bearer\s+[A-Za-z0-9\-._~+/]+=*', re.IGNORECASE), "[BEARER_TOKEN]"),
]

# パスワードフィールド判定キーワード
_PASSWORD_KEYWORDS = ("password", "パスワード", "passwd", "passcode", "pin")


class PrivacyGuard:
    """プライバシー保護フィルタ"""

    def __init__(self, level: PrivacyLevel = PrivacyLevel.STANDARD):
        self.level = level

    def is_secure_field(self, role: str, role_description: Optional[str] = None) -> bool:
        """AXSecureTextField またはパスワード関連フィールドかを判定"""
        if role == "AXSecureTextField":
            return True
        if role_description:
            desc_lower = role_description.lower()
            if any(kw in desc_lower for kw in _PASSWORD_KEYWORDS):
                return True
        return False

    def filter_text_input(self, text: str, is_secure: bool) -> Optional[str]:
        """テキスト入力のフィルタ。None=記録しない"""
        if self.level == PrivacyLevel.OFF:
            return text
        if self.level == PrivacyLevel.STRICT:
            return "[TEXT_INPUT]"
        # standard: secureフィールドなら記録しない
        if is_secure:
            return None
        return self.redact_sensitive_patterns(text)

    def sanitize_url(self, url: str) -> str:
        """URLから機密パラメータをマスク"""
        if self.level == PrivacyLevel.OFF:
            return url
        if not url:
            return url
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query, keep_blank_values=True)
            changed = False
            for key in params:
                if key.lower() in _SENSITIVE_URL_PARAMS:
                    params[key] = ["[MASKED]"]
                    changed = True
            if self.level == PrivacyLevel.STRICT:
                # strict: 全パラメータをマスク
                for key in params:
                    params[key] = ["[MASKED]"]
                changed = bool(params)
            if changed:
                # parse_qsはリスト値を返すので、単一値に戻す
                parts = [f"{k}={v[0]}" for k, v in params.items()]
                new_query = "&".join(parts)
                return urlunparse(parsed._replace(query=new_query))
            return url
        except Exception:
            return url

    def mask_value(self, value: Optional[str], role: str, role_description: Optional[str] = None) -> Optional[str]:
        """AXValueのマスキング"""
        if self.level == PrivacyLevel.OFF:
            return value
        if value is None:
            return None
        if self.level == PrivacyLevel.STRICT:
            return "[MASKED]"
        # standard: secureフィールドのみマスク
        if self.is_secure_field(role, role_description):
            return "[MASKED]"
        return value

    def should_skip_capture(self, role: str, focused: bool, role_description: Optional[str] = None) -> bool:
        """スクリーンショット撮影をスキップすべきか"""
        if self.level == PrivacyLevel.OFF:
            return False
        if focused and self.is_secure_field(role, role_description):
            return True
        return False

    def redact_sensitive_patterns(self, text: str) -> str:
        """テキスト内の機密パターン（APIキー、カード番号等）を除去"""
        if self.level == PrivacyLevel.OFF:
            return text
        result = text
        for pattern, replacement in _SENSITIVE_PATTERNS:
            result = pattern.sub(replacement, result)
        return result
