"use client";
import { useRef, useEffect, memo } from "react";
import type { EChartsOption } from "echarts";

interface AgentChartProps {
  option: EChartsOption;
  height?: number;
  className?: string;
}

function AgentChartInner({ option, height = 320, className = "" }: AgentChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<any>(null);

  useEffect(() => {
    if (!chartRef.current) return;
    let disposed = false;

    import("echarts").then((echarts) => {
      if (disposed || !chartRef.current) return;
      if (instanceRef.current) {
        instanceRef.current.dispose();
      }
      const chart = echarts.init(chartRef.current, undefined, { renderer: "canvas" });
      const mergedOption: EChartsOption = {
        backgroundColor: "transparent",
        grid: { left: 50, right: 20, top: 40, bottom: 40, containLabel: true },
        tooltip: { trigger: "axis", backgroundColor: "#fff", borderColor: "#e2e8f0", textStyle: { color: "#334155", fontSize: 12 } },
        ...option,
      };
      chart.setOption(mergedOption);
      instanceRef.current = chart;

      const resizeObserver = new ResizeObserver(() => chart.resize());
      resizeObserver.observe(chartRef.current);
      return () => resizeObserver.disconnect();
    });

    return () => {
      disposed = true;
      if (instanceRef.current) {
        instanceRef.current.dispose();
        instanceRef.current = null;
      }
    };
  }, [option]);

  return (
    <div
      ref={chartRef}
      className={`w-full rounded-xl border border-slate-200 bg-white ${className}`}
      style={{ height }}
    />
  );
}

export const AgentChart = memo(AgentChartInner);

export type ChartData = {
  type: "bar" | "line" | "pie" | "scatter" | "radar";
  title?: string;
  xAxis?: string[];
  series: Array<{
    name: string;
    data: number[];
    type?: string;
  }>;
};

export function chartDataToOption(chart: ChartData): EChartsOption {
  const colors = ["#F97316", "#06B6D4", "#EC4899", "#F59E0B", "#10B981", "#8B5CF6", "#EF4444"];

  if (chart.type === "pie") {
    return {
      title: chart.title ? { text: chart.title, left: "center", textStyle: { fontSize: 14, fontWeight: 600, color: "#0f172a" } } : undefined,
      tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
      color: colors,
      series: [{
        type: "pie",
        radius: ["40%", "70%"],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 6, borderColor: "#fff", borderWidth: 2 },
        label: { show: true, fontSize: 11, color: "#64748b" },
        data: chart.series[0]?.data.map((v, i) => ({
          value: v,
          name: chart.xAxis?.[i] || `Item ${i + 1}`,
        })) || [],
      }],
    };
  }

  if (chart.type === "radar") {
    const maxVal = Math.max(...(chart.series.flatMap(s => s.data) || [100]));
    return {
      title: chart.title ? { text: chart.title, left: "center", textStyle: { fontSize: 14, fontWeight: 600, color: "#0f172a" } } : undefined,
      color: colors,
      radar: {
        indicator: chart.xAxis?.map(name => ({ name, max: maxVal * 1.2 })) || [],
        shape: "circle",
      },
      series: [{
        type: "radar",
        data: chart.series.map(s => ({ value: s.data, name: s.name })),
      }],
    };
  }

  return {
    title: chart.title ? { text: chart.title, left: "center", textStyle: { fontSize: 14, fontWeight: 600, color: "#0f172a" } } : undefined,
    color: colors,
    xAxis: { type: "category", data: chart.xAxis || [], axisLabel: { fontSize: 11, color: "#94a3b8" }, axisLine: { lineStyle: { color: "#e2e8f0" } } },
    yAxis: { type: "value", axisLabel: { fontSize: 11, color: "#94a3b8" }, splitLine: { lineStyle: { color: "#f1f5f9" } } },
    legend: chart.series.length > 1 ? { bottom: 0, textStyle: { fontSize: 11, color: "#64748b" } } : undefined,
    series: chart.series.map((s) => ({
      name: s.name,
      type: (s.type || chart.type) as "bar" | "line" | "scatter",
      data: s.data,
      smooth: true,
      itemStyle: chart.type === "bar" ? { borderRadius: [4, 4, 0, 0] } : undefined,
      areaStyle: chart.type === "line" ? { opacity: 0.08 } : undefined,
    })),
  };
}
