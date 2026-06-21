/** @type {import('next').NextConfig} */
// 部署时设 NEXT_PUBLIC_BACKEND_BASE 为公网后端地址；本地回落 127.0.0.1:8001。
const BACKEND = process.env.NEXT_PUBLIC_BACKEND_BASE || "http://127.0.0.1:8001";
const nextConfig = {
  reactStrictMode: false, // 关闭以避免 SSE 订阅在 dev 下双订阅
  async rewrites() {
    // 把 /graphql、REST、认证接口代理到 FastAPI 后端，规避跨域
    return [
      { source: "/graphql", destination: `${BACKEND}/graphql` },
      { source: "/auth/:path*", destination: `${BACKEND}/auth/:path*` },
      { source: "/healthz", destination: `${BACKEND}/healthz` },
      { source: "/events", destination: `${BACKEND}/events` },
      { source: "/chat", destination: `${BACKEND}/chat` },
      { source: "/stop", destination: `${BACKEND}/stop` },
      { source: "/catchup", destination: `${BACKEND}/catchup` },
      { source: "/report-file", destination: `${BACKEND}/report-file` },
      { source: "/report-asset", destination: `${BACKEND}/report-asset` },
      { source: "/api/send-email", destination: "/api/send-email" },
      { source: "/api/:path*", destination: `${BACKEND}/:path*` },
    ];
  },
};
export default nextConfig;
