"""
市场数据服务 - 港股/美股/A股行情数据
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import akshare as ak
import pandas as pd
import redis.asyncio as aioredis
from loguru import logger


class RedisCache:
    """Redis缓存层，带文件缓存降级"""

    def __init__(self):
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            try:
                self._redis = await aioredis.from_url(
                    os.getenv("REDIS_URL", "redis://localhost:6379/0"), socket_connect_timeout=3, decode_responses=True
                )
            except Exception:
                self._redis = False  # Redis不可用，降级到文件缓存
        return self._redis if self._redis is not False else None

    async def get(self, key: str) -> Optional[str]:
        r = await self._get_redis()
        if r:
            try:
                return await r.get(key)
            except Exception:
                pass
        return None

    async def set(self, key: str, value: str, ttl: int = 300):
        r = await self._get_redis()
        if r:
            try:
                await r.setex(key, ttl, value)
            except Exception:
                pass


class MarketDataService:
    """市场数据服务"""

    _cache = RedisCache()

    def __init__(self):
        self.cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, symbol: str, market: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{market}_{symbol}.json")

    def _load_cache(self, symbol: str, market: str, max_age: int = 300) -> Optional[Dict]:
        """加载缓存数据"""
        cache_path = self._get_cache_path(symbol, market)
        if not os.path.exists(cache_path):
            return None

        # 检查缓存是否过期
        mtime = os.path.getmtime(cache_path)
        if datetime.now().timestamp() - mtime > max_age:
            return None

        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_cache(self, symbol: str, market: str, data: Dict):
        """保存缓存数据"""
        cache_path = self._get_cache_path(symbol, market)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)

    def get_stock_history(
        self, symbol: str, market: str = "hk", period: str = "daily", days: int = 180
    ) -> pd.DataFrame:
        """
        获取股票历史数据

        Args:
            symbol: 股票代码
            market: 市场类型 (hk/us/cn)
            period: 周期 (daily/weekly/monthly)
            days: 获取天数

        Returns:
            DataFrame包含历史数据
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            if market == "hk":
                df = ak.stock_hk_hist(
                    symbol=symbol,
                    period=period,
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                )
            elif market == "us":
                df = ak.stock_us_hist(
                    symbol=symbol,
                    period=period,
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                )
            else:  # cn
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period=period,
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                )

            return df

        except Exception as e:
            logger.warning(f"获取历史数据失败: {e}")
            return pd.DataFrame()

    async def get_stock_history_cached(self, symbol: str, market: str = "hk", days: int = 180):
        """带Redis缓存的股票历史数据"""
        cache_key = f"stock_history:{market}:{symbol}:{days}"

        # Try Redis cache first
        cached = await self._cache.get(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                df = pd.DataFrame(data)
                return df
            except Exception:
                pass

        # Fallback to direct API call
        df = self.get_stock_history(symbol, market, days=days)

        # Store in cache
        if df is not None and not df.empty:
            try:
                # Convert datetime columns to string for JSON serialization
                df_copy = df.copy()
                for col in df_copy.columns:
                    if "date" in col.lower() or "日期" in col:
                        df_copy[col] = df_copy[col].astype(str)
                await self._cache.set(cache_key, df_copy.to_json(orient="records"), ttl=300)
            except Exception:
                pass

        return df

    def _generate_mock_history(self, symbol: str, market: str = "hk", days: int = 180) -> pd.DataFrame:
        """生成 mock 历史行情数据（数据源不可用时用于演示）"""
        import numpy as np

        mock = self._HK_MOCK_DATA.get(symbol)
        base_price = mock["price"] if mock else 100.0
        name = mock["name"] if mock else self._get_stock_name(symbol, market)

        np.random.seed(hash(symbol) % 2**31)
        dates = pd.date_range(end=datetime.now(), periods=days, freq="B")
        returns = np.random.normal(0.0005, 0.016, days)
        prices = base_price * np.exp(np.cumsum(returns))
        # Ensure the last close matches the mock current price
        prices = prices / prices[-1] * base_price

        df = pd.DataFrame({
            "日期": dates.strftime("%Y-%m-%d"),
            "开盘": prices * (1 + np.random.normal(0, 0.005, days)),
            "收盘": prices,
            "最高": prices * (1 + np.abs(np.random.normal(0, 0.008, days))),
            "最低": prices * (1 - np.abs(np.random.normal(0, 0.008, days))),
            "成交量": np.random.randint(1_000_000, 50_000_000, days, dtype=np.int64),
            "成交额": np.random.randint(10_000_000, 5_000_000_000, days, dtype=np.int64),
        })
        # Ensure OHLC consistency
        df["最高"] = df[["开盘", "收盘", "最高"]].max(axis=1)
        df["最低"] = df[["开盘", "收盘", "最低"]].min(axis=1)
        return df

    def get_stock_info(self, symbol: str, market: str = "hk") -> Dict[str, Any]:
        """
        获取股票基本信息

        Args:
            symbol: 股票代码
            market: 市场类型

        Returns:
            股票信息字典
        """
        # 检查缓存
        cached = self._load_cache(symbol, market)
        if cached:
            return cached

        try:
            df = self.get_stock_history(symbol, market, days=120)
            # Fallback to mock history when real data source is unavailable
            if df.empty and market == "hk" and symbol in self._HK_MOCK_DATA:
                df = self._generate_mock_history(symbol, market, days=120)

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            # 计算技术指标
            df["MA5"] = df["收盘"].rolling(window=5).mean()
            df["MA20"] = df["收盘"].rolling(window=20).mean()
            df["MA60"] = df["收盘"].rolling(window=60).mean()

            # 计算涨跌幅
            change = latest["收盘"] - prev["收盘"]
            change_pct = (change / prev["收盘"]) * 100 if prev["收盘"] != 0 else 0

            # 计算波动率
            df["return"] = df["收盘"].pct_change()
            volatility = df["return"].std() * 100

            info = {
                "symbol": symbol,
                "market": market,
                "name": self._get_stock_name(symbol, market),
                "current_price": round(float(latest["收盘"]), 2),
                "open": round(float(latest["开盘"]), 2),
                "high": round(float(latest["最高"]), 2),
                "low": round(float(latest["最低"]), 2),
                "prev_close": round(float(prev["收盘"]), 2),
                "change": round(float(change), 2),
                "change_pct": round(float(change_pct), 2),
                "volume": int(latest["成交量"]),
                "turnover": round(float(latest.get("成交额", 0)), 2),
                "ma5": round(float(df["MA5"].iloc[-1]), 2) if not pd.isna(df["MA5"].iloc[-1]) else None,
                "ma20": round(float(df["MA20"].iloc[-1]), 2) if not pd.isna(df["MA20"].iloc[-1]) else None,
                "ma60": round(float(df["MA60"].iloc[-1]), 2) if not pd.isna(df["MA60"].iloc[-1]) else None,
                "volatility": round(float(volatility), 2),
                "high_52w": round(float(df["最高"].max()), 2),
                "low_52w": round(float(df["最低"].min()), 2),
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            # 保存缓存
            self._save_cache(symbol, market, info)

            return info

        except Exception as e:
            return {"error": f"获取股票信息失败: {str(e)}"}

    # 港股 mock 数据（网络受限或数据源不可用时降级展示）
    _HK_MOCK_DATA = {
        "00700": {"name": "腾讯控股", "price": 485.2, "change": 6.8, "change_pct": 1.42, "volume": 18543200, "turnover": 8997200000},
        "09988": {"name": "阿里巴巴", "price": 82.15, "change": 1.25, "change_pct": 1.54, "volume": 34215600, "turnover": 2810600000},
        "03690": {"name": "美团", "price": 128.5, "change": -2.1, "change_pct": -1.61, "volume": 12874300, "turnover": 1654300000},
        "01810": {"name": "小米集团", "price": 19.88, "change": 0.32, "change_pct": 1.64, "volume": 45673200, "turnover": 907800000},
        "01299": {"name": "友邦保险", "price": 58.75, "change": 0.45, "change_pct": 0.77, "volume": 5643200, "turnover": 331500000},
        "02318": {"name": "中国平安", "price": 41.35, "change": -0.25, "change_pct": -0.60, "volume": 9876500, "turnover": 408400000},
        "00883": {"name": "中国海洋石油", "price": 17.42, "change": 0.18, "change_pct": 1.04, "volume": 123456000, "turnover": 2150600000},
        "00941": {"name": "中国移动", "price": 68.9, "change": 0.6, "change_pct": 0.88, "volume": 8234500, "turnover": 567300000},
    }

    def _get_stock_name(self, symbol: str, market: str) -> str:
        """获取股票名称"""
        if market == "hk":
            return self._HK_MOCK_DATA.get(symbol, {}).get("name", f"港股{symbol}")
        elif market == "us":
            return f"美股{symbol}"
        else:
            return f"A股{symbol}"

    def get_hk_spot(self, limit: int = 20) -> List[Dict]:
        """获取港股实时行情（网络失败时返回 mock 数据保证演示可用）"""
        try:
            df = ak.stock_hk_spot_em()
            stocks = df.head(limit).to_dict(orient="records")

            # 格式化数据（与前端 StockSpot 接口字段名保持一致）
            formatted = []
            for stock in stocks:
                formatted.append(
                    {
                        "代码": stock.get("代码", ""),
                        "名称": stock.get("名称", ""),
                        "最新价": round(float(stock.get("最新价", 0)), 2),
                        "涨跌额": round(float(stock.get("涨跌额", 0)), 2),
                        "涨跌幅": round(float(stock.get("涨跌幅", 0)), 2),
                        "成交量": int(stock.get("成交量", 0)),
                        "成交额": round(float(stock.get("成交额", 0)), 2),
                    }
                )

            return formatted

        except Exception as e:
            logger.warning(f"获取港股行情失败，使用 mock 数据: {e}")
            return [
                {
                    "代码": code,
                    "名称": data["name"],
                    "最新价": data["price"],
                    "涨跌额": data["change"],
                    "涨跌幅": data["change_pct"],
                    "成交量": data["volume"],
                    "成交额": data["turnover"],
                }
                for code, data in self._HK_MOCK_DATA.items()
            ]

    def get_us_spot(self, limit: int = 20) -> List[Dict]:
        """获取美股实时行情"""
        try:
            df = ak.stock_us_spot_em()
            stocks = df.head(limit).to_dict(orient="records")

            formatted = []
            for stock in stocks:
                formatted.append(
                    {
                        "symbol": stock.get("代码", ""),
                        "name": stock.get("名称", ""),
                        "price": round(float(stock.get("最新价", 0)), 2),
                        "change": round(float(stock.get("涨跌额", 0)), 2),
                        "change_pct": round(float(stock.get("涨跌幅", 0)), 2),
                        "volume": int(stock.get("成交量", 0)),
                    }
                )

            return formatted

        except Exception as e:
            logger.warning(f"获取美股行情失败: {e}")
            return []

    def get_hot_stocks(self, market: str = "hk") -> List[Dict]:
        """获取热门股票（涨幅榜）"""
        try:
            if market == "hk":
                df = ak.stock_hk_spot_em()
                df = df.sort_values("涨跌幅", ascending=False)
            elif market == "us":
                df = ak.stock_us_spot_em()
                df = df.sort_values("涨跌幅", ascending=False)
            else:
                df = ak.stock_zh_a_spot_em()
                df = df.sort_values("涨跌幅", ascending=False)

            hot_stocks = df.head(10).to_dict(orient="records")

            formatted = []
            for stock in hot_stocks:
                formatted.append(
                    {
                        "symbol": stock.get("代码", ""),
                        "name": stock.get("名称", ""),
                        "price": round(float(stock.get("最新价", 0)), 2),
                        "change_pct": round(float(stock.get("涨跌幅", 0)), 2),
                    }
                )

            return formatted

        except Exception as e:
            logger.warning(f"获取热门股票失败: {e}")
            return []

    def calculate_technical_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        计算技术指标

        Args:
            df: 股票历史数据DataFrame

        Returns:
            技术指标字典
        """
        if df.empty:
            return {}

        try:
            # 移动平均线
            df["MA5"] = df["收盘"].rolling(window=5).mean()
            df["MA10"] = df["收盘"].rolling(window=10).mean()
            df["MA20"] = df["收盘"].rolling(window=20).mean()
            df["MA60"] = df["收盘"].rolling(window=60).mean()

            # MACD
            exp1 = df["收盘"].ewm(span=12, adjust=False).mean()
            exp2 = df["收盘"].ewm(span=26, adjust=False).mean()
            df["MACD_DIF"] = exp1 - exp2
            df["MACD_DEA"] = df["MACD_DIF"].ewm(span=9, adjust=False).mean()
            df["MACD_HIST"] = 2 * (df["MACD_DIF"] - df["MACD_DEA"])

            # RSI
            delta = df["收盘"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df["RSI"] = 100 - (100 / (1 + rs))

            # 布林带
            df["BB_MID"] = df["收盘"].rolling(window=20).mean()
            bb_std = df["收盘"].rolling(window=20).std()
            df["BB_UPPER"] = df["BB_MID"] + 2 * bb_std
            df["BB_LOWER"] = df["BB_MID"] - 2 * bb_std

            latest = df.iloc[-1]

            return {
                "ma5": round(float(latest["MA5"]), 2) if not pd.isna(latest["MA5"]) else None,
                "ma10": round(float(latest["MA10"]), 2) if not pd.isna(latest["MA10"]) else None,
                "ma20": round(float(latest["MA20"]), 2) if not pd.isna(latest["MA20"]) else None,
                "ma60": round(float(latest["MA60"]), 2) if not pd.isna(latest["MA60"]) else None,
                "macd_dif": round(float(latest["MACD_DIF"]), 4) if not pd.isna(latest["MACD_DIF"]) else None,
                "macd_dea": round(float(latest["MACD_DEA"]), 4) if not pd.isna(latest["MACD_DEA"]) else None,
                "macd_hist": round(float(latest["MACD_HIST"]), 4) if not pd.isna(latest["MACD_HIST"]) else None,
                "rsi": round(float(latest["RSI"]), 2) if not pd.isna(latest["RSI"]) else None,
                "bb_upper": round(float(latest["BB_UPPER"]), 2) if not pd.isna(latest["BB_UPPER"]) else None,
                "bb_mid": round(float(latest["BB_MID"]), 2) if not pd.isna(latest["BB_MID"]) else None,
                "bb_lower": round(float(latest["BB_LOWER"]), 2) if not pd.isna(latest["BB_LOWER"]) else None,
            }

        except Exception as e:
            logger.warning(f"计算技术指标失败: {e}")
            return {}


# 全局实例
market_data_service = MarketDataService()
