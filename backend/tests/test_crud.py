"""数据库 CRUD 操作测试 — 覆盖未测试的 User/Session/Analysis/ApiUsage/AuditLog 方法"""

import uuid

import pytest
from auth.password import hash_password
from database.crud import (
    create_analysis_record,
    create_audit_log,
    create_session,
    create_user,
    get_session_by_access_token,
    get_user_analysis_records,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    get_user_usage_stats,
    record_api_usage,
    revoke_user_sessions,
    update_analysis_record,
    update_user_login,
)


class TestUserCRUD:
    """用户 CRUD 操作"""

    @pytest.mark.asyncio
    async def test_create_user(self, db_session):
        user = await create_user(
            db_session,
            email=f"crud_{uuid.uuid4().hex[:6]}@test.com",
            username=f"cruduser_{uuid.uuid4().hex[:6]}",
            hashed_password=hash_password("Test1234!"),
        )
        assert user.id is not None
        assert user.email_verified is False  # 默认未验证

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, db_session, test_user):
        found = await get_user_by_id(db_session, test_user.id)
        assert found is not None
        assert found.email == test_user.email

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, db_session):
        found = await get_user_by_id(db_session, uuid.uuid4())
        assert found is None

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, db_session, test_user):
        found = await get_user_by_email(db_session, test_user.email)
        assert found is not None
        assert found.id == test_user.id

    @pytest.mark.asyncio
    async def test_get_user_by_username(self, db_session, test_user):
        found = await get_user_by_username(db_session, test_user.username)
        assert found is not None
        assert found.id == test_user.id

    @pytest.mark.asyncio
    async def test_update_user_login(self, db_session, test_user):
        old_login = test_user.last_login_at
        await update_user_login(db_session, test_user.id)
        # Core-level update bypasses ORM cache — refresh the object
        await db_session.refresh(test_user)
        assert test_user.last_login_at is not None
        assert test_user.last_login_at != old_login


class TestSessionCRUD:
    """会话管理 CRUD"""

    @pytest.mark.asyncio
    async def test_create_and_get_session(self, db_session, test_user):
        sess = await create_session(
            db_session,
            test_user.id,
            access_token="test_access_token_123",
            refresh_token="test_refresh_token_456",
            ip="127.0.0.1",
            ua="pytest",
        )
        assert sess.id is not None
        assert sess.user_id == test_user.id

        found = await get_session_by_access_token(db_session, "test_access_token_123")
        assert found is not None
        assert found.user.id == test_user.id

    @pytest.mark.asyncio
    async def test_get_session_invalid_token(self, db_session):
        found = await get_session_by_access_token(db_session, "nonexistent_token")
        assert found is None

    @pytest.mark.asyncio
    async def test_revoke_user_sessions(self, db_session, test_user):
        await create_session(db_session, test_user.id, "tok1", "ref1")
        await create_session(db_session, test_user.id, "tok2", "ref2")

        await revoke_user_sessions(db_session, test_user.id)

        # 撤销后应查不到有效会话
        found1 = await get_session_by_access_token(db_session, "tok1")
        found2 = await get_session_by_access_token(db_session, "tok2")
        assert found1 is None
        assert found2 is None


class TestAnalysisRecordCRUD:
    """分析记录 CRUD"""

    @pytest.mark.asyncio
    async def test_create_analysis_record(self, db_session, test_user):
        record = await create_analysis_record(
            db_session,
            test_user.id,
            request_data={"symbols": ["00700"], "market": "hk"},
        )
        assert record.id is not None
        assert record.status == "pending"
        assert record.request["symbols"] == ["00700"]

    @pytest.mark.asyncio
    async def test_update_analysis_record(self, db_session, test_user):
        record = await create_analysis_record(db_session, test_user.id, {"test": True})
        await update_analysis_record(
            db_session,
            record.id,
            status="completed",
            report={"recommendation": "buy"},
        )
        # Core-level update bypasses ORM cache — refresh the object
        await db_session.refresh(record)
        assert record.status == "completed"

    @pytest.mark.asyncio
    async def test_get_user_analysis_records_pagination(self, db_session, test_user):
        for i in range(5):
            await create_analysis_record(db_session, test_user.id, {"index": i})

        records = await get_user_analysis_records(db_session, test_user.id, limit=3, offset=0)
        assert len(records) == 3

        records2 = await get_user_analysis_records(db_session, test_user.id, limit=3, offset=3)
        assert len(records2) == 2


class TestApiUsageCRUD:
    """API 用量统计"""

    @pytest.mark.asyncio
    async def test_record_and_get_usage_stats(self, db_session, test_user):
        await record_api_usage(db_session, test_user.id, "/api/orchestrate", "POST", 200, 1500, 100)
        await record_api_usage(db_session, test_user.id, "/api/chat", "POST", 200, 800, 50)
        await record_api_usage(db_session, test_user.id, "/api/stock/analyze", "POST", 500, 200, 0)

        stats = await get_user_usage_stats(db_session, test_user.id)
        assert stats["total_requests"] == 3
        assert stats["total_tokens"] == 150
        assert stats["avg_duration_ms"] > 0

    @pytest.mark.asyncio
    async def test_usage_stats_empty_user(self, db_session, test_user):
        stats = await get_user_usage_stats(db_session, test_user.id)
        assert stats["total_requests"] == 0
        assert stats["total_tokens"] == 0


class TestAuditLogCRUD:
    """审计日志"""

    @pytest.mark.asyncio
    async def test_create_audit_log(self, db_session, test_user):
        # 仅验证不抛异常且成功写入
        await create_audit_log(
            db_session,
            user_id=test_user.id,
            action="login",
            resource="auth",
            detail={"method": "password"},
            ip="127.0.0.1",
            ua="pytest",
        )
        # 审计日志无直接查询接口，验证不抛异常即可
