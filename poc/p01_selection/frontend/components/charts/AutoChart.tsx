"use client";
import React, { useMemo } from "react";
import { AgentChart, chartDataToOption, type ChartData } from "./AgentChart";

/**
 * AutoChart: 自动检测 HTML table 中的数值列，渲染为 ECharts 图表。
 * 当表格包含 ≥1 列数值数据且 ≥2 行时自动触发。
 * 用法：包裹 <table> 元素，在表格下方自动追加图表。
 */

interface AutoChartProps {
  children: React.ReactNode;
}

/** 从 React table 子元素中提取文本行列 */
function extractTableData(children: React.ReactNode): { headers: string[]; rows: string[][] } {
  const headers: string[] = [];
  const rows: string[][] = [];

  React.Children.forEach(children, (child) => {
    if (!React.isValidElement(child)) return;
    const tag = child.type as string;
    const childProps = child.props as { children?: React.ReactNode };

    if (tag === "thead") {
      React.Children.forEach(childProps.children, (tr) => {
        if (!React.isValidElement(tr)) return;
        const trProps = tr.props as { children?: React.ReactNode };
        React.Children.forEach(trProps.children, (th) => {
          if (!React.isValidElement(th)) return;
          headers.push(extractText(th));
        });
      });
    } else if (tag === "tbody") {
      React.Children.forEach(childProps.children, (tr) => {
        if (!React.isValidElement(tr)) return;
        const trProps = tr.props as { children?: React.ReactNode };
        const row: string[] = [];
        React.Children.forEach(trProps.children, (td) => {
          if (!React.isValidElement(td)) return;
          row.push(extractText(td));
        });
        if (row.length > 0) rows.push(row);
      });
    }
  });

  return { headers, rows };
}

/** 递归提取 React 节点中的纯文本 */
function extractText(node: React.ReactNode): string {
  if (typeof node === "string") return node;
  if (typeof node === "number") return String(node);
  if (!React.isValidElement(node)) return "";
  const props = node.props as { children?: React.ReactNode };
  if (!props.children) return "";
  if (typeof props.children === "string") return props.children;
  if (typeof props.children === "number") return String(props.children);
  let result = "";
  React.Children.forEach(props.children, (c) => {
    result += extractText(c);
  });
  return result;
}

/** 解析数字（支持 $、¥、%、逗号、K/M 后缀） */
function parseNumeric(s: string): number | null {
  const cleaned = s.trim().replace(/[$¥€£,\s%]/g, "");
  if (!cleaned) return null;
  // K/M 后缀
  const kmMatch = cleaned.match(/^([+-]?\d+\.?\d*)\s*([KkMm])$/);
  if (kmMatch) {
    const val = parseFloat(kmMatch[1]);
    const mult = kmMatch[2].toLowerCase() === "k" ? 1000 : 1000000;
    return isNaN(val) ? null : val * mult;
  }
  const val = parseFloat(cleaned);
  return isNaN(val) ? null : val;
}

/** 判断一列数据是否为数值列（>60% 的非空单元格可解析为数字） */
function isNumericColumn(values: string[]): boolean {
  const nonEmpty = values.filter((v) => v.trim() !== "");
  if (nonEmpty.length < 2) return false;
  const numCount = nonEmpty.filter((v) => parseNumeric(v) !== null).length;
  return numCount / nonEmpty.length > 0.6;
}

/** 自动推断图表类型 */
function inferChartType(numericCols: number, rows: number): ChartData["type"] {
  if (numericCols === 1 && rows <= 8) return "pie";
  if (rows > 12) return "line";
  return "bar";
}

export function AutoChart({ children }: AutoChartProps) {
  const chartData = useMemo(() => {
    const { headers, rows } = extractTableData(children);
    if (headers.length < 2 || rows.length < 2) return null;

    // 找出数值列
    const numericColIndices: number[] = [];
    for (let col = 1; col < headers.length; col++) {
      const colValues = rows.map((row) => row[col] || "");
      if (isNumericColumn(colValues)) {
        numericColIndices.push(col);
      }
    }

    if (numericColIndices.length === 0) return null;

    // 第一列作为 X 轴标签
    const xAxis = rows.map((row) => row[0] || "");
    const chartType = inferChartType(numericColIndices.length, rows.length);

    const series = numericColIndices.map((colIdx) => ({
      name: headers[colIdx] || `列${colIdx}`,
      data: rows.map((row) => parseNumeric(row[colIdx] || "") ?? 0),
    }));

    return { type: chartType, xAxis, series } as ChartData;
  }, [children]);

  if (!chartData) {
    return <table className="w-full border-collapse text-sm">{children}</table>;
  }

  return (
    <div className="my-2">
      <table className="w-full border-collapse text-sm">{children}</table>
      <div className="mt-3">
        <AgentChart option={chartDataToOption(chartData)} height={280} />
      </div>
    </div>
  );
}
