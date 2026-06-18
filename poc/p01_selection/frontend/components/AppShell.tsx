"use client";
import React from "react";
import { useAtomValue, useSetAtom } from "jotai";
import { activeThreadIdAtom, draftCategoryAtom, activePageAtom, threadsAtom } from "@/lib/atoms";
import { Sidebar } from "@/components/Sidebar";
import { TopBar } from "@/components/TopBar";
import { WorkspaceHome } from "@/components/WorkspaceHome";
import { RightRail } from "@/components/RightRail";
import { ChatView } from "@/components/ChatView";
import { renderPage } from "@/components/pages/registry";
import { fetchThreads } from "@/lib/api";

export function AppShell() {
  const activeId = useAtomValue(activeThreadIdAtom);
  const draft = useAtomValue(draftCategoryAtom);
  const page = useAtomValue(activePageAtom);
  const setThreads = useSetAtom(threadsAtom);
  const isChat = !!activeId || !!draft;
  const isHome = page === "home";

  // 真实历史任务：从后端拉取，回到非会话态时刷新（侧边栏/首页/右栏共用此数据源）
  React.useEffect(() => {
    if (isChat) return;
    let alive = true;
    (async () => {
      try {
        const t = await fetchThreads();
        if (alive) setThreads(t);
      } catch {
        /* 后端未起时静默 */
      }
    })();
    return () => {
      alive = false;
    };
  }, [isChat, setThreads]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-surface-1">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <div className="flex min-h-0 flex-1 overflow-hidden">
          {isChat ? (
            <main className="min-w-0 flex-1 overflow-hidden bg-white">
              <ChatView />
            </main>
          ) : isHome ? (
            <>
              <main className="min-w-0 flex-1 overflow-y-auto">
                <WorkspaceHome />
              </main>
              <RightRail />
            </>
          ) : (
            <main className="min-w-0 flex-1 overflow-y-auto">{renderPage(page)}</main>
          )}
        </div>
      </div>
    </div>
  );
}
