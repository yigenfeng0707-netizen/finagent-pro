import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, ConfigProvider, theme, Switch, Tag } from 'antd';
import {
  DashboardOutlined, LineChartOutlined, PieChartOutlined, SafetyOutlined,
  RobotOutlined, SettingOutlined, ApiOutlined, SunOutlined, MoonOutlined,
} from '@ant-design/icons';
import { useAppStore } from './stores/appStore';
import { useAnalysis } from './hooks/useAnalysis';
import DashboardPage from './components/DashboardPage';
import AgentChatPage from './components/AgentChatPage';
import StockListPage from './components/StockListPage';
import OrchestratorWorkbench from './components/OrchestratorWorkbench';
import PortfolioPage from './pages/PortfolioPage';
import RiskPage from './pages/RiskPage';
import SettingsPage from './pages/SettingsPage';
import './App.css';

const { Header, Sider, Content } = Layout;

const MENU_ITEMS = [
  { key: '/', icon: <DashboardOutlined />, label: '投资仪表盘' },
  { key: '/stocks', icon: <LineChartOutlined />, label: '港股行情' },
  { key: '/agents', icon: <RobotOutlined />, label: 'Agent对话' },
  { key: '/workbench', icon: <ApiOutlined />, label: '数字员工工作台' },
  { key: '/portfolio', icon: <PieChartOutlined />, label: '组合分析' },
  { key: '/risk', icon: <SafetyOutlined />, label: '风险评估' },
  { key: '/settings', icon: <SettingOutlined />, label: '系统设置' },
];

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const collapsed = useAppStore(s => s.collapsed);
  const darkMode = useAppStore(s => s.darkMode);
  const setCollapsed = useAppStore(s => s.setCollapsed);
  const setDarkMode = useAppStore(s => s.setDarkMode);
  const wsConnected = useAppStore(s => s.wsConnected);
  const selectedStock = useAppStore(s => s.selectedStock);
  const { fetchStockData, fetchMarketOverview } = useAnalysis();

  useEffect(() => {
    fetchStockData(selectedStock);
    fetchMarketOverview();
    const interval = setInterval(fetchMarketOverview, 30000);
    return () => clearInterval(interval);
  }, [selectedStock, fetchStockData, fetchMarketOverview]);

  return (
    <ConfigProvider theme={{
      algorithm: darkMode ? theme.darkAlgorithm : theme.defaultAlgorithm,
      token: { colorPrimary: '#1890ff', borderRadius: 6 },
    }}>
      <Layout style={{ minHeight: '100vh' }}>
        <Sider trigger={null} collapsible collapsed={collapsed} onCollapse={setCollapsed} aria-label="主导航">
          <div className="logo">
            <RobotOutlined style={{ fontSize: 24, color: 'white' }} />
            {!collapsed && <span style={{ color: 'white', marginLeft: 8, fontSize: 18 }}>FinAgent Pro</span>}
          </div>
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[location.pathname]}
            onClick={({ key }) => navigate(key)}
            items={MENU_ITEMS}
          />
        </Sider>
        <Layout>
          <Header style={{
            padding: '0 24px',
            background: darkMode ? '#141414' : '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <h2 style={{ margin: 0 }}>
              {MENU_ITEMS.find(i => i.key === location.pathname)?.label || ''}
            </h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <Tag color="blue">港股通</Tag>
              <Tag color="green">AI驱动</Tag>
              <Tag color="orange">国产大模型</Tag>
              <Switch
                checked={darkMode}
                onChange={setDarkMode}
                checkedChildren={<MoonOutlined />}
                unCheckedChildren={<SunOutlined />}
                title="暗色模式"
                aria-label="切换暗色模式"
              />
            </div>
          </Header>
          <Content style={{
            margin: '24px 16px',
            padding: 24,
            background: darkMode ? '#1f1f1f' : '#f0f2f5',
            minHeight: 280,
          }}>
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/stocks" element={<StockListPageWrapper />} />
              <Route path="/agents" element={<AgentChatPage />} />
              <Route path="/workbench" element={<OrchestratorWorkbenchWrapper />} />
              <Route path="/portfolio" element={<PortfolioPage />} />
              <Route path="/risk" element={<RiskPage />} />
              <Route path="/settings" element={<SettingsPage wsConnected={wsConnected} />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
};

// 包装组件，从 store 获取 props
const StockListPageWrapper: React.FC = () => {
  const selectedStock = useAppStore(s => s.selectedStock);
  const setSelectedStock = useAppStore(s => s.setSelectedStock);
  return <StockListPage selectedStock={selectedStock} setSelectedStock={setSelectedStock} />;
};

const OrchestratorWorkbenchWrapper: React.FC = () => {
  const workbenchSteps = useAppStore(s => s.workbenchSteps);
  const toolCalls = useAppStore(s => s.toolCalls);
  const liveContext = useAppStore(s => s.liveContext);
  return <OrchestratorWorkbench steps={workbenchSteps} toolCalls={toolCalls} liveContext={liveContext} />;
};

const App: React.FC = () => (
  <BrowserRouter>
    <AppLayout />
  </BrowserRouter>
);

export default App;
