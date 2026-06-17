# 工具库：前端 / SaaS 框架（全环节共用的统一前端）

> 关键澄清：展示层 ≠ 整个产品前端。
> - Metabase 是"内嵌数据看板"，负责图表/报表展示，嵌进产品里用。
> - 真正的"统一前端"是 SaaS 外壳：登录、多租户、权限(RBAC)、计费、各环节功能页。
> 这是企业级 SaaS 的骨架，所有环节(选品/Listing/客服/...)共用这一套壳。
> star 与许可证已于 2026-05 核实。

---

## 一、架构定位

```
┌──────────────── 统一前端 SaaS 外壳（一套，全环节共用）────────────────┐
│  登录/注册 · 多租户(Org) · RBAC权限 · 订阅计费(Stripe) · i18n · 主题   │
│                                                                       │
│  ┌─选品工作台─┐ ┌─Listing工作台─┐ ┌─客服台─┐ ┌─数据看板─┐ ...        │
│  │ 各环节功能页 │ │ 各环节功能页  │ │       │ │(内嵌Metabase)│         │
│  └────────────┘ └──────────────┘ └────────┘ └───────────┘            │
└───────────────────────────┬───────────────────────────────────────────┘
                            │ REST/GraphQL
                   后端 API（业务逻辑） + 各环节微服务
```

---

## 二、统一前端骨架候选（SaaS Boilerplate）—— 核心选型

| 项目 | 技术栈 | 许可证 | star | 自带能力 | 适配度 |
|---|---|---|---|---|---|
| `boxyhq/saas-starter-kit` | Next.js+Prisma | ✅Apache-2.0 | 4.8k | **企业级**：多租户、SAML SSO、RBAC、审计日志、Webhook、团队 | ★★★★★ B2B首选 |
| `ixartz/SaaS-Boilerplate` | Next.js+Tailwind+Shadcn | ✅MIT | 7.1k | 多租户、RBAC、i18n、Auth、落地页、计费 | ★★★★★ 现代轻量 |
| `nextjs/saas-starter` | Next.js官方 | ✅MIT | 15.8k | Stripe订阅、登录、仪表盘(官方出品，干净) | ★★★★ 基础扎实 |
| `calcom/cal.com` | Next.js | ✅MIT(部分AGPL) | 44.8k | 超成熟企业级代码范本(可借鉴架构) | ★★★ 偏重,参考 |

> 推荐：**boxyhq/saas-starter-kit（B2B 企业级、Apache-2.0 商用友好）** 或
> **ixartz/SaaS-Boilerplate（更现代 Shadcn UI、MIT）** 二选一作起点。
> 二者都自带"多租户+权限+计费"——这正是 SaaS 最费时且我们最不该自研的部分。

---

## 三、后台管理 / 仪表盘框架（功能页面的 UI 底座）

| 项目 | 技术栈 | 许可证 | star | 特点 |
|---|---|---|---|---|
| `ant-design/ant-design-pro` | React+AntD | ✅MIT | 38.3k | 中后台标杆，组件最全，适合数据密集的 B 端(选品表格/筛选) |
| `refinedev/refine` | React元框架 | ✅MIT | 34.8k | CRUD 中后台元框架，快速搭增删改查后台，省大量样板 |
| `marmelab/react-admin` | React | ✅MIT | 26.8k | 成熟 admin 框架，数据驱动，生态大 |
| `tabler/tabler` | HTML/Bootstrap | ✅MIT | 41.1k | 漂亮的通用后台 UI 套件，框架无关 |
| `d3george/slash-admin` | React19+Vite+TS | ✅(核实) | 新锐 | 现代 React admin 模板，快 |

> 选型建议：
> - 若用 boxyhq/ixartz(Next.js) 当外壳 → 功能页直接用 Shadcn UI + 按需引 AntD Pro 的表格能力。
> - 数据密集型 B 端（选品大表、批量操作）→ AntD Pro 体验最好。
> - 要快速生成大量 CRUD 后台（多环节管理页）→ refine。

---

## 四、数据看板（嵌入产品里展示图表）

| 项目 | 许可证 | star | 角色 |
|---|---|---|---|
| `metabase/metabase` | ⚠️AGPL/商业版 | 46k | 拖拽建图，可嵌入(embedding)；非技术卖家自助分析 |
| `apache/superset` | ✅Apache-2.0 | 71k | 更强 BI，40+ 图表，许可证更友好 |

> 看板是"嵌入组件"，通过 iframe/embedding SDK 放进上面的 SaaS 外壳里，不是独立前端。
> Superset 许可证(Apache)比 Metabase(AGPL) 更适合深度集成。

---

## 五、我们自研什么（前端侧，极少）
- ✅ 直接用脚手架：登录/多租户/权限/计费/i18n —— **零自研**
- ✅ 直接用 UI 框架：表格/表单/图表组件 —— **零自研**
- 🟡 自研：各环节的**业务功能页面**(选品工作台、Listing 编辑器等)的页面编排和与后端 API 的对接。但这是在现成组件上拼页面，不是造框架。

---

## 六、推荐组合（最终建议）
```
外壳：boxyhq/saas-starter-kit (Apache-2.0, 多租户+RBAC+SSO+计费)
  + UI：Shadcn UI / Ant Design Pro(数据密集页)
  + 看板：Superset(Apache, 嵌入式) 或 Metabase(隔离部署)
  + CRUD后台(可选)：refine
全部 MIT/Apache，商用无传染风险（Metabase 走嵌入/隔离）。
```

---

## 七、许可证红线
- ✅ 商用友好：boxyhq(Apache)、ixartz(MIT)、nextjs/saas-starter(MIT)、antd-pro(MIT)、refine(MIT)、react-admin(MIT)、tabler(MIT)、superset(Apache)
- ⚠️ 注意：metabase(AGPL，走官方 embedding 或独立部署规避)、cal.com(部分 AGPL，仅参考架构不直接 fork)

---

## 待办
- [ ] 在 boxyhq vs ixartz 之间二选一，跑起来看多租户/计费是否满足
- [ ] 确认计费方式(Stripe 海外 / 国内支付)，影响脚手架选择
- [ ] 定 UI 库：纯 Shadcn 还是引入 AntD Pro
- [ ] 数据看板定 Superset(嵌入) 还是 Metabase(隔离)
