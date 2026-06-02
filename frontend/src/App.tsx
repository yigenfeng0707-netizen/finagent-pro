import React, { useState, useEffect } from 'react';
import { Layout, Menu, Card, Row, Col, Statistic, Button, Input, Select, message, Tabs, List, Tag, Spin } from 'antd';
import {
  DashboardOutlined,
  LineChartOutlined,
  PieChartOutlined,
  SafetyOutlined,
  RobotOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  RiseOutlined,
  FallOutlined,
  DollarOutlined
} from '@ant-design/icons';
import StockChart from './charts/StockChart';
import PortfolioPieChart from './charts/PortfolioPieChart';
import RiskGauge from './charts/RiskGauge';
import './App.css';

const { Header, Sider, Content } = Layout;
const { Option } = Select;
const { TabPane } = Tabs;

// 港股热门股票
const HK_STOCKS = [
  { code: '00700', name: '腾讯控股', sector: '科技' },
  { code: '09988', name: '阿里巴巴', sector: '科技' },
  { code: '03690', name: '美团', sector: '科技' },
  { code: '01810', name: '小米集团', sector: '科技' },
  { code: '01299', name: '友邦保险', sector: '金融' },
  { code: '02318', name: '中国平安', sector: '金融' },
  { code: '00883', name: '中国海洋石油', sector: '能源' },
  { code: '00941', name: '中国移动', sector: '通信' },
];

interface StockData {
  dates: string[];
  prices: number[];
  volumes: number[];
  ma5?: number[];
  ma20?: number[];
  ma60?: number[];
}

interface AgentMessage {
  agent: string;
  role: string;
  content: string;
  timestamp: string;
}

interface AnalysisResult {
  recommendation: string;
  confidence: number;
  risk_level: number;
  expected_return: number;
  reasoning: string;
  portfolio_allocation: Array<{symbol: string; name: string; weight: number; amount: number}>;
  agent_messages: AgentMessage[];
}

