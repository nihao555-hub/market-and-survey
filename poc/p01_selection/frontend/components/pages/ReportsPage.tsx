"use client";
import React from "react";
import { useAtom, useSetAtom } from "jotai";
import { FileText, ArrowRight, FileBarChart } from "lucide-react";
import { activeThreadIdAtom, threadsAtom } from "@/lib/atoms";
import { gqlRequest } from "@/lib/graphql-client";
import { formatDate, parseTitle } from "@/lib/thread-format";
import type { ThreadSummary } from "@/lib/agent-types";
import { PageContainer, PageHeader, Panel, EmptyState } from "./primitives";

const THREADS_QUERY = /* GraphQL */ `
  query Threads { threads { id title updatedAt activeStreamId } }
`;

export function ReportsPage() {
  const [threads, setThreads] = useAtom(threadsAtom);
  const setActiveId = useSetAtom(activeThreadIdAtom);

  React.useEffect(() => {
    (async () => {
      try {
        const data = await gqlRequest<{ threads: ThreadSummary[] }>(THREADS_QUERY);
        setThreads(data.threads || []);
      } catch {
        /* 静默 */
      }
    })();
  }, [setThreads]);

  const reports = threads.filter((t) => !t.activeStreamId);

  return (
    <PageContainer>
      <PageHeader
        icon={<FileText className="h-5 w-5" />}
        title="报告中心"
        subtitle="已完成调研任务产出的选品决策报告，可回看完整分析与证据链。"
      />

      {reports.length === 0 ? (
        <Panel bodyClassName="p-0">
          <EmptyState
            icon={<FileBarChart className="h-6 w-6" />}
            title="还没有可查看的报告"
            hint="完成一个调研任务后，AI 生成的选品报告会自动归档在这里。"
          />
        </Panel>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {reports.map((t) => {
            const { name, market } = parseTitle(t.title);
            return (
              <button
                key={t.id}
                onClick={() => setActiveId(t.id)}
                className="group flex flex-col rounded-2xl border border-hairline bg-white p-5 text-left transition-all hover:-translate-y-0.5 hover:border-brand/30 hover:shadow-sm"
              >
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand/10 text-brand">
                  <FileText className="h-5 w-5" />
                </span>
                <div className="mt-3 line-clamp-1 text-sm font-semibold text-ink">{name}</div>
                <div className="mt-1 text-xs text-ink-subtle">{market}</div>
                <div className="mt-4 flex items-center justify-between border-t border-hairline pt-3 text-[11px] text-ink-tertiary">
                  <span>{formatDate(t.updatedAt)}</span>
                  <span className="inline-flex items-center gap-0.5 text-brand opacity-0 transition-opacity group-hover:opacity-100">
                    查看报告 <ArrowRight className="h-3.5 w-3.5" />
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </PageContainer>
  );
}
