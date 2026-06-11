import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Alert, Skeleton, Typography } from 'antd';
import { RiseOutlined, FallOutlined } from '@ant-design/icons';
import { HK_STOCKS, API_BASE } from '../constants';

const { Text } = Typography;

export interface StockListPageProps {
  selectedStock: string;
  setSelectedStock: (s: string) => void;
}

interface StockSpot {
  代码: string;
  名称: string;
  最新价: number;
  涨跌幅: number;
  涨跌额: number;
  成交量: number;
  成交额: number;
}

const StockListPage: React.FC<StockListPageProps> = ({ selectedStock, setSelectedStock }) => {
  const [stocks, setStocks] = useState<StockSpot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchSpot = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/market/hk-spot`);
        const json = await res.json();
        if (json.success && json.data) {
          // Match with our HK_STOCKS list
          const codes = new Set(HK_STOCKS.map(s => s.code));
          const matched = json.data
            .filter((s: any) => codes.has(s['代码'] || s['编号']))
            .map((s: any) => ({
              代码: s['代码'] || s['编号'],
              名称: s['名称'],
              最新价: parseFloat(s['最新价']) || 0,
              涨跌幅: parseFloat(s['涨跌幅']) || 0,
              涨跌额: parseFloat(s['涨跌额']) || 0,
              成交量: parseFloat(s['成交量']) || 0,
              成交额: parseFloat(s['成交额']) || 0,
            }));
          setStocks(matched);
        }
      } catch (e) {
        setError('行情数据获取失败');
      } finally {
        setLoading(false);
      }
    };
    fetchSpot();
  }, []);

  if (error) return <Alert message={error} type="warning" showIcon />;

  return (
    <div>
      <Row gutter={[16, 16]}>
        {(loading ? HK_STOCKS : stocks).map((stock, idx) => {
          const isSpot = '最新价' in stock;
          const change = isSpot ? (stock as StockSpot).涨跌幅 : 0;
          const isUp = change > 0;
          return (
            <Col xs={24} sm={12} md={8} lg={6} key={isSpot ? (stock as StockSpot).代码 : idx}>
              <Card
                hoverable
                size="small"
                onClick={() => {
                  const code = isSpot
                    ? (stock as StockSpot).代码
                    : (stock as typeof HK_STOCKS[number]).code;
                  setSelectedStock(code);
                }}
                style={{
                  borderLeft: `3px solid ${isUp ? '#cf1322' : change < 0 ? '#3f8600' : '#d9d9d9'}`,
                  borderColor: (isSpot ? (stock as StockSpot).代码 : (stock as typeof HK_STOCKS[number]).code) === selectedStock ? '#1890ff' : undefined,
                }}
              >
                {loading ? (
                  <Skeleton active paragraph={{ rows: 2 }} />
                ) : isSpot ? (
                  <>
                    <Text strong>{(stock as StockSpot).名称}</Text>
                    <Text type="secondary" style={{ marginLeft: 8 }}>{(stock as StockSpot).代码}</Text>
                    <Statistic
                      value={(stock as StockSpot).最新价}
                      precision={2}
                      suffix="HKD"
                      valueStyle={{ color: isUp ? '#cf1322' : change < 0 ? '#3f8600' : '#333', fontSize: 20 }}
                      style={{ marginTop: 8 }}
                    />
                    <div style={{ marginTop: 4 }}>
                      <Text style={{ color: isUp ? '#cf1322' : '#3f8600' }}>
                        {isUp ? <RiseOutlined /> : <FallOutlined />}
                        {' '}{change > 0 ? '+' : ''}{change.toFixed(2)}%
                        {' '}({(stock as StockSpot).涨跌额 > 0 ? '+' : ''}{(stock as StockSpot).涨跌额.toFixed(2)})
                      </Text>
                    </div>
                  </>
                ) : (
                  <>
                    <Text strong>{(stock as typeof HK_STOCKS[number]).name}</Text>
                    <Text type="secondary" style={{ marginLeft: 8 }}>{(stock as typeof HK_STOCKS[number]).code}</Text>
                    <div style={{ color: '#999', marginTop: 8 }}>暂无行情数据</div>
                  </>
                )}
              </Card>
            </Col>
          );
        })}
      </Row>
    </div>
  );
};

export default StockListPage;
