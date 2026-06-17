/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false, // 关闭以避免 SSE 订阅在 dev 下双订阅
  async rewrites() {
    // 把 /graphql 和 REST 接口代理到 FastAPI 后端，规避跨域
    return [
      { source: "/graphql", destination: "http://127.0.0.1:8001/graphql" },
      { source: "/api/:path*", destination: "http://127.0.0.1:8001/:path*" },
    ];
  },
};
export default nextConfig;