const App: React.FC = () => {
  const [collapsed] = useState(false);
  const [selectedMenu, setSelectedMenu] = useState('dashboard');
  const [loading, setLoading] = useState(false);
  const [stockData, setStockData] = useState<StockData | null>(null);
  const [selectedStock, setSelectedStock] = useState('00700');
  const [investmentAmount, setInvestmentAmount] = useState<number>(100000);
  const [riskPreference, setRiskPreference] = useState('moderate');
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [marketOverview, setMarketOverview] = useState({
    hsIndex: 0,
    hsChange: 0,
    techIndex: 0,
    techChange: 0,
    volume: 0
  });

  // 获取股票历史数据
  const fetchStockData = async (symbol: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/market/stock/${symbol}?market=hk&days=180`);
      const data = await response.json();
      if (data.status === 'success') {
        setStockData(data.data);
      }
    } catch (error) {
      message.error('获取股票数据失败');
    }
  };

  // 执行多Agent分析
  const runAnalysis = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/analysis/portfolio', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbols: [selectedStock],
          investment_amount: investmentAmount,
          risk_preference: riskPreference,
          market: 'hk'
        })
      });
      const data = await response.json();
      if (data.status === 'success') {
        setAnalysisResult(data.data);
        message.success('分析完成！');
      }
    } catch (error) {
      message.error('分析失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  // 获取市场概览
  const fetchMarketOverview = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/market/hot?market=hk');
      const data = await response.json();
      if (data.status === 'success') {
        // 模拟市场数据
        setMarketOverview({
          hsIndex: 18500 + Math.random() * 500,
          hsChange: (Math.random() - 0.5) * 2,
          techIndex: 4200 + Math.random() * 200,
          techChange: (Math.random() - 0.5) * 3,
          volume: 1200 + Math.random() * 300
        });
      }
    } catch (error) {
      console.error('获取市场概览失败');
    }
  };

  useEffect(() => {
    fetchStockData(selectedStock);
    fetchMarketOverview();
    const interval = setInterval(fetchMarketOverview, 30000);
    return () => clearInterval(interval);
  }, [selectedStock]);

  // 渲染仪表盘
  const renderDashboard = () => (
    <div className="dashboard">
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card>
            <Statistic
              title="恒生指数"
              value={marketOverview.hsIndex}
              precision={2}
              valueStyle={{ color: marketOverview.hsChange >= 0 ? '#cf1322' : '#3f8600' }}
              prefix={marketOverview.hsChange >= 0 ? <RiseOutlined /> : <FallOutlined />}
              suffix={`${marketOverview.hsChange >= 0 ? '+' : ''}${marketOverview.hsChange.toFixed(2)}%`}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="恒生科技指数"
              value={marketOverview.techIndex}
              precision={2}
              valueStyle={{ color: marketOverview.techChange >= 0 ? '#cf1322' : '#3f8600' }}
              prefix={marketOverview.techChange >= 0 ? <RiseOutlined /> : <FallOutlined />}
              suffix={`${marketOverview.techChange >= 0 ? '+' : ''}${marketOverview.techChange.toFixed(2)}%`}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="今日成交额(亿)"
              value={marketOverview.volume}
              precision={0}
              prefix={<DollarOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="AI分析状态"
              value="运行中"
              valueStyle={{ color: '#52c41a' }}
              prefix={<RobotOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={16}>
          <Card title="股票走势" extra={
            <Select
              value={selectedStock}
              onChange={setSelectedStock}
              style={{ width: 150 }}
            >
              {HK_STOCKS.map(stock => (
                <Option key={stock.code} value={stock.code}>
                  {stock.name} ({stock.code})
                </Option>
              ))}
            </Select>
          }>
            {stockData ? (
              <StockChart data={stockData} />
            ) : (
              <div style={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Spin size="large" />
              </div>
            )}
          </Card>
        </Col>
        <Col span={8}>
          <Card title="快速分析">
            <div style={{ marginBottom: 16 }}>
              <label>投资金额 (HKD):</label>
              <Input
                type="number"
                value={investmentAmount}
                onChange={e => setInvestmentAmount(Number(e.target.value))}
                prefix="$"
                style={{ marginTop: 8 }}
              />
            </div>
            <div style={{ marginBottom: 16 }}>
              <label>风险偏好:</label>
              <Select
                value={riskPreference}
                onChange={setRiskPreference}
                style={{ width: '100%', marginTop: 8 }}
              >
                <Option value="conservative">保守型</Option>
                <Option value="moderate">稳健型</Option>
                <Option value="aggressive">进取型</Option>
              </Select>
            </div>
            <Button
              type="primary"
              icon={<ThunderboltOutlined />}
              onClick={runAnalysis}
              loading={loading}
              block
              size="large"
            >
              启动AI分析
            </Button>
          </Card>
        </Col>
      </Row>

      {analysisResult && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col span={8}>
            <Card title="投资组合配置">
              <PortfolioPieChart data={analysisResult.portfolio_allocation} />
            </Card>
          </Col>
          <Col span={8}>
            <Card title="风险等级评估">
              <RiskGauge value={analysisResult.risk_level} />
            </Card>
          </Col>
          <Col span={8}>
            <Card title="投资建议">
              <div style={{ textAlign: 'center', padding: '20px 0' }}>
                <Tag color={analysisResult.recommendation === 'buy' ? 'red' : analysisResult.recommendation === 'sell' ? 'green' : 'default'}
                  style={{ fontSize: 18, padding: '8px 16px' }}
                >
                  {analysisResult.recommendation === 'buy' ? '买入' : analysisResult.recommendation === 'sell' ? '卖出' : '持有'}
                </Tag>
                <div style={{ marginTop: 16 }}>
                  <Statistic
                    title="预期收益率"
                    value={analysisResult.expected_return}
                    precision={2}
                    suffix="%"
                    valueStyle={{ color: analysisResult.expected_return >= 0 ? '#cf1322' : '#3f8600' }}
                  />
                </div>
                <div style={{ marginTop: 16 }}>
                  <Statistic
                    title="置信度"
                    value={analysisResult.confidence}
                    precision={1}
                    suffix="%"
                  />
                </div>
              </div>
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );

  // 渲染Agent对话
  const renderAgentChat = () => (
    <Card title="多Agent协作分析" style={{ height: 'calc(100vh - 200px)' }}>
      {analysisResult?.agent_messages ? (
        <List
          itemLayout="horizontal"
          dataSource={analysisResult.agent_messages}
          renderItem={(msg: AgentMessage) => (
            <List.Item>
              <List.Item.Meta
                avatar={
                  <div style={{
                    width: 40,
                    height: 40,
                    borderRadius: '50%',
                    background: msg.agent.includes('市场') ? '#1890ff' :
                               msg.agent.includes('风险') ? '#ff4d4f' :
                               msg.agent.includes('组合') ? '#52c41a' : '#faad14',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    fontWeight: 'bold'
                  }}>
                    {msg.agent.charAt(0)}
                  </div>
                }
                title={<span><strong>{msg.agent}</strong> <Tag>{msg.role}</Tag></span>}
                description={
                  <div>
                    <div style={{ color: '#666', fontSize: 12, marginBottom: 8 }}>{msg.timestamp}</div>
                    <div>{msg.content}</div>
                  </div>
                }
              />
            </List.Item>
          )}
        />
      ) : (
        <div style={{ textAlign: 'center', padding: '100px 0', color: '#999' }}>
          <RobotOutlined style={{ fontSize: 48, marginBottom: 16 }} />
          <p>请先执行分析以查看Agent协作过程</p>
        </div>
      )}
    </Card>
  );

  // 渲染港股列表
  const renderStockList = () => (
    <Card title="港股热门股票">
      <List
        grid={{ gutter: 16, column: 4 }}
        dataSource={HK_STOCKS}
        renderItem={(stock: typeof HK_STOCKS[0]) => (
          <List.Item>
            <Card
              hoverable
              onClick={() => setSelectedStock(stock.code)}
              style={{ borderColor: selectedStock === stock.code ? '#1890ff' : undefined }}
            >
              <div style={{ textAlign: 'center' }}>
                <h4>{stock.name}</h4>
                <p style={{ color: '#666' }}>{stock.code}</p>
                <Tag>{stock.sector}</Tag>
              </div>
            </Card>
          </List.Item>
        )}
      />
    </Card>
  );

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed}>
        <div className="logo">
          <RobotOutlined style={{ fontSize: 24, color: 'white' }} />
          {!collapsed && <span style={{ color: 'white', marginLeft: 8, fontSize: 18 }}>FinAgent Pro</span>}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedMenu]}
          onClick={({ key }) => setSelectedMenu(key)}
          items={[
            { key: 'dashboard', icon: <DashboardOutlined />, label: '投资仪表盘' },
            { key: 'stocks', icon: <LineChartOutlined />, label: '港股行情' },
            { key: 'agents', icon: <RobotOutlined />, label: 'Agent对话' },
            { key: 'portfolio', icon: <PieChartOutlined />, label: '组合分析' },
            { key: 'risk', icon: <SafetyOutlined />, label: '风险评估' },
            { key: 'settings', icon: <SettingOutlined />, label: '系统设置' },
          ]}
        />
      </Sider>
      <Layout>
        <Header style={{ padding: '0 24px', background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h2 style={{ margin: 0 }}>
            {selectedMenu === 'dashboard' && '投资仪表盘'}
            {selectedMenu === 'stocks' && '港股行情'}
            {selectedMenu === 'agents' && '多Agent协作'}
            {selectedMenu === 'portfolio' && '组合分析'}
            {selectedMenu === 'risk' && '风险评估'}
            {selectedMenu === 'settings' && '系统设置'}
          </h2>
          <div>
            <Tag color="blue">港股通</Tag>
            <Tag color="green">AI驱动</Tag>
            <Tag color="orange">国产大模型</Tag>
          </div>
        </Header>
        <Content style={{ margin: '24px 16px', padding: 24, background: '#f0f2f5', minHeight: 280 }}>
          {selectedMenu === 'dashboard' && renderDashboard()}
          {selectedMenu === 'stocks' && renderStockList()}
          {selectedMenu === 'agents' && renderAgentChat()}
          {selectedMenu === 'portfolio' && (
            <Card title="投资组合分析">
              {analysisResult ? (
                <Tabs defaultActiveKey="1">
                  <TabPane tab="配置详情" key="1">
                    <List
                      dataSource={analysisResult.portfolio_allocation}
                      renderItem={(item: any) => (
                        <List.Item>
                          <List.Item.Meta
                            title={`${item.name} (${item.symbol})`}
                            description={`配置金额: HKD ${item.amount.toLocaleString()}`}
                          />
                          <div style={{ fontSize: 18, fontWeight: 'bold' }}>{item.weight}%</div>
                        </List.Item>
                      )}
                    />
                  </TabPane>
                  <TabPane tab="分析报告" key="2">
                    <div style={{ whiteSpace: 'pre-wrap', lineHeight: 2 }}>
                      {analysisResult.reasoning}
                    </div>
                  </TabPane>
                </Tabs>
              ) : (
                <div style={{ textAlign: 'center', padding: '100px 0', color: '#999' }}>
                  <PieChartOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                  <p>请先执行投资分析</p>
                </div>
              )}
            </Card>
          )}
          {selectedMenu === 'risk' && (
            <Card title="风险评估中心">
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <Card title="当前组合风险">
                    {analysisResult ? (
                      <RiskGauge value={analysisResult.risk_level} height={350} />
                    ) : (
                      <div style={{ height: 350, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
                        暂无分析数据
                      </div>
                    )}
                  </Card>
                </Col>
                <Col span={12}>
                  <Card title="风险等级说明">
                    <List>
                      <List.Item>
                        <Tag color="green">低风险 (0-30)</Tag>
                        <span>适合保守型投资者，追求本金安全</span>
                      </List.Item>
                      <List.Item>
                        <Tag color="yellow">中低风险 (30-50)</Tag>
                        <span>适合稳健型投资者，平衡收益与风险</span>
                      </List.Item>
                      <List.Item>
                        <Tag color="orange">中风险 (50-70)</Tag>
                        <span>适合平衡型投资者，可接受一定波动</span>
                      </List.Item>
                      <List.Item>
                        <Tag color="red">高风险 (70-100)</Tag>
                        <span>适合进取型投资者，追求高收益</span>
                      </List.Item>
                    </List>
                  </Card>
                </Col>
              </Row>
            </Card>
          )}
          {selectedMenu === 'settings' && (
            <Card title="系统配置">
              <p>大模型: DeepSeek V3</p>
              <p>数据源: AKShare</p>
              <p>向量数据库: ChromaDB</p>
              <p>版本: v1.0.0</p>
            </Card>
          )}
        </Content>
      </Layout>
    </Layout>
  );
};

export default App;
