import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Next.js Middleware — 路由守卫
 *
 * 1. 未登录用户访问 /dashboard → 重定向到 /login
 * 2. 已登录用户访问 /login 或 /register → 重定向到 /dashboard
 *
 * 判断依据：cookie `auth_token`（由前端 saveAuth 写入）。
 * Middleware 在 Edge Runtime 运行，不能读 localStorage，
 * 所以我们在 saveAuth 时同时写 cookie，Middleware 读 cookie。
 */

const PROTECTED = ["/dashboard"];
const AUTH_PAGES = ["/login", "/register"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get("auth_token")?.value;

  // Unauthenticated user trying to access protected pages → redirect to landing
  if (PROTECTED.some((p) => pathname.startsWith(p)) && !token) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }

  // Authenticated user visiting login/register → redirect to dashboard
  if (AUTH_PAGES.some((p) => pathname.startsWith(p)) && token) {
    const url = request.nextUrl.clone();
    url.pathname = "/dashboard";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/login", "/register"],
};
