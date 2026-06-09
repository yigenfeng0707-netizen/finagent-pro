import akshare as ak
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Callable


class MarketTools:
    """Agent工具库 - 市场数据查询和计算工具"""

    @staticmethod
    def get_stock_price(symbol: str, market: str = "hk") -> Dict[str, Any]:
        try:
            if market == "hk":
                df = ak.stock_hk_spot_em()
                row = df[df['代码'] == symbol]
                if row.empty:
                    return {"error": f"未找到股票 {symbol}"}
                row = row.iloc[0]
                return {
                    "symbol": symbol,
                    "name": row.get('名称', ''),
                    "price": round(float(row.get('最新价', 0)), 2),
                    "change_pct": round(float(row.get('涨跌幅', 0)), 2),
                    "volume": int(row.get('成交量', 0)),
                    "turnover": round(float(row.get('成交额', 0)), 2)
                }
            return {"error": f"不支持的市场: {market}"}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_technical_indicators(symbol: str, market: str = "hk", days: int = 180) -> Dict[str, Any]:
        try:
            end = pd.Timestamp.now()
            start = end - pd.Timedelta(days=days)
            if market == "hk":
                df = ak.stock_hk_hist(symbol=symbol, period="daily",
                                      start_date=start.strftime("%Y%m%d"),
                                      end_date=end.strftime("%Y%m%d"))
            else:
                return {"error": f"不支持的市场: {market}"}
            if df.empty:
                return {"error": "无法获取数据"}
            close = df['收盘']
            ma5 = close.rolling(5).mean().iloc[-1]
            ma20 = close.rolling(20).mean().iloc[-1]
            ma60 = close.rolling(60).mean().iloc[-1]
            exp1 = close.ewm(span=12, adjust=False).mean()
            exp2 = close.ewm(span=26, adjust=False).mean()
            macd_dif = exp1.iloc[-1] - exp2.iloc[-1]
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            bb_mid = close.rolling(20).mean().iloc[-1]
            bb_std = close.rolling(20).std().iloc[-1]
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            change_pct = (latest['收盘'] - prev['收盘']) / prev['收盘'] * 100
            volatility = close.pct_change().std() * 100
            return {
                "symbol": symbol,
                "current_price": round(float(latest['收盘']), 2),
                "change_pct": round(float(change_pct), 2),
                "volume": int(latest['成交量']),
                "ma5": round(float(ma5), 2) if not pd.isna(ma5) else None,
                "ma20": round(float(ma20), 2) if not pd.isna(ma20) else None,
                "ma60": round(float(ma60), 2) if not pd.isna(ma60) else None,
                "macd_dif": round(float(macd_dif), 4) if not pd.isna(macd_dif) else None,
                "rsi": round(float(rsi.iloc[-1]), 2) if not pd.isna(rsi.iloc[-1]) else None,
                "bb_upper": round(float(bb_mid + 2 * bb_std), 2),
                "bb_lower": round(float(bb_mid - 2 * bb_std), 2),
                "volatility": round(float(volatility), 2),
                "high_52w": round(float(df['最高'].max()), 2),
                "low_52w": round(float(df['最低'].min()), 2),
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def calculate_var(returns: List[float], confidence: float = 0.95) -> float:
        if not returns:
            return 0.0
        return float(np.percentile(returns, (1 - confidence) * 100))

    @staticmethod
    def get_portfolio_risk(symbols: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            portfolio_returns = []
            stock_risks = []
            for item in symbols:
                sym = item['symbol']
                market = item.get('market', 'hk')
                weight = item.get('weight', 1.0 / len(symbols))
                if market == "hk":
                    df = ak.stock_hk_hist(symbol=sym, period="daily", start_date="20240101")
                else:
                    continue
                if df.empty:
                    continue
                df['return'] = df['收盘'].pct_change()
                rets = df['return'].dropna().tolist()
                if rets:
                    vol = float(np.std(rets) * np.sqrt(252) * 100)
                    var95 = float(MarketTools.calculate_var(rets, 0.95) * 100)
                    mdd = float(((df['收盘'] / df['收盘'].cummax()) - 1).min() * 100)
                    stock_risks.append({
                        "symbol": sym, "weight": weight,
                        "volatility": round(vol, 2), "var_95": round(var95, 2),
                        "max_drawdown": round(mdd, 2)
                    })
                    portfolio_returns.extend([r * weight for r in rets])
            if not portfolio_returns:
                return {"error": "无法计算组合风险"}
            pvol = float(np.std(portfolio_returns) * np.sqrt(252) * 100)
            pvar = float(MarketTools.calculate_var(portfolio_returns, 0.95) * 100)
            if pvol < 15:
                risk_level = "低风险"
            elif pvol < 25:
                risk_level = "中风险"
            else:
                risk_level = "高风险"
            return {
                "portfolio_volatility": round(pvol, 2),
                "portfolio_var_95": round(pvar, 2),
                "risk_level": risk_level,
                "stock_risks": stock_risks
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
        }
