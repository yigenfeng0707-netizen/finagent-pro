from typing import Any, Callable, Dict, List

import akshare as ak
import numpy as np
import pandas as pd
from loguru import logger


class MarketTools:
    """Agent工具库 - 市场数据查询和计算工具"""

    @staticmethod
    def get_stock_price(symbol: str, market: str = "hk") -> Dict[str, Any]:
        try:
            if market == "hk":
                df = ak.stock_hk_spot_em()
                row = df[df["代码"] == symbol]
                if row.empty:
                    return {"error": f"未找到股票 {symbol}"}
                row = row.iloc[0]
                return {
                    "symbol": symbol,
                    "name": row.get("名称", ""),
                    "price": round(float(row.get("最新价", 0)), 2),
                    "change_pct": round(float(row.get("涨跌幅", 0)), 2),
                    "volume": int(row.get("成交量", 0)),
                    "turnover": round(float(row.get("成交额", 0)), 2),
                }
            return {"error": f"不支持的市场: {market}"}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_technical_indicators(symbol: str, market: str = "hk", days: int = 180) -> Dict[str, Any]:
        try:
            from services.market_data import MarketDataService

            svc = MarketDataService()
            df = svc.get_stock_history(symbol, market, days=days)
            if df is None or df.empty:
                return {"error": "无法获取数据"}

            indicators = svc.calculate_technical_indicators(df)
            if not indicators:
                return {"error": "计算指标失败"}

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            change_pct = (latest["收盘"] - prev["收盘"]) / prev["收盘"] * 100 if prev["收盘"] != 0 else 0
            volatility = df["收盘"].pct_change().std() * 100

            return {
                "symbol": symbol,
                "current_price": round(float(latest["收盘"]), 2),
                "change_pct": round(float(change_pct), 2),
                "volume": int(latest["成交量"]),
                **indicators,  # ma5, ma10, ma20, ma60, macd_dif, macd_dea, macd_hist, rsi, bb_upper, bb_mid, bb_lower
                "volatility": round(float(volatility), 2),
                "high_52w": round(float(df["最高"].max()), 2),
                "low_52w": round(float(df["最低"].min()), 2),
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_fund_flow(symbol: str, market: str = "hk") -> Dict[str, Any]:
        """获取个股资金流向数据"""
        try:
            import akshare as ak

            df = ak.stock_hk_fund_flow_detail_em(symbol=symbol)
            if df is None or df.empty:
                return {"net_inflow": 0, "direction": "无数据"}

            latest = df.iloc[0] if len(df) > 0 else None
            if latest is None:
                return {"net_inflow": 0, "direction": "无数据"}

            # Parse net inflow from the dataframe columns
            net_inflow = 0
            for col in df.columns:
                if "净流入" in str(col) or "net" in str(col).lower():
                    try:
                        net_inflow = float(latest[col])
                    except (ValueError, TypeError):
                        pass
                    break

            return {
                "net_inflow": net_inflow,
                "direction": "净流入" if net_inflow > 0 else "净流出" if net_inflow < 0 else "持平",
                "data_date": str(latest.get("日期", "")) if "日期" in df.columns else "",
            }
        except Exception as e:
            logger.warning(f"资金流向数据获取失败({symbol}): {e}")
            return {"net_inflow": 0, "direction": "无数据", "error": str(e)}

    @staticmethod
    def calculate_var(returns: List[float], confidence: float = 0.95) -> float:
        if not returns:
            return 0.0
        return float(np.percentile(returns, (1 - confidence) * 100))

    @staticmethod
    def get_portfolio_risk(symbols: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            # 收集各股票收益率数据
            stock_returns: Dict[str, pd.Series] = {}
            stock_risks = []
            for item in symbols:
                sym = item["symbol"]
                market = item.get("market", "hk")
                weight = item.get("weight", 1.0 / len(symbols))
                if market == "hk":
                    end = pd.Timestamp.now()
                    start = end - pd.Timedelta(days=180)
                    df = ak.stock_hk_hist(
                        symbol=sym, period="daily", start_date=start.strftime("%Y%m%d"), end_date=end.strftime("%Y%m%d")
                    )
                else:
                    continue
                if df.empty:
                    continue
                df["return"] = df["收盘"].pct_change()
                rets = df["return"].dropna()
                if not rets.empty:
                    stock_returns[sym] = rets.reset_index(drop=True)
                    vol = float(rets.std() * np.sqrt(252) * 100)
                    var95 = float(np.percentile(rets, 5) * 100)
                    mdd = float(((df["收盘"] / df["收盘"].cummax()) - 1).min() * 100)
                    stock_risks.append(
                        {
                            "symbol": sym,
                            "weight": weight,
                            "volatility": round(vol, 2),
                            "var_95": round(var95, 2),
                            "max_drawdown": round(mdd, 2),
                        }
                    )

            if not stock_returns:
                return {"error": "无法计算组合风险"}

            # 使用协方差矩阵计算组合风险（正确方法）
            returns_df = pd.DataFrame(stock_returns)
            weights = np.array(
                [item.get("weight", 1.0 / len(symbols)) for item in symbols if item["symbol"] in stock_returns]
            )
            # 归一化权重
            weights = weights / weights.sum()

            cov_matrix = returns_df.cov() * 252  # 年化协方差矩阵
            portfolio_variance = float(weights @ cov_matrix.values @ weights)
            pvol = float(np.sqrt(portfolio_variance) * 100)

            # 组合收益率序列用于VaR计算
            portfolio_returns_series = returns_df @ weights
            pvar = float(np.percentile(portfolio_returns_series, 5) * 100)

            # CVaR: expected loss given loss exceeds VaR
            portfolio_returns = portfolio_returns_series.values
            var_threshold = np.percentile(portfolio_returns, 5)
            tail_returns = portfolio_returns[portfolio_returns <= var_threshold]
            cvar = float(tail_returns.mean() * 100) if len(tail_returns) > 0 else pvar

            # Sharpe Ratio (annualized, risk-free rate = 3%)
            risk_free_rate = 0.03
            annual_return = float(np.mean(portfolio_returns) * 252)
            annual_vol = float(np.sqrt(portfolio_variance))  # already from covariance matrix
            sharpe_ratio = round((annual_return - risk_free_rate) / annual_vol, 2) if annual_vol > 0 else 0

            if pvol < 15:
                risk_level = "低风险"
            elif pvol < 25:
                risk_level = "中风险"
            else:
                risk_level = "高风险"

            return {
                "portfolio_volatility": round(pvol, 2),
                "portfolio_var_95": round(pvar, 2),
                "cvar_95": round(cvar, 2),
                "sharpe_ratio": sharpe_ratio,
                "annual_return": round(annual_return * 100, 2),
                "annual_volatility": round(annual_vol * 100, 2),
                "var_time_horizon": "1-day",
                "risk_level": risk_level,
                "risk_level_num": 25 if risk_level == "低风险" else 55 if risk_level == "中风险" else 80,
                "stock_risks": stock_risks,
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_fundamentals(symbol: str, market: str = "hk") -> Dict[str, Any]:
        """获取股票基本面数据（估值指标、财务摘要）"""
        try:
            from services.market_data import MarketDataService

            svc = MarketDataService()
            info = svc.get_stock_info(symbol, market)
            if "error" in info:
                return info

            # 尝试获取额外基本面数据
            pe_ratio = None
            pb_ratio = None
            try:
                if market == "hk":
                    df_profile = ak.stock_hk_profile_em(symbol=symbol)
                    if df_profile is not None and not df_profile.empty:
                        row = df_profile.iloc[0]
                        for col in df_profile.columns:
                            col_lower = str(col).lower()
                            if "市盈率" in str(col) or "pe" in col_lower:
                                try:
                                    pe_ratio = round(float(row[col]), 2)
                                except (ValueError, TypeError):
                                    pass
                            elif "市净率" in str(col) or "pb" in col_lower:
                                try:
                                    pb_ratio = round(float(row[col]), 2)
                                except (ValueError, TypeError):
                                    pass
            except Exception:
                pass

            return {
                "symbol": symbol,
                "name": info.get("name", ""),
                "current_price": info.get("current_price"),
                "market_cap": info.get("turnover"),
                "pe_ratio": pe_ratio,
                "pb_ratio": pb_ratio,
                "volatility": info.get("volatility"),
                "high_52w": info.get("high_52w"),
                "low_52w": info.get("low_52w"),
                "ma5": info.get("ma5"),
                "ma20": info.get("ma20"),
                "ma60": info.get("ma60"),
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def stress_test(symbols: List[Dict[str, Any]], scenarios: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """压力测试 — 模拟极端市场情景下的组合损失"""
        try:
            if scenarios is None:
                scenarios = [
                    {"name": "2008金融危机", "shock_pct": -0.40},
                    {"name": "2015股灾", "shock_pct": -0.30},
                    {"name": "2020疫情冲击", "shock_pct": -0.25},
                    {"name": "温和回调", "shock_pct": -0.10},
                ]

            stock_returns: Dict[str, pd.Series] = {}
            for item in symbols:
                sym = item["symbol"]
                market = item.get("market", "hk")
                if market == "hk":
                    end = pd.Timestamp.now()
                    start = end - pd.Timedelta(days=365)
                    df = ak.stock_hk_hist(
                        symbol=sym, period="daily", start_date=start.strftime("%Y%m%d"), end_date=end.strftime("%Y%m%d")
                    )
                    if not df.empty:
                        df["return"] = df["收盘"].pct_change()
                        rets = df["return"].dropna()
                        if not rets.empty:
                            stock_returns[sym] = rets.reset_index(drop=True)

            if not stock_returns:
                return {"error": "无法获取数据执行压力测试"}

            weights = np.array([item.get("weight", 1.0 / len(symbols)) for item in symbols if item["symbol"] in stock_returns])
            weights = weights / weights.sum()

            results = []
            for scenario in scenarios:
                shock = scenario["shock_pct"]
                # 基于历史波动率调整冲击
                returns_df = pd.DataFrame(stock_returns)
                portfolio_vol = float((returns_df @ weights).std() * np.sqrt(252))

                # 情景损失 = 冲击百分比 × 组合权重
                portfolio_loss = shock * 100
                # 考虑分散化效应的调整损失
                diversified_loss = portfolio_loss * (1 - 0.2 * min(len(stock_returns) - 1, 3) / 3)

                results.append({
                    "scenario": scenario["name"],
                    "shock_pct": f"{shock * 100:.0f}%",
                    "portfolio_loss_pct": round(diversified_loss, 2),
                    "recovery_days_est": round(abs(diversified_loss) / (portfolio_vol * 100 / np.sqrt(252)) * 1.5, 0) if portfolio_vol > 0 else 0,
                })

            return {
                "stress_test_results": results,
                "portfolio_annual_volatility": round(float((returns_df @ weights).std() * np.sqrt(252) * 100), 2),
                "worst_case_loss": min(r["portfolio_loss_pct"] for r in results),
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def markowitz_optimize(symbols: List[Dict[str, Any]], risk_free_rate: float = 0.03) -> Dict[str, Any]:
        """马科维茨均值-方差优化 — 计算最优资产配置权重"""
        try:
            stock_returns: Dict[str, pd.Series] = {}
            for item in symbols:
                sym = item["symbol"]
                market = item.get("market", "hk")
                if market == "hk":
                    end = pd.Timestamp.now()
                    start = end - pd.Timedelta(days=365)
                    df = ak.stock_hk_hist(
                        symbol=sym, period="daily", start_date=start.strftime("%Y%m%d"), end_date=end.strftime("%Y%m%d")
                    )
                    if not df.empty:
                        df["return"] = df["收盘"].pct_change()
                        rets = df["return"].dropna()
                        if not rets.empty:
                            stock_returns[sym] = rets.reset_index(drop=True)

            if len(stock_returns) < 2:
                return {"error": "至少需要2只股票才能进行马科维茨优化"}

            returns_df = pd.DataFrame(stock_returns)
            mean_returns = returns_df.mean() * 252  # 年化收益
            cov_matrix = returns_df.cov() * 252  # 年化协方差

            n_assets = len(stock_returns)
            # 生成随机有效前沿上的组合
            n_portfolios = 1000
            results_list = []
            for _ in range(n_portfolios):
                w = np.random.random(n_assets)
                w = w / np.sum(w)
                port_return = float(w @ mean_returns.values)
                port_vol = float(np.sqrt(w @ cov_matrix.values @ w))
                sharpe = (port_return - risk_free_rate) / port_vol if port_vol > 0 else 0
                results_list.append({
                    "weights": w.tolist(),
                    "return": round(port_return * 100, 2),
                    "volatility": round(port_vol * 100, 2),
                    "sharpe": round(sharpe, 2),
                })

            # 找到最大夏普比率组合
            max_sharpe = max(results_list, key=lambda x: x["sharpe"])
            # 找到最小波动率组合
            min_vol = min(results_list, key=lambda x: x["volatility"])

            symbol_list = list(stock_returns.keys())
            optimal_weights = {
                symbol_list[i]: round(max_sharpe["weights"][i] * 100, 1) for i in range(n_assets)
            }
            conservative_weights = {
                symbol_list[i]: round(min_vol["weights"][i] * 100, 1) for i in range(n_assets)
            }

            return {
                "optimal_portfolio": {
                    "weights": optimal_weights,
                    "expected_return": max_sharpe["return"],
                    "volatility": max_sharpe["volatility"],
                    "sharpe_ratio": max_sharpe["sharpe"],
                },
                "conservative_portfolio": {
                    "weights": conservative_weights,
                    "expected_return": min_vol["return"],
                    "volatility": min_vol["volatility"],
                    "sharpe_ratio": min_vol["sharpe"],
                },
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_tool_registry() -> Dict[str, Callable]:
        return {
            "get_stock_price": MarketTools.get_stock_price,
            "get_technical_indicators": MarketTools.get_technical_indicators,
            "calculate_var": MarketTools.calculate_var,
            "get_portfolio_risk": MarketTools.get_portfolio_risk,
            "get_fund_flow": MarketTools.get_fund_flow,
            "get_fundamentals": MarketTools.get_fundamentals,
            "stress_test": MarketTools.stress_test,
            "markowitz_optimize": MarketTools.markowitz_optimize,
        }
