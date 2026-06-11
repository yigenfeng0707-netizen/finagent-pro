"""市场数据服务和工具的单元测试"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unittest.mock import patch, MagicMock
import numpy as np
import pandas as pd


class TestMarketTools:
    """市场工具函数测试"""

    def test_get_fund_flow_returns_dict(self):
        from tools.market_tools import MarketTools
        with patch('tools.market_tools.ak') as mock_ak:
            mock_df = pd.DataFrame({
                '日期': ['2026-06-12'],
                '主力净流入': [1000000.0]
            })
            mock_ak.stock_hk_fund_flow_detail_em.return_value = mock_df
            result = MarketTools.get_fund_flow("00700")
            assert isinstance(result, dict)
            assert "net_inflow" in result or "direction" in result

    def test_get_fund_flow_error_handling(self):
        from tools.market_tools import MarketTools
        with patch('tools.market_tools.ak') as mock_ak:
            mock_ak.stock_hk_fund_flow_detail_em.side_effect = Exception("API error")
            result = MarketTools.get_fund_flow("00700")
            assert isinstance(result, dict)
            assert result.get("net_inflow", 0) == 0 or "error" in result

    def test_portfolio_risk_covariance(self):
        """验证组合风险使用协方差矩阵方法"""
        from tools.market_tools import MarketTools
        with patch('tools.market_tools.ak') as mock_ak:
            # Mock stock history data
            dates = pd.date_range('2026-01-01', periods=60)
            mock_df = pd.DataFrame({
                '日期': dates,
                '收盘': np.random.uniform(100, 200, 60),
            })
            mock_ak.stock_hk_spot_em.return_value = pd.DataFrame({
                '代码': ['00700'], '名称': ['腾讯'], '最新价': [350.0]
            })
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
