import React from 'react';
import { Card, Row, Col, Tabs, List, Button } from 'antd';
import { PieChartOutlined, FilePdfOutlined } from '@ant-design/icons';
import { useAppStore } from '../stores/appStore';
import { useAnalysis } from '../hooks/useAnalysis';
import PortfolioPieChart from '../charts/PortfolioPieChart';

const PortfolioPage: React.FC = () => {
  const analysisResult = useAppStore(s => s.analysisResult);
  const { exportReport } = useAnalysis();

  return (
    <Card title="投资组合分析" extra={analysisResult && <Button icon={<FilePdfOutlined />} onClick={exportReport}>导出PDF报告</Button>}>
      {analysisResult ? (
        <Tabs defaultActiveKey="1" items={[
          {
            key: '1',
            label: '配置详情',
            children: (
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <List
                    dataSource={analysisResult.portfolio_allocation}
                    renderItem={(item) => (
                      <List.Item>
                        <List.Item.Meta title={`${item.name} (${item.symbol})`} description={`配置金额: HKD ${item.amount.toLocaleString()}`} />
                        <div style={{ fontSize: 18, fontWeight: 'bold' }}>{item.weight}%</div>
                      </List.Item>
                    )}
                  />
                </Col>
                <Col span={12}>
                  <PortfolioPieChart data={analysisResult.portfolio_allocation} />
                </Col>
              </Row>
            ),
          },
          {
            key: '2',
            label: '分析报告',
            children: <div style={{ whiteSpace: 'pre-wrap', lineHeight: 2 }}>{analysisResult.reasoning}</div>,
          },
        ]} />
      ) : (
        <div style={{ textAlign: 'center', padding: '100px 0', color: '#999' }}>
          <PieChartOutlined style={{ fontSize: 48, marginBottom: 16 }} />
          <p>请先执行投资分析</p>
        </div>
      )}
    </Card>
  );
};

export default PortfolioPage;
