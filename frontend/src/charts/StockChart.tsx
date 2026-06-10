import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

interface StockChartProps {
  data: {
    dates: string[];
    prices: number[];
    volumes: number[];
    ma5?: number[];
    ma20?: number[];
    ma60?: number[];
  };
  title?: string;
  height?: number;
}

const StockChart: React.FC<StockChartProps> = ({ data, title = '股票价格走势', height = 400 }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    // Initialize chart only once
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const option: echarts.EChartsOption = {
      title: {
        text: title,
        left: 'center',
        textStyle: {
          fontSize: 16,
          fontWeight: 'normal'
        }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        }
      },
      legend: {
        data: ['收盘价', 'MA5', 'MA20', 'MA60'],
        bottom: 0
      },
      grid: [
        {
          left: '10%',
          right: '8%',
          height: '50%'
        },
        {
          left: '10%',
          right: '8%',
          top: '68%',
          height: '16%'
        }
      ],
      xAxis: [
        {
          type: 'category',
          data: data.dates,
          boundaryGap: false,
          axisLine: { onZero: false },
          splitLine: { show: false },
          axisLabel: { show: false },
          min: 'dataMin',
          max: 'dataMax'
        },
        {
          type: 'category',
          gridIndex: 1,
          data: data.dates,
          boundaryGap: false,
          axisLine: { onZero: false },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: { show: true },
          min: 'dataMin',
          max: 'dataMax'
        }
      ],
      yAxis: [
        {
          scale: true,
          splitArea: {
            show: true
          }
        },
        {
          scale: true,
          gridIndex: 1,
          splitNumber: 2,
          axisLabel: { show: false },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { show: false }
        }
      ],
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: [0, 1],
          start: 50,
          end: 100
        },
        {
          show: true,
          xAxisIndex: [0, 1],
          type: 'slider',
          top: '85%',
          start: 50,
          end: 100
        }
      ],
      series: [
        {
          name: '收盘价',
          type: 'line',
          data: data.prices,
          smooth: true,
          lineStyle: {
            width: 2,
            color: '#5470c6'
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(84, 112, 198, 0.3)' },
              { offset: 1, color: 'rgba(84, 112, 198, 0.05)' }
            ])
          }
        },
        {
          name: 'MA5',
          type: 'line',
          data: data.ma5,
          smooth: true,
          lineStyle: { width: 1, color: '#fac858' }
        },
        {
          name: 'MA20',
          type: 'line',
          data: data.ma20,
          smooth: true,
          lineStyle: { width: 1, color: '#91cc75' }
        },
        {
          name: 'MA60',
          type: 'line',
          data: data.ma60,
          smooth: true,
          lineStyle: { width: 1, color: '#ee6666' }
        },
        {
          name: '成交量',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: data.volumes,
          itemStyle: {
            color: '#5470c6'
          }
        }
      ]
    };

    chartInstance.current.setOption(option, true); // true = replace mode

    // 响应式
    const handleResize = () => {
      chartInstance.current?.resize();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [data, title]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      chartInstance.current?.dispose();
      chartInstance.current = null;
    };
  }, []);

  return <div ref={chartRef} style={{ width: '100%', height: `${height}px` }} />;
};

export default StockChart;
