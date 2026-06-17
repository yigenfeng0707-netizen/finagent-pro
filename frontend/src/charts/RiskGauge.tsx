import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { GaugeChart } from 'echarts/charts';
import { TitleComponent } from 'echarts/components';
import type { EChartsOption } from 'echarts';

echarts.use([CanvasRenderer, GaugeChart, TitleComponent]);

interface RiskGaugeProps {
  value: number; // 0-100
  title?: string;
  height?: number;
}

const RiskGauge: React.FC<RiskGaugeProps> = ({ 
  value, 
  title = '风险等级', 
  height = 300 
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<ReturnType<typeof echarts.init> | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    // Initialize chart only once
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    // 根据风险值确定颜色和标签
    let riskLabel = '低风险';
    let color = '#91cc75';
    
    if (value < 30) {
      riskLabel = '低风险';
      color = '#91cc75';
    } else if (value < 50) {
      riskLabel = '中低风险';
      color = '#fac858';
    } else if (value < 70) {
      riskLabel = '中风险';
      color = '#ee6666';
    } else {
      riskLabel = '高风险';
      color = '#d93025';
    }

    const option: EChartsOption = {
      title: {
        text: title,
        left: 'center',
        textStyle: {
          fontSize: 16,
          fontWeight: 'normal'
        }
      },
      series: [
        {
          type: 'gauge',
          startAngle: 180,
          endAngle: 0,
          min: 0,
          max: 100,
          splitNumber: 5,
          radius: '90%',
          center: ['50%', '70%'],
          itemStyle: {
            color: color
          },
          progress: {
            show: true,
            roundCap: true,
            width: 18
          },
          pointer: {
            icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
            length: '12%',
            width: 20,
            offsetCenter: [0, '-60%'],
            itemStyle: {
              color: 'auto'
            }
          },
          axisLine: {
            roundCap: true,
            lineStyle: {
              width: 18,
              color: [
                [0.3, '#91cc75'],
                [0.5, '#fac858'],
                [0.7, '#ee6666'],
                [1, '#d93025']
              ]
            }
          },
          axisTick: {
            splitNumber: 2,
            lineStyle: {
              width: 2,
              color: '#999'
            }
          },
          splitLine: {
            length: 12,
            lineStyle: {
              width: 3,
              color: '#999'
            }
          },
          axisLabel: {
            distance: 25,
            color: '#666',
            fontSize: 12,
            formatter: (value: number) => {
              if (value === 0) return '低';
              if (value === 50) return '中';
              if (value === 100) return '高';
              return '';
            }
          },
          title: {
            show: true,
            offsetCenter: [0, '20%'],
            fontSize: 16,
            color: '#333'
          },
          detail: {
            valueAnimation: true,
            fontSize: 36,
            offsetCenter: [0, '-10%'],
            formatter: (value: number) => {
              return `{value|${value.toFixed(0)}}\n{label|${riskLabel}}`;
            },
            rich: {
              value: {
                fontSize: 36,
                fontWeight: 'bold',
                color: color
              },
              label: {
                fontSize: 14,
                color: '#666',
                padding: [10, 0, 0, 0]
              }
            }
          },
          data: [
            {
              value: value,
              name: '风险评分'
            }
          ]
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
  }, [value, title]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      chartInstance.current?.dispose();
      chartInstance.current = null;
    };
  }, []);

  return (
    <div 
      ref={chartRef} 
      style={{ width: '100%', height: `${height}px` }}
      aria-label="风险等级仪表盘"
      role="img"
    />
  );
};

export default RiskGauge;
