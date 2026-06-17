import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { PieChart } from 'echarts/charts';
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components';
import type { EChartsOption } from 'echarts';

echarts.use([CanvasRenderer, PieChart, TitleComponent, TooltipComponent, LegendComponent]);

interface PortfolioPieChartProps {
  data: {
    name: string;
    value?: number;
    weight?: number;
    amount: number;
    symbol?: string;
  }[];
  title?: string;
  height?: number;
}

const PortfolioPieChart: React.FC<PortfolioPieChartProps> = ({ 
  data, 
  title = '资产配置分布', 
  height = 350 
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<ReturnType<typeof echarts.init> | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    // Initialize chart only once
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272'];

    const option: EChartsOption = {
      title: {
        text: title,
        left: 'center',
        textStyle: {
          fontSize: 16,
          fontWeight: 'normal'
        }
      },
      tooltip: {
        trigger: 'item',
        formatter: '{b}<br/>占比: {d}%<br/>金额: {c}万港币',
      },
      legend: {
        orient: 'vertical',
        left: 'left',
        top: 'center'
      },
      color: colors,
      series: [
        {
          name: '资产配置',
          type: 'pie',
          radius: ['40%', '70%'],
          center: ['60%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 10,
            borderColor: '#fff',
            borderWidth: 2
          },
          label: {
            show: true,
            formatter: '{b}\n{d}%'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 16,
              fontWeight: 'bold'
            },
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          },
          labelLine: {
            show: true
          },
          data: data.map(item => ({
            name: item.name,
            value: item.value ?? item.weight ?? 0,
            amount: item.amount
          }))
        }
      ]
    };

    chartInstance.current.setOption(option, true); // true = replace mode

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

  return <div ref={chartRef} style={{ width: '100%', height: `${height}px` }} aria-label="资产配置饼图" role="img" />;
};

export default PortfolioPieChart;
