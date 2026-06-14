"""认证依赖测试 — get_current_user, get_optional_user, require_admin"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


class TestGetCurrentUser:
    """get_current_user 依赖"""

    @pytest.mark.asyncio
    async def test_no_credentials_raises_401(self):
        from auth.dependencies import get_current_user

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=None, db=AsyncMock())
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        from auth.dependencies import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.token.here")

        with patch("auth.dependencies.verify_token", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials=creds, db=AsyncMock())
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_rejected(self):
        from auth.dependencies import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="refresh.token.here")

        with patch("auth.dependencies.verify_token", return_value={"type": "refresh", "sub": "some-uuid"}):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials=creds, db=AsyncMock())
            assert exc_info.value.status_code == 401
            assert "token type" in exc_info.value.detail.lower() or "Invalid" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_revoked_session_raises_401(self):
        from auth.dependencies import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid.access.token")

        with patch("auth.dependencies.verify_token", return_value={"type": "access", "sub": "some-uuid"}):
            with patch("auth.dependencies.get_session_by_access_token", new_callable=AsyncMock, return_value=None):
                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user(credentials=creds, db=AsyncMock())
                assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_auth_returns_user(self):
        from auth.dependencies import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid.access.token")
        mock_user = MagicMock()
        mock_user.id = "test-user-id"

        mock_session = MagicMock()
        mock_session.user = mock_user

        with patch("auth.dependencies.verify_token", return_value={"type": "access", "sub": "test-user-id"}):
            with patch(
                "auth.dependencies.get_session_by_access_token",
                new_callable=AsyncMock,
                return_value=mock_session,
            ):
                user = await get_current_user(credentials=creds, db=AsyncMock())
                assert user.id == "test-user-id"


class TestGetOptionalUser:
    """get_optional_user 依赖 — 无凭证时返回 None"""

    @pytest.mark.asyncio
    async def test_no_credentials_returns_none(self):
        from auth.dependencies import get_optional_user

        result = await get_optional_user(credentials=None, db=AsyncMock())
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_token_returns_none(self):
        from auth.dependencies import get_optional_user
        from fastapi.security import HTTPAuthorizationCredentials

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad.token")

        with patch("auth.dependencies.verify_token", return_value=None):
            result = await get_optional_user(credentials=creds, db=AsyncMock())
            assert result is None

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self):
        import uuid

        from auth.dependencies import get_optional_user
        from fastapi.security import HTTPAuthorizationCredentials

        uid = uuid.uuid4()
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="good.token")
        mock_user = MagicMock()
        mock_user.id = uid

        with patch("auth.dependencies.verify_token", return_value={"type": "access", "sub": str(uid)}):
            with patch("auth.dependencies.get_user_by_id", new_callable=AsyncMock, return_value=mock_user):
                result = await get_optional_user(credentials=creds, db=AsyncMock())
                assert result is not None
                assert result.id == uid


class TestRequireAdmin:
    """require_admin 依赖 — 角色校验"""

    def test_admin_passes(self):
        from auth.dependencies import require_admin

        admin_user = MagicMock()
        admin_user.role = "admin"
        result = require_admin(user=admin_user)
        assert result.role == "admin"

    def test_non_admin_raises_403(self):
        from auth.dependencies import require_admin

        regular_user = MagicMock()
        regular_user.role = "user"

        with pytest.raises(HTTPException) as exc_info:
            require_admin(user=regular_user)
        assert exc_info.value.status_code == 403
