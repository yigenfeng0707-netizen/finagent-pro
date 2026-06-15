import React from 'react';
import { Card, Tag } from 'antd';

interface SettingsPageProps {
  wsConnected: boolean;
}

const SettingsPage: React.FC<SettingsPageProps> = ({ wsConnected }) => (
  <Card title="系统配置">
    <p>大模型: DeepSeek V3 (deepseek-chat)</p>
    <p>备选模型: 智谱 GLM-4-plus</p>
    <p>数据源: AKShare</p>
    <p>向量数据库: ChromaDB</p>
    <p>编排引擎: Agent Orchestrator</p>
    <p>版本: v2.0.0</p>
    <p>WebSocket: {wsConnected ? <Tag color="success">已连接</Tag> : <Tag color="default">未连接</Tag>}</p>
  </Card>
);

export default SettingsPage;
