"use client";
import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated, getStoredPlan, getStoredEmail, checkUsage, UserPlan, PLAN_NAMES } from "@/lib/auth";

interface AuthGuardProps {
  children: React.ReactNode;
  /** Minimum plan required; defaults to "free" (any logged-in user) */
  requiredPlan?: UserPlan;
}

const PLAN_ORDER: Record<UserPlan, number> = { free: 0, pro: 1, enterprise: 2 };

function hasPlanAccess(userPlan: UserPlan, requiredPlan: UserPlan): boolean {
  return PLAN_ORDER[userPlan] >= PLAN_ORDER[requiredPlan];
}

export function AuthGuard({ children, requiredPlan = "free" }: AuthGuardProps) {
  const router = useRouter();
  const [status, setStatus] = useState<"checking" | "ok" | "no_auth" | "no_plan">("checking");
  const [userPlan, setUserPlan] = useState<UserPlan>("free");

  useEffect(() => {
    if (!isAuthenticated()) {
      setStatus("no_auth");
      return;
    }
    const plan = getStoredPlan();
    setUserPlan(plan);
    if (!hasPlanAccess(plan, requiredPlan)) {
      setStatus("no_plan");
    } else {
      setStatus("ok");
    }
  }, [requiredPlan]);

  if (status === "checking") {
    return (
      <div className="flex h-screen items-center justify-center bg-white">
        <div className="animate-pulse text-neutral-400 text-sm">加载中...</div>
      </div>
    );
  }

  if (status === "no_auth") {
    return (
      <div className="flex h-screen items-center justify-center bg-white">
        <div className="text-center max-w-sm px-6">
          <div className="mb-4 text-5xl">🔒</div>
          <h2 className="text-xl font-semibold text-neutral-900 mb-2">请先登录</h2>
          <p className="text-sm text-neutral-500 mb-6">登录后即可使用 SelectPilot 的全部功能</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => router.push("/login")}
              className="rounded-full bg-neutral-900 px-6 py-2.5 text-sm font-medium text-white hover:bg-neutral-800"
            >
              去登录
            </button>
            <button
              onClick={() => router.push("/register")}
              className="rounded-full border border-neutral-200 px-6 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
            >
              注册账号
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (status === "no_plan") {
    return (
      <div className="flex h-screen items-center justify-center bg-white">
        <div className="text-center max-w-sm px-6">
          <div className="mb-4 text-5xl">⬆️</div>
          <h2 className="text-xl font-semibold text-neutral-900 mb-2">需要升级套餐</h2>
          <p className="text-sm text-neutral-500 mb-2">
            当前套餐：<span className="font-medium text-neutral-700">{PLAN_NAMES[userPlan]}</span>
          </p>
          <p className="text-sm text-neutral-500 mb-6">
            此功能需要 <span className="font-medium text-violet-600">{PLAN_NAMES[requiredPlan]}</span> 及以上
          </p>
          <button
            onClick={() => router.push("/#pricing")}
            className="rounded-full bg-neutral-900 px-6 py-2.5 text-sm font-medium text-white hover:bg-neutral-800"
          >
            查看升级方案
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
