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
import { BACKEND_BASE } from "@/lib/graphql-client";

let _warmedUp = false;
function warmUpBackend() {
  if (_warmedUp) return;
  _warmedUp = true;
  fetch(`${BACKEND_BASE}/healthz`, { mode: "cors" }).catch(() => {});
}

export function AppShell() {
  const activeId = useAtomValue(activeThreadIdAtom);
  const draft = useAtomValue(draftCategoryAtom);
  const page = useAtomValue(activePageAtom);
  const setThreads = useSetAtom(threadsAtom);
  const isChat = !!activeId || !!draft;
  const isHome = page === "home";

  React.useEffect(() => { warmUpBackend(); }, []);

  React.useEffect(() => {
    if (isChat) return;
    let alive = true;
    (async () => {
      try {
        const t = await fetchThreads();
        if (alive) setThreads(t);
      } catch {}
    })();
    return () => { alive = false; };
  }, [isChat, setThreads]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[var(--gray-3)]">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <div className="flex min-h-0 flex-1 overflow-hidden">
          {isChat ? (
            <main className="min-w-0 flex-1 overflow-hidden bg-[var(--gray-1)]">
              <ChatView />
            </main>
          ) : isHome ? (
            <>
              <main className="min-w-0 flex-1 overflow-y-auto bg-[var(--gray-3)] p-5">
                <WorkspaceHome />
              </main>
              <RightRail />
            </>
          ) : (
            <main className="min-w-0 flex-1 overflow-y-auto bg-[var(--gray-3)] p-5">
              {renderPage(page)}
            </main>
          )}
        </div>
      </div>
    </div>
  );
}
