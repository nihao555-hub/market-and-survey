"use client";
import React from "react";
import { useAtomValue } from "jotai";
import { activeThreadIdAtom, draftCategoryAtom, activePageAtom } from "@/lib/atoms";
import { Sidebar } from "@/components/Sidebar";
import { TopBar } from "@/components/TopBar";
import { WorkspaceHome } from "@/components/WorkspaceHome";
import { RightRail } from "@/components/RightRail";
import { ChatView } from "@/components/ChatView";
import { renderPage } from "@/components/pages/registry";

export function AppShell() {
  const activeId = useAtomValue(activeThreadIdAtom);
  const draft = useAtomValue(draftCategoryAtom);
  const page = useAtomValue(activePageAtom);
  const isChat = !!activeId || !!draft;
  const isHome = page === "home";

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
