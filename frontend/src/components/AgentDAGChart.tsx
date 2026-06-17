import React, { useRef, useEffect } from 'react';
import * as echarts from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { GraphChart } from 'echarts/charts';
import { TooltipComponent } from 'echarts/components';


echarts.use([CanvasRenderer, GraphChart, TooltipComponent]);

interface DAGStep {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  confidence?: number;
  duration?: number;
}

interface AgentDAGChartProps {
  steps: DAGStep[];
  activeStep: number;
}

const STATUS_COLORS: Record<string, string> = {
  pending: '#d9d9d9',
  running: '#1890ff',
  completed: '#52c41a',
  failed: '#ff4d4f',
};

const AgentDAGChart: React.FC<AgentDAGChartProps> = ({ steps, activeStep }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<ReturnType<typeof echarts.init> | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;
    instanceRef.current = echarts.init(chartRef.current);
    return () => { instanceRef.current?.dispose(); };
  }, []);

  useEffect(() => {
    if (!instanceRef.current) return;

    const nodes = steps.map((step, i) => ({
      name: step.name,
      x: 100 + i * 180,
      y: 80,
      symbolSize: step.status === 'running' ? 55 : 45,
      itemStyle: {
        color: STATUS_COLORS[step.status] || '#d9d9d9',
        borderColor: step.status === 'running' ? '#1890ff' : 'transparent',
        borderWidth: step.status === 'running' ? 3 : 0,
        shadowBlur: step.status === 'running' ? 15 : 0,
        shadowColor: step.status === 'running' ? 'rgba(24,144,255,0.4)' : 'transparent',
      },
      label: {
        show: true,
        formatter: [
          `{name|${step.name}}`,
          step.confidence !== undefined ? `{conf|置信度: ${(step.confidence * 100).toFixed(0)}%}` : '',
          step.duration !== undefined ? `{dur|耗时: ${step.duration.toFixed(1)}s}` : '',
        ].filter(Boolean).join('\n'),
        rich: {
          name: { fontSize: 12, fontWeight: 'bold' as const, color: '#333', lineHeight: 20 },
          conf: { fontSize: 10, color: '#666', lineHeight: 16 },
          dur: { fontSize: 10, color: '#999', lineHeight: 16 },
        },
      },
    }));

    const links = steps.slice(0, -1).map((step, i) => ({
      source: step.name,
      target: steps[i + 1].name,
      lineStyle: {
        color: (step.status === 'completed' && steps[i + 1].status !== 'pending')
          ? '#52c41a' : '#d9d9d9',
        width: (step.status === 'completed' && steps[i + 1].status !== 'pending') ? 3 : 1.5,
        curveness: 0.1,
      },
      symbol: ['none', 'arrow'],
      symbolSize: 8,
    }));

    instanceRef.current!.setOption({
      tooltip: {},
      animationDuration: 500,
      animationEasingUpdate: 'quinticInOut',
      series: [{
        type: 'graph',
        layout: 'none',
        roam: false,
        data: nodes,
        links: links,
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: 8,
        emphasis: { focus: 'adjacency' },
      }],
    }, true);
  }, [steps, activeStep]);

  return <div ref={chartRef} style={{ width: '100%', height: 180 }} aria-label="Agent协作流程图" role="img" />;
};

export default AgentDAGChart;
