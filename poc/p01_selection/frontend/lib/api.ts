/**
 * 管理类页面统一数据访问层（GraphQL Query / Mutation 的类型化封装）。
 * 页面只调用这里的函数，不直接拼 GraphQL 字符串。
 */
import { gqlRequest } from "./graphql-client";
import type { ThreadSummary, ResearchKind } from "./agent-types";

const THREAD_FIELDS = "id title updatedAt activeStreamId isFavorite kind";

// ─────────── 线程：列表 / 收藏 / 回收站 ───────────
export async function fetchThreads(): Promise<ThreadSummary[]> {
  const d = await gqlRequest<{ threads: ThreadSummary[] }>(
    `query { threads { ${THREAD_FIELDS} } }`
  );
  return d.threads || [];
}

export async function fetchFavoriteThreads(): Promise<ThreadSummary[]> {
  const d = await gqlRequest<{ favoriteThreads: ThreadSummary[] }>(
    `query { favoriteThreads { ${THREAD_FIELDS} } }`
  );
  return d.favoriteThreads || [];
}

export async function fetchTrashedThreads(): Promise<ThreadSummary[]> {
  const d = await gqlRequest<{ trashedThreads: ThreadSummary[] }>(
    `query { trashedThreads { ${THREAD_FIELDS} } }`
  );
  return d.trashedThreads || [];
}

// 按调研类型列出历史调研（供 5 个功能页各自展示本类型历史）
export async function fetchThreadsByKind(kind: ResearchKind): Promise<ThreadSummary[]> {
  const d = await gqlRequest<{ threadsByKind: ThreadSummary[] }>(
    `query($kind: String!) { threadsByKind(kind: $kind) { ${THREAD_FIELDS} } }`,
    { kind }
  );
  return d.threadsByKind || [];
}

export async function toggleFavorite(threadId: string): Promise<boolean> {
  const d = await gqlRequest<{ toggleFavorite: boolean }>(
    `mutation($id: String!) { toggleFavorite(threadId: $id) }`,
    { id: threadId }
  );
  return d.toggleFavorite;
}

export async function deleteThread(threadId: string): Promise<boolean> {
  const d = await gqlRequest<{ deleteThread: boolean }>(
    `mutation($id: String!) { deleteThread(threadId: $id) }`,
    { id: threadId }
  );
  return d.deleteThread;
}

export async function restoreThread(threadId: string): Promise<boolean> {
  const d = await gqlRequest<{ restoreThread: boolean }>(
    `mutation($id: String!) { restoreThread(threadId: $id) }`,
    { id: threadId }
  );
  return d.restoreThread;
}

export async function purgeThread(threadId: string): Promise<boolean> {
  const d = await gqlRequest<{ purgeThread: boolean }>(
    `mutation($id: String!) { purgeThread(threadId: $id) }`,
    { id: threadId }
  );
  return d.purgeThread;
}

// ─────────── 数据源 ───────────
export interface DataSource {
  id: string;
  name: string;
  description: string;
  kind: string;
  frequency: string;
  connected: boolean;
  builtin: boolean;
}
const DS_FIELDS = "id name description kind frequency connected builtin";

export async function fetchDataSources(): Promise<DataSource[]> {
  const d = await gqlRequest<{ dataSources: DataSource[] }>(
    `query { dataSources { ${DS_FIELDS} } }`
  );
  return d.dataSources || [];
}

export async function createDataSource(input: {
  name: string;
  description?: string;
  kind?: string;
  frequency?: string;
}): Promise<DataSource> {
  const d = await gqlRequest<{ createDataSource: DataSource }>(
    `mutation($name: String!, $description: String!, $kind: String!, $frequency: String!) {
       createDataSource(name: $name, description: $description, kind: $kind, frequency: $frequency) { ${DS_FIELDS} }
     }`,
    {
      name: input.name,
      description: input.description ?? "",
      kind: input.kind ?? "trends",
      frequency: input.frequency ?? "每日",
    }
  );
  return d.createDataSource;
}

