# DESIGN.md — MarketAgent 统一 UI 规范

> 选品 & 市场调研 Agent 的设计系统。橙色系产品工具风格（非营销页）：
> 侧边栏 + 顶栏 + 工作区，承载调研发起、流式思考、报告渲染与各类管理页。
> 所有页面共用 `components/pages/primitives.tsx` 的组件库，令牌定义在 `tailwind.config.ts`。

## 设计哲学
- 克制、精确、安静的工具感；信息密度优先，装饰其次。
- 单一品牌强调色（橙 `#F97316`）：仅用于主操作、激活态、焦点环、链接、关键指标。不做大面积铺色（Hero 渐变除外）。
- 用 surface 层级 + 1px hairline 边框承担层次，阴影仅用于浮层 / 主按钮。
- 中性色走 slate 阶（`ink` / `surface` / `hairline`），保证文字对比与留白节奏。

## 配色令牌（`tailwind.config.ts`）
| 语义 | token | hex | 用途 |
|---|---|---|---|
| 品牌主色 | `brand` | `#F97316` | 主按钮 / 激活态 / 焦点环 / 链接 |
| 品牌 hover | `brand-hover` | `#EA580C` | 主按钮 hover |
| 品牌浅 | `brand-light` | `#FB923C` | 渐变中段 / 浅强调 |
| 品牌辅 | `brand2` | `#FBBF24` | Hero 渐变第二色（橙→琥珀） |
| 成功 | `success` | `#10B981` | 已完成 / 已连接 |
| 警告 | `warning` | `#F59E0B` | 提醒 / 待处理 |
| 危险 | `danger` | `#EF4444` | 失败 / 删除 / 吊销 |
| 信息 | `info` | `#3B82F6` | 分析中 / 中性提示 |
| 画布 | `canvas` | `#FFFFFF` | 页面 / 卡片背景 |
| 表面 | `surface-1..4` | `#F8FAFC`→`#CBD5E1` | 浅底 / hover / 分隔块 |
| 描边 | `hairline` | `#E2E8F0` | 1px 边框 / 分隔线 |
| 文字 | `ink` | `#0F172A` | 标题 / 强调正文 |
| 文字次 | `ink-muted` | `#475569` | 正文 |
| 文字弱 | `ink-subtle` | `#64748B` | 元信息 / 占位 |
| 文字微 | `ink-tertiary` | `#94A3B8` | 禁用 / 装饰图标 |

橙色渐变统一写法：`bg-gradient-to-br from-brand to-brand2`（或经 `via-brand-light`）。

## 字体
- Inter：400 正文 · 500 按钮/标签 · 600 标题。
- 等宽 JetBrains Mono：API token / ASIN / 端点路径。
- 字号阶梯：`text-[10px]`/`text-[11px]` 元信息 · `text-xs` 辅助 · `text-sm` 正文/控件 · `text-xl` 页面标题。

## 圆角 / 阴影 / 动效
- 圆角：`rounded-lg`(8) 按钮/输入 · `rounded-xl`(16) 小卡/StatTile · `rounded-2xl` 面板 · `rounded-full` 徽章/头像/开关。
- 阴影：`shadow-xs/sm` 卡片悬浮 · 主按钮 `shadow-sm`；列表与面板默认无阴影，用 hairline。
- 动效：`transition-colors`（200ms）为默认；骨架屏 `animate-pulse`；进行中状态点 `animate-pulse`。

## 间距（8pt 网格）
- 页面外壳 `PageContainer`：`max-w-[1180px] px-8 py-7`。
- 卡片内边距 `p-5`；行间距 `gap-2/3/4`；区块间 `space-y-4`。

## 共享组件库（`components/pages/primitives.tsx`）
全站页面只使用以下组件，不再各自手写样式，保证一致性。

| 组件 | 说明 |
|---|---|
| `PageContainer` | 统一页面外壳与留白 |
| `PageHeader` | 图标 + 标题 + 副标题 + 右侧 `actions` |
| `Panel` | 带标题/操作链接的卡片面板（`bodyClassName` 可定制内边距） |
| `EmptyState` | 空状态：图标 + 标题 + 提示 + CTA |
| `StatTile` | 指标小卡（label / value / delta / icon / tone） |
| `Button` | 5 变体 `primary/secondary/ghost/danger/outline` × 2 尺寸 `sm/md`，支持 `loading` |
| `StatusBadge` | 6 态 `running/done/pending/error/info/neutral`，圆点 + 文案 |
| `FilterTabs` | 过滤标签栏，带计数胶囊（受控 `value/onChange`） |
| `Switch` | 开关（受控 `checked/onChange`，品牌色激活） |
| `Skeleton` | 骨架屏占位（`animate-pulse`） |
| `DataTable<T>` | 列配置 `Column<T>` + 行数据 + 行点击 + 空态 |

### 状态语义对齐
- 分析中 → `running`（info 蓝，圆点呼吸）
- 已完成 / 已连接 / 生效中 → `done`（success 绿）
- 待开始 / 中性 → `pending` / `neutral`（slate）
- 失败 / 已吊销 → `error`（danger 红）

## 页面结构约定
1. `PageContainer` 包裹整页。
2. 顶部 `PageHeader`（右侧放主操作按钮，如「新建任务」「创建 API Key」）。
3. 概览指标用 `StatTile` 三列网格（可选）。
4. 主体用 `Panel` 分区；列表数据用 `DataTable`，卡片集合用响应式 `grid`。
5. 数据加载中渲染 `Skeleton`；无数据渲染 `EmptyState`（含引导 CTA）。
6. 所有写操作走乐观更新：先改本地状态，失败再 `reload()` 回滚。

## 数据接入约定
- 页面通过 `lib/api.ts` 的类型化函数访问后端（`fetchThreads` / `toggleFavorite` / `fetchDataSources` / `fetchMonitors` / `fetchApiKeys` / `fetchSettings` …）。
- `lib/api.ts` 内部统一调用 `gqlRequest()`（`lib/graphql-client.ts`），是 GraphQL 字段选择的唯一出处。
- 后端不可用时静默回退到空态，不阻塞 UI。

## Do / Don't
- Do：品牌色稀缺使用；hairline 承担层次；状态统一走 `StatusBadge`；空/载入态必备。
- Don't：多个强调色并列；纯黑 `#000`；列表滥用阴影；页面各自手写按钮/徽章样式；写死假数据当真实数据展示。
