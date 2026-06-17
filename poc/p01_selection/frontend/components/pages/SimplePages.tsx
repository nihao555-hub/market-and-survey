"use client";
import React from "react";
import { useSetAtom } from "jotai";
import { Star, Trash2, Plus } from "lucide-react";
import { activePageAtom, activeThreadIdAtom, draftCategoryAtom } from "@/lib/atoms";
import { PageContainer, PageHeader, Panel, EmptyState } from "./primitives";

export function FavoritesPage() {
  const setPage = useSetAtom(activePageAtom);
  const setActiveId = useSetAtom(activeThreadIdAtom);
  const setDraft = useSetAtom(draftCategoryAtom);
  return (
    <PageContainer>
      <PageHeader
        icon={<Star className="h-5 w-5" />}
        title="收藏夹"
        subtitle="收藏的品类、竞品与报告，方便随时回看与对比。"
      />
      <Panel bodyClassName="p-0">
        <EmptyState
          icon={<Star className="h-6 w-6" />}
          title="收藏夹为空"
          hint="在任务或报告中点击收藏图标，即可把重要内容固定到这里。"
          action={
            <button
              onClick={() => {
                setPage("home");
                setActiveId(null);
                setDraft(null);
              }}
              className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-3.5 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-hover"
            >
              <Plus className="h-4 w-4" />
              去发起调研
            </button>
          }
        />
      </Panel>
    </PageContainer>
  );
}

export function TrashPage() {
  return (
    <PageContainer>
      <PageHeader
        icon={<Trash2 className="h-5 w-5" />}
        title="回收站"
        subtitle="已删除的任务与报告会在这里保留 30 天，可恢复或彻底清除。"
      />
      <Panel bodyClassName="p-0">
        <EmptyState
          icon={<Trash2 className="h-6 w-6" />}
          title="回收站是空的"
          hint="删除的内容会临时保留在这里，30 天后自动清除。"
        />
      </Panel>
    </PageContainer>
  );
}
