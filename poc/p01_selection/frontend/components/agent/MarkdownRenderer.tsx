"use client";
import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { BACKEND_BASE } from "@/lib/graphql-client";

/**
 * Markdown 流式渲染（steering §9.4.1）。memo 化避免流式时频繁 re-render。
 * 图片本地路径自动指向后端静态资源（直连 BACKEND_BASE，与 GraphQL/SSE 一致，
 * 避免 Next dev rewrite 对静态资源 + query 的边界问题）。
 *
 * 报告里图片来源三种形态：
 *   1. 远程图  https://...（Amazon CDN 主图）→ 原样
 *   2. 本地截图 evidence/xxx.png、keepa_charts/xxx.png（相对 reports/ 根）
 *   3. 本地化资源 assets/xxx.jpg（相对报告目录，已 localize）
 * 后端 /report-asset?path= 统一以 reports/ 为根解析，故相对路径直接透传即可。
 */
// 模型偶尔把工具调用以 DSML / DeepSeek 控制标记写进正文，渲染出来是乱码尾巴。
// 后端已在生成处剔除；此处再兜一层，保证历史线程也能干净渲染。
const CTRL_TAG_RE = /<[^>\n]{0,40}(?:DSML|tool[\u2581_\s]?calls)[^>]*>/i;
const TRAILING_INTENT_RE =
  /(?:\n\s*)+[^\n]*?(?:补跑|继续(?:输出|调用)|调用(?:以下)?工具|工具调用|我(?:先|现在)[^\n]*工具)[^\n]*$/;

function stripControlMarkup(text: string): string {
  if (!text) return text;
  const m = CTRL_TAG_RE.exec(text);
  if (!m) return text;
  // 先去尾部空白，让 TRAILING_INTENT_RE 的 $ 锚点能命中过渡句（与后端 rstrip 一致）。
  return text.slice(0, m.index).trimEnd().replace(TRAILING_INTENT_RE, "").trimEnd();
}

function rewriteImg(src: string): string {
  if (!src) return src;
  const s = src.trim();
  if (/^https?:\/\//i.test(s)) return s; // 远程图原样
  if (s.startsWith("data:")) return s; // 内联 base64
  // 去掉前导 ./ 或 / ，统一成相对 reports/ 的路径
  const clean = s.replace(/^\.?\//, "");
  return `${BACKEND_BASE}/report-asset?path=${encodeURIComponent(clean)}`;
}

export const MarkdownRenderer = React.memo(function MarkdownRenderer({
  text,
}: {
  text: string;
}) {
  const clean = React.useMemo(() => stripControlMarkup(text), [text]);
  return (
    <div className="markdown-body text-[15px] leading-relaxed text-gray-800">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          img: ({ src, alt }) => <ReportImage src={rewriteImg(src || "")} alt={alt || ""} />,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer">
              {children}
            </a>
          ),
        }}
      >
        {clean}
      </ReactMarkdown>
    </div>
  );
});

/** 报告内图片：圆角 + 边框 + 说明文字，加载失败时优雅降级为占位条。 */
function ReportImage({ src, alt }: { src: string; alt: string }) {
  const [failed, setFailed] = React.useState(false);
  if (failed) {
    return (
      <span className="my-2 flex items-center gap-2 rounded-lg border border-dashed border-hairline bg-surface-1 px-3 py-2 text-xs text-ink-subtle">
        图片暂不可用{alt ? `：${alt}` : ""}
      </span>
    );
  }
  return (
    <figure className="my-3">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={alt}
        loading="lazy"
        onError={() => setFailed(true)}
        className="max-h-[420px] w-auto max-w-full rounded-lg border border-hairline object-contain"
      />
      {alt && <figcaption className="mt-1 text-xs text-ink-subtle">{alt}</figcaption>}
    </figure>
  );
}