export async function setDataSourceConnected(
  sourceId: string,
  connected: boolean
): Promise<boolean> {
  const d = await gqlRequest<{ setDataSourceConnected: boolean }>(
    `mutation($id: String!, $c: Boolean!) { setDataSourceConnected(sourceId: $id, connected: $c) }`,
    { id: sourceId, c: connected }
  );
  return d.setDataSourceConnected;
}

// ─────────── 订阅规则 ───────────
export interface Monitor {
  id: string;
  name: string;
  description: string;
  kind: string;
  cadence: string;
  enabled: boolean;
}
const MON_FIELDS = "id name description kind cadence enabled";

export async function fetchMonitors(): Promise<Monitor[]> {
  const d = await gqlRequest<{ monitors: Monitor[] }>(
    `query { monitors { ${MON_FIELDS} } }`
  );
  return d.monitors || [];
}

export async function createMonitor(input: {
  name: string;
  description?: string;
  kind?: string;
  cadence?: string;
}): Promise<Monitor> {
  const d = await gqlRequest<{ createMonitor: Monitor }>(
    `mutation($name: String!, $description: String!, $kind: String!, $cadence: String!) {
       createMonitor(name: $name, description: $description, kind: $kind, cadence: $cadence) { ${MON_FIELDS} }
     }`,
    {
      name: input.name,
      description: input.description ?? "",
      kind: input.kind ?? "trend",
      cadence: input.cadence ?? "每日",
    }
  );
  return d.createMonitor;
}

export async function setMonitorEnabled(
  monitorId: string,
  enabled: boolean
): Promise<boolean> {
  const d = await gqlRequest<{ setMonitorEnabled: boolean }>(
    `mutation($id: String!, $e: Boolean!) { setMonitorEnabled(monitorId: $id, enabled: $e) }`,
    { id: monitorId, e: enabled }
  );
  return d.setMonitorEnabled;
}

export async function deleteMonitor(monitorId: string): Promise<boolean> {
  const d = await gqlRequest<{ deleteMonitor: boolean }>(
    `mutation($id: String!) { deleteMonitor(monitorId: $id) }`,
    { id: monitorId }
  );
  return d.deleteMonitor;
}

// ─────────── 每日数据刷新（定时获取真实数据落库）───────────
export interface DataSnapshot {
  id: string;
  term: string;
  source: string;
  geo: string;
  tier: number;
  status: string;          // ok / empty / error / unavailable
  realData: boolean;       // 是否真实抓到（反幻觉标记）
  summary: string;
  payload: any;
  capturedAt?: string | null;
}

export interface RefreshStatus {
  status: string;          // never_run / running / done / failed
  runId?: string | null;
  trigger?: string | null;
  startedAt?: string | null;
  finishedAt?: string | null;
  elapsedSec?: number | null;
  tier2ChannelOk: boolean;
  terms: string[];
  counts: Record<string, number>;
}

const SNAPSHOT_FIELDS =
  "id term source geo tier status realData summary payload capturedAt";
const REFRESH_FIELDS =
  "status runId trigger startedAt finishedAt elapsedSec tier2ChannelOk terms counts";

export async function fetchDailyRefreshStatus(): Promise<RefreshStatus> {
  const d = await gqlRequest<{ dailyRefreshStatus: RefreshStatus }>(
    `query { dailyRefreshStatus { ${REFRESH_FIELDS} } }`
  );
  return d.dailyRefreshStatus;
}

export async function fetchDataSnapshots(opts?: {
  term?: string;
  source?: string;
  limit?: number;
}): Promise<DataSnapshot[]> {
  const d = await gqlRequest<{ dataSnapshots: DataSnapshot[] }>(
    `query($term: String, $source: String, $limit: Int!) {
       dataSnapshots(term: $term, source: $source, limit: $limit) { ${SNAPSHOT_FIELDS} }
     }`,
    { term: opts?.term ?? null, source: opts?.source ?? null, limit: opts?.limit ?? 200 }
  );
  return d.dataSnapshots || [];
}

