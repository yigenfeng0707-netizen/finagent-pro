from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

from database.models import User, Session, AnalysisRecord, Subscription, AuditLog, ApiUsage


# ── User ──

async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, email: str, username: str, hashed_password: str) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        username=username,
        hashed_password=hashed_password,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_login(db: AsyncSession, user_id: uuid.UUID):
    await db.execute(
        User.__table__.update().where(User.id == user_id).values(last_login_at=datetime.utcnow())
    )
    await db.commit()


# ── Session ──

async def create_session(db: AsyncSession, user_id: uuid.UUID, access_token: str,
                         refresh_token: str, ip: str = None, ua: str = None, hours: int = 24) -> Session:
    sess = Session(
        id=uuid.uuid4(),
        user_id=user_id,
        access_token=access_token,
        refresh_token=refresh_token,
        ip_address=ip,
        user_agent=ua,
        expires_at=datetime.utcnow() + timedelta(hours=hours),
    )
    db.add(sess)
    await db.commit()
    return sess


async def get_session_by_access_token(db: AsyncSession, token: str) -> Optional[Session]:
    result = await db.execute(
        select(Session).options(selectinload(Session.user)).where(
            Session.access_token == token,
            Session.revoked == False,
            Session.expires_at > datetime.utcnow()
        )
    )
    return result.scalar_one_or_none()


async def revoke_user_sessions(db: AsyncSession, user_id: uuid.UUID):
    await db.execute(
        Session.__table__.update().where(Session.user_id == user_id).values(revoked=True)
    )
    await db.commit()


# ── Analysis Record ──

async def create_analysis_record(db: AsyncSession, user_id: uuid.UUID, request_data: Dict[str, Any]) -> AnalysisRecord:
    record = AnalysisRecord(
        id=uuid.uuid4(),
        user_id=user_id,
        request=request_data,
        status="pending",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def update_analysis_record(db: AsyncSession, record_id: uuid.UUID, **kwargs):
    await db.execute(
        AnalysisRecord.__table__.update().where(AnalysisRecord.id == record_id).values(**kwargs)
    )
    await db.commit()


async def get_user_analysis_records(db: AsyncSession, user_id: uuid.UUID, limit: int = 20, offset: int = 0) -> List[AnalysisRecord]:
    result = await db.execute(
        select(AnalysisRecord).where(AnalysisRecord.user_id == user_id)
        .order_by(AnalysisRecord.created_at.desc())
        .limit(limit).offset(offset)
    )
    return list(result.scalars().all())


# ── API Usage ──

async def record_api_usage(db: AsyncSession, user_id: uuid.UUID, endpoint: str,
                           method: str, status_code: int, duration_ms: int = None, tokens: int = 0):
    usage = ApiUsage(
        id=uuid.uuid4(),
        user_id=user_id,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        duration_ms=duration_ms,
        tokens_used=tokens,
    )
    db.add(usage)
    await db.commit()


async def get_user_usage_stats(db: AsyncSession, user_id: uuid.UUID, since: datetime = None) -> Dict:
    if since is None:
        since = datetime.utcnow() - timedelta(days=30)
    result = await db.execute(
        select(
            func.count(ApiUsage.id).label("total_requests"),
            func.sum(ApiUsage.tokens_used).label("total_tokens"),
            func.avg(ApiUsage.duration_ms).label("avg_duration_ms"),
        ).where(ApiUsage.user_id == user_id, ApiUsage.created_at >= since)
    )
    row = result.one()
    return {
        "total_requests": row.total_requests or 0,
        "total_tokens": row.total_tokens or 0,
        "avg_duration_ms": round(row.avg_duration_ms, 2) if row.avg_duration_ms else 0,
    }


# ── Audit Log ──

async def create_audit_log(db: AsyncSession, user_id: uuid.UUID, action: str,
                           resource: str = None, resource_id: str = None,
                           detail: Dict = None, ip: str = None, ua: str = None):
    log = AuditLog(
        id=uuid.uuid4(),
        user_id=user_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        detail=detail,
        ip_address=ip,
        user_agent=ua,
    )
    db.add(log)
    await db.commit()
