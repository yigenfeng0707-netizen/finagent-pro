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
        """压力测试 — 基于历史相关性的情景分析

        基于协方差矩阵计算组合在极端情景下的损失，考虑资产间相关性对分散化效应的影响。

        References:
            Basel Committee on Banking Supervision (2009). Principles for Sound Stress Testing Practices
            and Supervision. Bank for International Settlements.
            Kupiec, P. (2000). Stress Testing in a Value at Risk Framework. Journal of Derivatives, 6(1), 7-24.
        """
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

            # 计算协方差矩阵和相关性矩阵
            returns_df = pd.DataFrame(stock_returns)
            cov_matrix = returns_df.cov() * 252  # 年化协方差
            corr_matrix = returns_df.corr()  # 相关系数矩阵

            # 组合年化波动率
            portfolio_vol = float(np.sqrt(weights @ cov_matrix.values @ weights))

            # 计算分散化比率 (Diversification Ratio)
            # DR = (w' * sigma) / sqrt(w' * Sigma * w), 参见 Choueifaty & Coignard (2008)
            individual_vols = returns_df.std().values * np.sqrt(252)
            dr = float((weights * individual_vols).sum() / portfolio_vol) if portfolio_vol > 0 else 1.0

            # 分散化效益 = 1 - 1/DR
            diversification_benefit = 1.0 - 1.0 / dr if dr > 1 else 0.0

            results = []
            for scenario in scenarios:
                shock = scenario["shock_pct"]

                # 方法1：基于历史波动率的情景损失
                # 假设冲击服从正态分布，损失 = shock * 组合beta调整
                # beta = portfolio_vol / market_vol (市场波动率约20%)
                market_vol = 0.20
                beta = portfolio_vol / market_vol if market_vol > 0 else 1.0
                adjusted_shock = shock * beta

                # 方法2：考虑分散化效应
                # 分散化降低损失的程度取决于资产间相关性
                # 相关性越高，分散化效益越低，极端情景下损失越大
                avg_corr = float(corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].mean())
                # 极端情景下相关性趋近1 (相关性聚集效应,参见 Longin & Solnik (2001))
                stress_corr = min(1.0, avg_corr + 0.3)  # 压力相关性 = 正常相关性 + 0.3
                # 分散化调整因子
                diversification_factor = 1.0 - diversification_benefit * (1.0 - stress_corr)
                diversified_loss = adjusted_shock * diversification_factor

                # 恢复时间估计（基于历史均值回归速度）
                mean_daily_return = float(returns_df.mean().mean())
                recovery_days = int(abs(diversified_loss) / (mean_daily_return * 100) * 1.5) if mean_daily_return > 0 else 999

                results.append({
                    "scenario": scenario["name"],
                    "shock_pct": f"{shock * 100:.0f}%",
                    "portfolio_loss_pct": round(diversified_loss * 100, 2),
                    "diversification_adjustment": round((1 - diversification_factor) * 100, 2),
                    "recovery_days_est": min(recovery_days, 999),
                    "stress_correlation": round(stress_corr, 3),
                })

            return {
                "stress_test_results": results,
                "portfolio_annual_volatility": round(portfolio_vol * 100, 2),
                "worst_case_loss": min(r["portfolio_loss_pct"] for r in results),
                "diversification_ratio": round(dr, 3),
                "average_correlation": round(avg_corr, 3),
                "methodology": "covariance-based with correlation clustering adjustment (Longin & Solnik, 2001)",
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def markowitz_optimize(symbols: List[Dict[str, Any]], risk_free_rate: float = 0.03) -> Dict[str, Any]:
        """马科维茨均值-方差优化 — scipy精确求解 + 随机采样有效前沿

        References:
            Markowitz, H. (1952). Portfolio Selection. The Journal of Finance, 7(1), 77-91.
            Merton, R.C. (1972). An Analytic Derivation of the Efficient Frontier.
        """
        try:
            from scipy.optimize import minimize

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
            symbol_list = list(stock_returns.keys())

            # ---- scipy 精确求解 ----
            def portfolio_volatility(w):
                return float(np.sqrt(w @ cov_matrix.values @ w))

            def neg_sharpe(w):
                ret = float(w @ mean_returns.values)
                vol = portfolio_volatility(w)
                return -(ret - risk_free_rate) / vol if vol > 1e-10 else 0

            constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
            bounds = tuple((0.02, 0.60) for _ in range(n_assets))  # 单资产2%-60%
            init_w = np.ones(n_assets) / n_assets

            # 最大夏普比率组合
            opt_sharpe = minimize(neg_sharpe, init_w, method="SLSQP", bounds=bounds, constraints=constraints,
                                  options={"ftol": 1e-10, "maxiter": 500})
            w_sharpe = opt_sharpe.x if opt_sharpe.success else init_w
            w_sharpe = w_sharpe / w_sharpe.sum()

            # 最小波动率组合
            opt_vol = minimize(portfolio_volatility, init_w, method="SLSQP", bounds=bounds, constraints=constraints,
                               options={"ftol": 1e-10, "maxiter": 500})
            w_minvol = opt_vol.x if opt_vol.success else init_w
            w_minvol = w_minvol / w_minvol.sum()

            # ---- 随机采样生成有效前沿（可视化用） ----
            n_portfolios = 2000
            frontier_returns, frontier_vols = [], []
            for _ in range(n_portfolios):
                w = np.random.dirichlet(np.ones(n_assets))
                ret = float(w @ mean_returns.values)
                vol = float(np.sqrt(w @ cov_matrix.values @ w))
                frontier_returns.append(ret)
                frontier_vols.append(vol)

            # 计算精确组合指标
            def compute_metrics(w):
                ret = float(w @ mean_returns.values)
                vol = float(np.sqrt(w @ cov_matrix.values @ w))
                sharpe = (ret - risk_free_rate) / vol if vol > 1e-10 else 0
                return ret, vol, sharpe

            max_sharpe_ret, max_sharpe_vol, max_sharpe_ratio = compute_metrics(w_sharpe)
            min_vol_ret, min_vol_vol, min_vol_sharpe = compute_metrics(w_minvol)

            optimal_weights = {symbol_list[i]: round(float(w_sharpe[i]) * 100, 1) for i in range(n_assets)}
            conservative_weights = {symbol_list[i]: round(float(w_minvol[i]) * 100, 1) for i in range(n_assets)}

            return {
                "optimal_portfolio": {
                    "weights": optimal_weights,
                    "expected_return": round(max_sharpe_ret * 100, 2),
                    "volatility": round(max_sharpe_vol * 100, 2),
                    "sharpe_ratio": round(max_sharpe_ratio, 2),
                    "solver": "scipy-SLSQP",
                },
                "conservative_portfolio": {
                    "weights": conservative_weights,
                    "expected_return": round(min_vol_ret * 100, 2),
                    "volatility": round(min_vol_vol * 100, 2),
                    "sharpe_ratio": round(min_vol_sharpe, 2),
                    "solver": "scipy-SLSQP",
                },
                "efficient_frontier": {
                    "n_samples": n_portfolios,
                    "returns": [round(r * 100, 2) for r in frontier_returns],
                    "volatilities": [round(v * 100, 2) for v in frontier_vols],
                },
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_esg_rating(symbol: str, market: str = "hk") -> Dict[str, Any]:
        """ESG评级查询 — 聚合MSCI/商道融绿/华证三家ESG评级数据

        数据源: AKShare免费接口（底层为东方财富/新浪财经公开API）
        覆盖: MSCI 712只港股 + 商道融绿8200+条 + 华证6250+条
        """
        try:
            result: Dict[str, Any] = {"symbol": symbol, "market": market, "sources": {}}

            # MSCI ESG评级
            try:
                df_msci = ak.stock_esg_msci_sina()
                code = f"{symbol}.HK" if market == "hk" else symbol
                row = df_msci[df_msci["股票代码"] == code]
                if not row.empty:
                    r = row.iloc[0]
                    result["sources"]["msci"] = {
                        "rating": r.get("ESG评分", "N/A"),
                        "environment_score": float(r.get("环境总评", 0)),
                        "social_score": float(r.get("社会责任总评", 0)),
                        "governance_score": float(r.get("治理总评", 0)),
                        "date": str(r.get("评级日期", "")),
                        "source": "MSCI ESG Ratings",
                    }
            except Exception:
                pass

            # 商道融绿ESG评级
            try:
                df_zd = ak.stock_esg_zd_sina()
                code = f"{symbol}.HK" if market == "hk" else symbol
                row = df_zd[df_zd["股票代码"] == code]
                if not row.empty:
                    r = row.iloc[0]
                    def _parse_score(val):
                        try:
                            return float(str(val).split("(")[0])
                        except (ValueError, IndexError):
                            return 0.0
                    def _parse_grade(val):
                        try:
                            return str(val).split("(")[1].rstrip(")")
                        except (IndexError):
                            return str(val)
                    esg_val = r.get("ESG评分", "")
                    result["sources"]["shangdao_ronglv"] = {
                        "overall_score": _parse_score(esg_val),
                        "overall_grade": _parse_grade(esg_val),
                        "environment_score": _parse_score(r.get("环境总评", "")),
                        "environment_grade": _parse_grade(r.get("环境总评", "")),
                        "social_score": _parse_score(r.get("社会责任总评", "")),
                        "social_grade": _parse_grade(r.get("社会责任总评", "")),
                        "governance_score": _parse_score(r.get("治理总评", "")),
                        "governance_grade": _parse_grade(r.get("治理总评", "")),
                        "date": str(r.get("评分日期", "")),
                        "source": "商道融绿ESG评级",
                    }
            except Exception:
                pass

            # 华证ESG评级
            try:
                df_hz = ak.stock_esg_hz_sina()
                code = f"{symbol}.HK" if market == "hk" else symbol
                row = df_hz[df_hz["股票代码"] == code]
                if not row.empty:
                    r = row.iloc[0]
                    result["sources"]["huazheng"] = {
                        "overall_score": float(r.get("ESG评分", 0)),
                        "overall_grade": str(r.get("ESG等级", "")),
                        "environment_score": float(r.get("环境", 0)),
                        "environment_grade": str(r.get("环境等级", "")),
                        "social_score": float(r.get("社会", 0)),
                        "social_grade": str(r.get("社会等级", "")),
                        "governance_score": float(r.get("公司治理", 0)),
                        "governance_grade": str(r.get("公司治理等级", "")),
                        "name": str(r.get("股票名称", "")),
                        "date": str(r.get("日期", "")),
                        "source": "华证ESG评级",
                    }
            except Exception:
                pass

            result["data_sources_count"] = len(result["sources"])
            return result
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_tool_registry() -> Dict[str, Callable]:
        return {
            "get_stock_price": MarketTools.get_stock_price,
            "get_technical_indicators": MarketTools.get_technical_indicators,
            "calculate_var": MarketTools.get_portfolio_risk,
            "get_portfolio_risk": MarketTools.get_portfolio_risk,
            "get_fund_flow": MarketTools.get_fund_flow,
            "get_fundamentals": MarketTools.get_fundamentals,
            "stress_test": MarketTools.stress_test,
            "markowitz_optimize": MarketTools.markowitz_optimize,
            "get_esg_rating": MarketTools.get_esg_rating,
        }
