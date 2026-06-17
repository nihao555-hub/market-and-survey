/**
 * GraphQL 客户端（Query / Mutation 走 fetch POST 到后端 /graphql）。
 * 订阅不走这里 —— 改用后端原生 SSE /events（见 useAgentChatSubscription）。
 *
 * 直连后端 :8001（CORS 已开），避免 Next dev 代理对 SSE 的缓冲问题。
 */
export const BACKEND_BASE =
  process.env.NEXT_PUBLIC_BACKEND_BASE || "http://127.0.0.1:8001";

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
