import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import jwt
from loguru import logger

_DEFAULT_SECRET = "finagent-pro-jwt-secret-change-in-production"
JWT_SECRET = os.getenv("JWT_SECRET", _DEFAULT_SECRET)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("JWT_ACCESS_EXPIRE_HOURS", "24"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", "30"))


def validate_jwt_config():
    """启动时校验JWT密钥安全性"""
    is_production = os.getenv("ENV", "development").lower() == "production"
    if JWT_SECRET == _DEFAULT_SECRET:
        if is_production:
            raise RuntimeError(
                "生产环境禁止使用默认JWT密钥！请设置 JWT_SECRET 环境变量。"
                " 生成方式: python -c 'import secrets; print(secrets.token_hex(32))'"
            )
        logger.warning(
            "⚠️  JWT_SECRET 使用默认值！生产环境请务必设置随机密钥。"
            " 可通过: export JWT_SECRET=$(python -c 'import secrets; print(secrets.token_hex(32))')"
        )
    if len(JWT_SECRET) < 32:
        if is_production:
            raise RuntimeError("生产环境 JWT_SECRET 长度必须 >= 32 字符")
        logger.warning("⚠️  JWT_SECRET 长度不足32字符，建议使用更长的密钥")


def create_access_token(user_id: uuid.UUID, role: str = "user") -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: uuid.UUID) -> str:
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[Dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
