/** thread 标题/时间格式化（工作台、我的任务、报告中心共用） */

export function formatDate(s?: string): string {
  if (!s) return "—";
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return s;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** 解析 thread 标题「品类 · 市场」→ {name, market} */
export function parseTitle(title?: string): { name: string; market: string } {
  if (!title) return { name: "未命名任务", market: "—" };
  const idx = title.lastIndexOf(" · ");
  if (idx === -1) return { name: title, market: "—" };
  return { name: title.slice(0, idx), market: title.slice(idx + 3) };
}
