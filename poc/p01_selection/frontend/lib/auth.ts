"use client";
import { BACKEND_BASE } from "./graphql-client";

export type UserPlan = "free" | "pro" | "enterprise";

export interface UserInfo {
  email: string;
  name?: string;
  plan: UserPlan;
  reports_used: number;
  reports_limit: number;
  can_use: boolean;
}

/** Get token from localStorage */
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("auth_token");
}

/** Save auth data to localStorage */
export function saveAuth(token: string, email: string, plan: string) {
  localStorage.setItem("auth_token", token);
  localStorage.setItem("user_email", email);
  localStorage.setItem("user_plan", plan || "free");
}

/** Clear auth data from localStorage */
export function clearAuth() {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("user_email");
  localStorage.removeItem("user_plan");
}

/** Check if user is authenticated */
export function isAuthenticated(): boolean {
  return !!getToken();
}

/** Get stored plan */
export function getStoredPlan(): UserPlan {
  if (typeof window === "undefined") return "free";
  return (localStorage.getItem("user_plan") as UserPlan) || "free";
}

/** Get stored email */
export function getStoredEmail(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("user_email") || "";
}

/** Validate token with backend and get usage info */
export async function checkUsage(): Promise<UserInfo | null> {
  const token = getToken();
  if (!token) return null;
  try {
    const res = await fetch(`${BACKEND_BASE}/auth/usage?token=${encodeURIComponent(token)}`);
    if (!res.ok) return null;
    const data = await res.json();
    if (!data.ok) return null;
    return {
      email: getStoredEmail(),
      plan: data.plan,
      reports_used: data.reports_used,
      reports_limit: data.reports_limit,
      can_use: data.can_use,
    };
  } catch {
    // If backend is unreachable, use stored plan
    return {
      email: getStoredEmail(),
      plan: getStoredPlan(),
      reports_used: 0,
      reports_limit: -1,
      can_use: true,
    };
  }
}

/** Plan display names */
export const PLAN_NAMES: Record<UserPlan, string> = {
  free: "免费版",
  pro: "专业版",
  enterprise: "企业版",
};

/** Plan feature limits description */
export const PLAN_FEATURES: Record<UserPlan, string[]> = {
  free: ["5 次 AI 调研/月", "1 个品类追踪", "基础数据浏览"],
  pro: ["100 次 AI 调研/月", "10 品类追踪", "ECharts 图表", "26 国数据", "利润测算"],
  enterprise: ["无限 AI 调研", "无限品类", "API 访问", "多人协作", "SLA 保障"],
};
