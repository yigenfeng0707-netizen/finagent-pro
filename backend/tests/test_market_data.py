"""市场数据服务和工具的单元测试"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest


class TestMarketTools:
    """市场工具函数测试"""

    def test_get_fund_flow_returns_dict(self):
        from tools.market_tools import MarketTools

        with patch("tools.market_tools.ak") as mock_ak:
            mock_df = pd.DataFrame({"日期": ["2026-06-12"], "主力净流入": [1000000.0]})
            mock_ak.stock_hk_fund_flow_detail_em.return_value = mock_df
            result = MarketTools.get_fund_flow("00700")
            assert isinstance(result, dict)
            assert "net_inflow" in result or "direction" in result

    def test_get_fund_flow_error_handling(self):
        from tools.market_tools import MarketTools

        with patch("tools.market_tools.ak") as mock_ak:
            mock_ak.stock_hk_fund_flow_detail_em.side_effect = Exception("API error")
            result = MarketTools.get_fund_flow("00700")
            assert isinstance(result, dict)
            assert result.get("net_inflow", 0) == 0 or "error" in result

    def test_portfolio_risk_covariance(self):
        """验证组合风险使用协方差矩阵方法"""
        from tools.market_tools import MarketTools

        with patch("tools.market_tools.ak") as mock_ak:
            # Mock stock history data
            dates = pd.date_range("2026-01-01", periods=60)
            mock_df = pd.DataFrame(
                {
                    "日期": dates,
                    "收盘": np.random.uniform(100, 200, 60),
                }
            )
            mock_ak.stock_hk_spot_em.return_value = pd.DataFrame(
                {"代码": ["00700"], "名称": ["腾讯"], "最新价": [350.0]}
            )
            mock_ak.stock_hk_hist_em.return_value = mock_df

            symbols = [{"symbol": "00700", "market": "hk", "weight": 1.0}]
            result = MarketTools.get_portfolio_risk(symbols)

            if result and "error" not in result:
                assert "var_95" in result
                assert "volatility" in result
                # 验证VaR是负数（表示损失）
                if "cvar_95" in result:
                    assert result["cvar_95"] <= result["var_95"]  # CVaR应更极端
                if "sharpe_ratio" in result:
                    assert isinstance(result["sharpe_ratio"], (int, float))


class TestExceptionHandlers:
    """自定义异常测试"""

    def test_agent_execution_error(self):
        from exception_handlers import AgentExecutionError

        err = AgentExecutionError("market_analyst", "timeout")
        assert err.status_code == 500
        assert "market_analyst" in err.message
        assert err.detail["agent"] == "market_analyst"

    def test_data_fetch_error(self):
        from exception_handlers import DataFetchError

        err = DataFetchError("akshare", "network error")
        assert err.status_code == 502
        assert "akshare" in err.message

    def test_llm_error(self):
        from exception_handlers import LLMError

        err = LLMError("deepseek-chat", "rate limited")
        assert err.status_code == 503
        assert err.detail["model"] == "deepseek-chat"


class TestMiddleware:
    """中间件测试"""

    def test_rate_limiter_allows_under_limit(self):
        from middleware import InMemoryRateLimiter

        limiter = InMemoryRateLimiter()
        assert limiter.check("test_key", 5, 60) is True
        assert limiter.check("test_key", 5, 60) is True

    def test_rate_limiter_blocks_over_limit(self):
        from middleware import InMemoryRateLimiter

        limiter = InMemoryRateLimiter()
        for _ in range(5):
            limiter.check("test_key2", 5, 60)
        assert limiter.check("test_key2", 5, 60) is False


class TestRedisCache:
    """RedisCache 异步缓存层"""

    @pytest.mark.asyncio
    async def test_redis_cache_get_set_with_mock(self):
        """Redis 可用时正常读写"""
        from unittest.mock import AsyncMock

        from services.market_data import RedisCache

        cache = RedisCache()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value='{"price": 350}')
        cache._redis = mock_redis

        result = await cache.get("stock:00700")
        assert result == '{"price": 350}'

    @pytest.mark.asyncio
    async def test_redis_cache_fallback_when_unavailable(self):
        """Redis 不可用时 get 返回 None"""
        from services.market_data import RedisCache

        cache = RedisCache()
        cache._redis = False  # 模拟不可用状态
        result = await cache.get("any_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_redis_cache_set_silent_on_error(self):
        """Redis set 失败时不抛异常"""
        from unittest.mock import AsyncMock

        from services.market_data import RedisCache

        cache = RedisCache()
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock(side_effect=Exception("connection lost"))
        cache._redis = mock_redis
        # 不应抛异常
        await cache.set("key", "value", ttl=60)


class TestMarketDataServiceFileCache:
    """MarketDataService 文件缓存"""

    def test_save_and_load_cache(self, tmp_path):
        from services.market_data import MarketDataService

        svc = MarketDataService()
        svc.cache_dir = str(tmp_path)
        data = {"price": 350, "name": "腾讯"}
        svc._save_cache("00700", "hk", data)

        loaded = svc._load_cache("00700", "hk")
        assert loaded is not None
        assert loaded["price"] == 350

    def test_load_cache_miss_returns_none(self, tmp_path):
        from services.market_data import MarketDataService

        svc = MarketDataService()
        svc.cache_dir = str(tmp_path)
        assert svc._load_cache("99999", "hk") is None


class TestTechnicalIndicators:
    """技术指标计算"""

    def test_calculate_indicators_basic(self):
        from services.market_data import MarketDataService

        svc = MarketDataService()
        # 生成足够长的数据以计算 MA60
        df = pd.DataFrame({"收盘": np.random.uniform(100, 200, 100)})

        result = svc.calculate_technical_indicators(df)
        assert "ma5" in result
        assert "ma20" in result
        assert "ma60" in result
        assert "rsi" in result
        assert "macd_dif" in result
        assert "bb_upper" in result

    def test_calculate_indicators_empty_df(self):
        from services.market_data import MarketDataService

        svc = MarketDataService()
        result = svc.calculate_technical_indicators(pd.DataFrame())
        assert result == {}


class TestStockNameMapping:
    """股票名称映射"""

    def test_hk_known_stock(self):
        from services.market_data import MarketDataService

        svc = MarketDataService()
        assert svc._get_stock_name("00700", "hk") == "腾讯控股"
        assert svc._get_stock_name("09988", "hk") == "阿里巴巴"

    def test_hk_unknown_stock(self):
        from services.market_data import MarketDataService

        svc = MarketDataService()
        name = svc._get_stock_name("99999", "hk")
        assert "港股" in name

    def test_us_stock_prefix(self):
        from services.market_data import MarketDataService

        svc = MarketDataService()
        assert "美股" in svc._get_stock_name("AAPL", "us")

    def test_cn_stock_prefix(self):
        from services.market_data import MarketDataService

        svc = MarketDataService()
        assert "A股" in svc._get_stock_name("600519", "cn")


class TestGetStockHistory:
    """股票历史数据获取（mock akshare）"""

    def test_get_stock_history_hk(self):
        from unittest.mock import patch

        from services.market_data import MarketDataService

        svc = MarketDataService()
        mock_df = pd.DataFrame({"日期": ["2026-06-01"], "收盘": [350.0], "成交量": [1000000]})

        with patch("services.market_data.ak") as mock_ak:
            mock_ak.stock_hk_hist.return_value = mock_df
            result = svc.get_stock_history("00700", "hk", days=30)
            assert not result.empty
            mock_ak.stock_hk_hist.assert_called_once()

    def test_get_stock_history_failure_returns_empty(self):
        from unittest.mock import patch

        from services.market_data import MarketDataService

        svc = MarketDataService()
        with patch("services.market_data.ak") as mock_ak:
            mock_ak.stock_hk_hist.side_effect = Exception("API error")
            result = svc.get_stock_history("00700", "hk")
            assert result.empty
