/**
 * GraphQL 客户端（Query / Mutation 走 fetch POST 到后端 /graphql）。
 * 订阅不走这里 —— 改用后端原生 SSE /events（见 useAgentChatSubscription）。
 *
 * 部署时设 NEXT_PUBLIC_BACKEND_BASE 为后端公网地址（如 https://xxx.onrender.com）。
 * 未设置时：
 *   - 浏览器端（生产）：使用相对路径 ""，走 Vercel rewrites 代理到后端
 *   - 服务端/开发模式：用 127.0.0.1:8001 直连本地后端
 */
function resolveBackendBase(): string {
  const explicit = process.env.NEXT_PUBLIC_BACKEND_BASE;
  if (explicit) return explicit;
  // 浏览器端生产环境：用相对路径走 rewrites
  if (typeof window !== "undefined" && window.location.hostname !== "localhost") {
    return "";
  }
  // 本地开发 / SSR
  return "http://127.0.0.1:8001";
}

export const BACKEND_BASE = resolveBackendBase();

// 后端开启鉴权（BACKEND_AUTH_REQUIRED=1）时需配置此值；dev 模式留空即可。
export const BACKEND_API_KEY = process.env.NEXT_PUBLIC_BACKEND_API_KEY || "";

const GRAPHQL_HTTP = `${BACKEND_BASE}/graphql`;

/** 普通 query / mutation（fetch POST） */
export async function gqlRequest<T = any>(
  query: string,
  variables?: Record<string, unknown>
): Promise<T> {
  const res = await fetch(GRAPHQL_HTTP, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, variables }),
  });
  const json = await res.json();
  if (json.errors) {
    throw new Error(json.errors.map((e: any) => e.message).join("; "));
  }
  return json.data as T;
}
