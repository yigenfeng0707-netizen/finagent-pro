"""
金融知识库 - RAG检索增强
"""

import os
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings
from loguru import logger


class FinanceKnowledgeBase:
    """金融知识库"""

    def __init__(self, persist_dir: str = "./chroma_db"):
        """
        初始化知识库

        Args:
            persist_dir: 向量数据库持久化目录
        """
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        self._client: Optional[Any] = None
        self._collection: Optional[Any] = None

    def _ensure_initialized(self):
        if self._client is not None:
            return
        self._client = chromadb.Client(Settings(persist_directory=self.persist_dir, anonymized_telemetry=False))
        self._collection = self._client.get_or_create_collection(
            name="finance_knowledge", metadata={"description": "金融投资知识库"}
        )
        self._init_knowledge()

    @property
    def client(self):
        self._ensure_initialized()
        return self._client

    @property
    def collection(self):
        self._ensure_initialized()
        return self._collection

    def _init_knowledge(self):
        """初始化金融知识"""
        # 检查是否已有数据
        if self.collection.count() > 0:
            return

        # 基础金融知识
        knowledge_items = [
            {
                "id": "risk_profile_1",
                "content": "保守型投资者：风险承受能力低，追求本金安全，适合配置债券、货币基金等低风险资产。建议股票配置不超过30%。",
                "metadata": {"category": "风险偏好", "type": "保守型"},
            },
            {
                "id": "risk_profile_2",
                "content": "稳健型投资者：风险承受能力中等，追求稳健收益，适合股债平衡配置。建议股票配置30%-60%。",
                "metadata": {"category": "风险偏好", "type": "稳健型"},
            },
            {
                "id": "risk_profile_3",
                "content": "进取型投资者：风险承受能力高，追求高收益，适合配置成长型股票。建议股票配置60%-80%。",
                "metadata": {"category": "风险偏好", "type": "进取型"},
            },
            {
                "id": "asset_allocation_1",
                "content": "资产配置原则：不要把所有鸡蛋放在一个篮子里。通过分散投资降低风险，一般建议配置股票、债券、现金、黄金等多种资产。",
                "metadata": {"category": "资产配置", "type": "基础原则"},
            },
            {
                "id": "asset_allocation_2",
                "content": "再平衡策略：定期调整投资组合，使其回到目标配置比例。一般建议每季度或每半年进行一次再平衡。",
                "metadata": {"category": "资产配置", "type": "再平衡"},
            },
            {
                "id": "hk_stock_1",
                "content": "港股特点：港股市场国际化程度高，机构投资者占主导。主要指数包括恒生指数、恒生科技指数。交易时间为周一至周五9:30-12:00, 13:00-16:00。",
                "metadata": {"category": "港股市场", "type": "基础知识"},
            },
            {
                "id": "hk_stock_2",
                "content": "港股通：内地投资者可通过港股通投资港股，需满足50万资产门槛。港股通标的包括恒生综合大型股、中型股指数成分股等。",
                "metadata": {"category": "港股市场", "type": "港股通"},
            },
            {
                "id": "tech_analysis_1",
                "content": "移动平均线(MA)：MA5、MA10、MA20、MA60是常用均线。金叉（短期均线上穿长期均线）为买入信号，死叉为卖出信号。",
                "metadata": {"category": "技术分析", "type": "均线"},
            },
            {
                "id": "tech_analysis_2",
                "content": "MACD指标：由DIF、DEA和MACD柱状图组成。DIF上穿DEA为金叉买入信号，下穿为死叉卖出信号。",
                "metadata": {"category": "技术分析", "type": "MACD"},
            },
            {
                "id": "tech_analysis_3",
                "content": "RSI指标：相对强弱指数，取值0-100。RSI>70为超买，可能回调；RSI<30为超卖，可能反弹。",
                "metadata": {"category": "技术分析", "type": "RSI"},
            },
            {
                "id": "risk_mgmt_1",
                "content": "止损策略：设定止损点，当股价下跌到止损点时果断卖出，控制损失。一般建议止损幅度为5%-10%。",
                "metadata": {"category": "风险管理", "type": "止损"},
            },
            {
                "id": "risk_mgmt_2",
                "content": "仓位管理：不要满仓操作，保留一定现金比例。建议单只股票仓位不超过总资产的20%，单一行业不超过30%。",
                "metadata": {"category": "风险管理", "type": "仓位管理"},
            },
            {
                "id": "valuation_1",
                "content": "市盈率(PE)：股价与每股收益的比率。PE越低，股票相对越便宜。但不同行业PE水平差异大，需横向比较。",
                "metadata": {"category": "估值指标", "type": "PE"},
            },
            {
                "id": "valuation_2",
                "content": "市净率(PB)：股价与每股净资产的比率。PB<1表示股价低于净资产，可能被低估（需结合其他指标判断）。",
                "metadata": {"category": "估值指标", "type": "PB"},
            },
            {
                "id": "investment_style_1",
                "content": "价值投资：寻找被低估的优质公司，长期持有。代表人物：巴菲特。关注公司基本面、盈利能力、护城河。",
                "metadata": {"category": "投资风格", "type": "价值投资"},
            },
            {
                "id": "investment_style_2",
                "content": "成长投资：投资高成长性公司，追求资本增值。关注收入增长率、市场份额扩张、创新能力。",
                "metadata": {"category": "投资风格", "type": "成长投资"},
            },
            {
                "id": "etf_1",
                "content": "ETF基金：交易型开放式指数基金，跟踪特定指数。优点：分散风险、成本低、交易灵活。港股常见ETF：盈富基金(02800.HK)、恒生科技ETF(03033.HK)。",
                "metadata": {"category": "基金投资", "type": "ETF"},
            },
            {
                "id": "market_cycle_1",
                "content": "市场周期：股市通常经历牛市、熊市、震荡市。牛市上涨为主，熊市下跌为主，震荡市横盘整理。不同周期应采取不同策略。",
                "metadata": {"category": "市场周期", "type": "周期理论"},
            },
            {
                "id": "tencent_00700",
                "content": "腾讯控股(00700.HK)：中国最大互联网公司之一，业务涵盖社交、游戏、广告、金融科技等。核心产品包括微信、QQ、王者荣耀等。",
                "metadata": {"category": "个股介绍", "symbol": "00700", "name": "腾讯控股"},
            },
            {
                "id": "alibaba_09988",
                "content": "阿里巴巴(09988.HK)：中国最大电商平台，业务包括淘宝、天猫、阿里云、菜鸟网络等。港股第二上市，美股代码BABA。",
                "metadata": {"category": "个股介绍", "symbol": "09988", "name": "阿里巴巴"},
            },
            {
                "id": "meituan_03690",
                "content": "美团(03690.HK)：中国领先的生活服务电商平台，业务包括外卖、到店、酒店旅游、新零售等。",
                "metadata": {"category": "个股介绍", "symbol": "03690", "name": "美团"},
            },
            {
                "id": "xiaomi_01810",
                "content": "小米集团(01810.HK)：以手机、智能硬件和IoT平台为核心的互联网公司。生态链产品覆盖多个品类。",
                "metadata": {"category": "个股介绍", "symbol": "01810", "name": "小米集团"},
            },
            {
                "id": "hsbc_00005",
                "content": "汇丰控股(00005.HK)：香港最大的银行，也是全球最大的银行之一。业务遍及全球，股息率较高，是稳健投资者的选择。",
                "metadata": {"category": "个股介绍", "symbol": "00005", "name": "汇丰控股"},
            },
        ]

        # 添加到知识库
        for item in knowledge_items:
            self.collection.add(ids=[item["id"]], documents=[item["content"]], metadatas=[item["metadata"]])

        logger.info(f"知识库初始化完成，共添加 {len(knowledge_items)} 条知识")

    def search(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        搜索相关知识

        Args:
            query: 查询内容
            n_results: 返回结果数量

        Returns:
            相关知识列表
        """
        try:
            results = self.collection.query(query_texts=[query], n_results=n_results)

            knowledge_list = []
            for i in range(len(results["ids"][0])):
                knowledge_list.append(
                    {
                        "id": results["ids"][0][i],
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if "distances" in results else None,
                    }
                )

            return knowledge_list

        except Exception as e:
            logger.warning(f"知识库搜索失败: {e}")
            return []

    def query_knowledge(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        查询知识库（别名方法，兼容main.py调用）

        Args:
            query: 查询内容
            n_results: 返回结果数量

        Returns:
            相关知识列表
        """
        return self.search(query, n_results)

    def get_context_for_query(self, query: str, n_results: int = 3) -> str:
        """
        获取查询的上下文知识

        Args:
            query: 查询内容
            n_results: 返回结果数量

        Returns:
            格式化的知识文本
        """
        knowledge = self.search(query, n_results)

        if not knowledge:
            return ""

        context = "相关金融知识:\n"
        for i, item in enumerate(knowledge, 1):
            context += f"{i}. {item['content']}\n"

        return context

    def add_knowledge(self, content: str, metadata: Dict[str, Any], doc_id: str = None):
        """
        添加新知识

        Args:
            content: 知识内容
            metadata: 元数据
            doc_id: 文档ID（可选）
        """
        if doc_id is None:
            doc_id = f"custom_{self.collection.count()}"

        self.collection.add(ids=[doc_id], documents=[content], metadatas=[metadata])


# 全局实例
finance_kb = FinanceKnowledgeBase()
