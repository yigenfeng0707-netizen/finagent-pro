import React from 'react';
import { Card, List, Tag } from 'antd';
import { HK_STOCKS } from '../constants';

export interface StockListPageProps {
  selectedStock: string;
  setSelectedStock: (s: string) => void;
}

const StockListPage: React.FC<StockListPageProps> = ({ selectedStock, setSelectedStock }) => (
  <Card title="港股热门股票">
    <List grid={{ gutter: 16, column: 4 }} dataSource={HK_STOCKS}
      renderItem={(stock: typeof HK_STOCKS[0]) => (
        <List.Item>
          <Card hoverable onClick={() => setSelectedStock(stock.code)}
            style={{ borderColor: selectedStock === stock.code ? '#1890ff' : undefined }}>
            <div style={{ textAlign: 'center' }}>
              <h4>{stock.name}</h4>
              <p style={{ color: '#666' }}>{stock.code}</p>
              <Tag>{stock.sector}</Tag>
            </div>
          </Card>
        </List.Item>
      )} />
  </Card>
);

export default StockListPage;