export async function fetchAllSnapshots(opts?: {
  source?: string;
  limit?: number;
}): Promise<DataSnapshot[]> {
  const d = await gqlRequest<{ allSnapshots: DataSnapshot[] }>(
    `query($source: String, $limit: Int!) {
       allSnapshots(source: $source, limit: $limit) { ${SNAPSHOT_FIELDS} }
     }`,
    { source: opts?.source ?? null, limit: opts?.limit ?? 500 }
  );
  return d.allSnapshots || [];
}

export async function triggerDailyRefresh(): Promise<boolean> {
  const d = await gqlRequest<{ triggerDailyRefresh: boolean }>(
    `mutation { triggerDailyRefresh }`
  );
  return d.triggerDailyRefresh;
}

// ─────────── API Key ───────────
export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  last4: string;
  revoked: boolean;
  createdAt?: string | null;
  lastUsedAt?: string | null;
}
const KEY_FIELDS = "id name prefix last4 revoked createdAt lastUsedAt";

export async function fetchApiKeys(): Promise<ApiKey[]> {
  const d = await gqlRequest<{ apiKeys: ApiKey[] }>(
    `query { apiKeys { ${KEY_FIELDS} } }`
  );
  return d.apiKeys || [];
}

export async function createApiKey(
  name: string
): Promise<{ key: ApiKey; token: string }> {
  const d = await gqlRequest<{ createApiKey: { key: ApiKey; token: string } }>(
    `mutation($name: String!) { createApiKey(name: $name) { key { ${KEY_FIELDS} } token } }`,
    { name }
  );
  return d.createApiKey;
}

export async function revokeApiKey(keyId: string): Promise<boolean> {
  const d = await gqlRequest<{ revokeApiKey: boolean }>(
    `mutation($id: String!) { revokeApiKey(keyId: $id) }`,
    { id: keyId }
  );
  return d.revokeApiKey;
}

// ─────────── 设置 ───────────
export interface Settings {
  displayName: string;
  email: string;
  plan: string;
  defaultModel: string;
  defaultMarket: string;
  defaultPositioning: string;
  notifyEmail: boolean;
  notifyInApp: boolean;
  targetCountries: string[];
  refreshHourUtc: number;
}
const SETTINGS_FIELDS =
  "displayName email plan defaultModel defaultMarket defaultPositioning notifyEmail notifyInApp targetCountries refreshHourUtc";

export async function fetchSettings(): Promise<Settings> {
  const d = await gqlRequest<{ settings: Settings }>(
    `query { settings { ${SETTINGS_FIELDS} } }`
  );
  return d.settings;
}

export async function updateSettings(patch: Partial<Settings>): Promise<Settings> {
  const d = await gqlRequest<{ updateSettings: Settings }>(
    `mutation($displayName: String, $email: String, $defaultModel: String,
              $defaultMarket: String, $defaultPositioning: String,
              $notifyEmail: Boolean, $notifyInApp: Boolean,
              $targetCountries: [String!], $refreshHourUtc: Int) {
       updateSettings(displayName: $displayName, email: $email, defaultModel: $defaultModel,
                      defaultMarket: $defaultMarket, defaultPositioning: $defaultPositioning,
                      notifyEmail: $notifyEmail, notifyInApp: $notifyInApp,
                      targetCountries: $targetCountries, refreshHourUtc: $refreshHourUtc) { ${SETTINGS_FIELDS} }
     }`,
    {
      displayName: patch.displayName ?? null,
      email: patch.email ?? null,
      defaultModel: patch.defaultModel ?? null,
      defaultMarket: patch.defaultMarket ?? null,
      defaultPositioning: patch.defaultPositioning ?? null,
      notifyEmail: patch.notifyEmail ?? null,
      notifyInApp: patch.notifyInApp ?? null,
      targetCountries: patch.targetCountries ?? null,
      refreshHourUtc: patch.refreshHourUtc ?? null,
    }
  );
  return d.updateSettings;
}
