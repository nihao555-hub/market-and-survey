# DESIGN.md — 选品 Agent 前端设计系统

> 基于 Linear 设计语言（VoltAgent/awesome-design-md），适配为**亮色产品工具**主题。
> 用途：跨境选品调研 Agent（侧边栏 + 输入框 + 流式思考 + 报告渲染），属产品 UI 非营销页。

## 设计哲学
- 软件工艺感：克制、精确、安静的高级感。
- 单一强调色（Linear lavender #5e6ad2），仅用于：发送按钮、焦点环、流式指示、链接强调。绝不装饰性滥用。
- 用 surface 层级 + 1px hairline 边框承担层次，几乎不用阴影。
- 显示字体负字距（headline -0.6px），正文 -0.05px。

## 配色（亮色主题）
| 语义 | hex | 用途 |
|---|---|---|
| accent | #5e6ad2 | 主按钮 / 焦点环 / 流式 / 链接 |
| accent-hover | #4f5ac0 | hover |
| canvas | #ffffff | 页面背景 |
| surface-1 | #fafbfc | 侧边栏 / 卡片 |
| surface-2 | #f4f5f7 | 选中态 / hover 卡片 |
| hairline | #e8eaed | 1px 边框 / 分隔线 |
| hairline-strong | #d8dbe0 | 焦点边框 |
| ink | #1a1d21 | 标题 / 强调正文 |
| ink-muted | #4b5563 | 正文 |
| ink-subtle | #8a8f98 | 次要 / 占位 / 元信息 |
| success | #27a644 | 工具完成态 |
| danger | #dc2626 | 错误态 |

## 字体
- Inter（Linear 官方推荐替代）：400 正文 / 500 按钮 / 600 标题 / 700 大标题。
- 等宽：JetBrains Mono（工具名标签 / JSON 输出 / ASIN）。

## 圆角
- 6px 小 chip/badge · 8px 按钮+输入框 · 12px 卡片 · pill 标签切换/状态 · full 头像。

## 间距
- 4px 基准：xs 8 · sm 12 · md 16 · lg 24 · xl 32。

## 组件
- 主按钮：bg accent，text white，8px radius，padding 8/14。
- 次按钮：bg surface-1，1px hairline，ink。
- 输入框：bg white，1px hairline，焦点 2px accent 环 @50%。
- 卡片：bg surface-1，1px hairline，12px radius，无阴影。
- 工具步骤卡：进行中 lavender + shimmer；完成 success √；出错 danger。

## Do / Don't
- Do：accent 稀缺使用；hairline 承担层次；负字距显示字体。
- Don't：AI 紫色辉光；纯黑 #000；多个强调色；重投影；pill 圆角主 CTA。
