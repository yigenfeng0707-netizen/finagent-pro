import React from 'react';
import { Card, Row, Col, Statistic, List, Tag } from 'antd';
import { useAppStore } from '../stores/appStore';
import RiskGauge from '../charts/RiskGauge';

const RiskPage: React.FC = () => {
  const analysisResult = useAppStore(s => s.analysisResult);

  return (
    <Card title="风险评估中心">
      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card title="当前组合风险">
            {analysisResult ? <RiskGauge value={analysisResult.risk_level} height={350} />
              : <div style={{ height: 350, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>暂无分析数据</div>}
          </Card>
        </Col>
        <Col span={12}>
          <Card title="风险等级说明">
            <List>
              <List.Item><Tag color="green">低风险 (0-30)</Tag><span>适合保守型投资者，追求本金安全</span></List.Item>
              <List.Item><Tag color="yellow">中低风险 (30-50)</Tag><span>适合稳健型投资者，平衡收益与风险</span></List.Item>
              <List.Item><Tag color="orange">中风险 (50-70)</Tag><span>适合平衡型投资者，可接受一定波动</span></List.Item>
              <List.Item><Tag color="red">高风险 (70-100)</Tag><span>适合进取型投资者，追求高收益</span></List.Item>
            </List>
          </Card>
        </Col>
      </Row>
      {analysisResult && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col span={8}>
            <Statistic title="CVaR(95%)" value={analysisResult.cvar_95 ?? 0} suffix="%" precision={2} valueStyle={{ color: '#cf1322' }} />
          </Col>
          <Col span={8}>
            <Statistic title="夏普比率" value={analysisResult.sharpe_ratio ?? 0} precision={2} valueStyle={{ color: (analysisResult.sharpe_ratio ?? 0) > 1 ? '#3f8600' : '#333' }} />
          </Col>
          <Col span={8}>
            <Statistic title="年化收益" value={analysisResult.annual_return ?? 0} suffix="%" precision={2} />
          </Col>
        </Row>
      )}
    </Card>
  );
};

export default RiskPage;
