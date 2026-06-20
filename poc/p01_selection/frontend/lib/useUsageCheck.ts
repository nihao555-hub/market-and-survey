"use client";
import { useState, useCallback } from "react";
import { checkUsage, getStoredPlan, PLAN_NAMES } from "./auth";

interface UsageState {
  checking: boolean;
  blocked: boolean;
  message: string;
}

/**
 * Hook to check if the user can start a new research.
 * Returns a `canProceed()` async function that returns true if usage is ok.
 */
export function useUsageCheck() {
  const [state, setState] = useState<UsageState>({ checking: false, blocked: false, message: "" });

  const canProceed = useCallback(async (): Promise<boolean> => {
    setState({ checking: true, blocked: false, message: "" });
    const info = await checkUsage();
    if (!info) {
      setState({ checking: false, blocked: true, message: "请先登录" });
      return false;
    }
    if (!info.can_use) {
      const plan = PLAN_NAMES[info.plan];
      setState({
        checking: false,
        blocked: true,
        message: `本月 AI 调研次数已用完（${info.reports_used}/${info.reports_limit}）。当前方案：${plan}，升级后可获得更多次数。`,
      });
      return false;
    }
    setState({ checking: false, blocked: false, message: "" });
    return true;
  }, []);

  const dismiss = useCallback(() => {
    setState({ checking: false, blocked: false, message: "" });
  }, []);

  return { ...state, canProceed, dismiss };
}
