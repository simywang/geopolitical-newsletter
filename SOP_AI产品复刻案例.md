# 看到一个好的 AI 产品，如何自己复刻做一个

**以《每日地缘政治简报》为例 — 从零到自动化 Newsletter 的完整 SOP**

---

## 前言

这份 SOP 记录了我们如何在一天内，从零开始复刻一个 AI 驱动的 newsletter 产品。

**灵感来源：** news.smol.ai — 一个每日自动抓取 AI 领域新闻、用 AI 筛选摘要、发送给订阅者的 newsletter。

**我们做的：** 把同样的逻辑应用到地缘政治领域，搭建了 CODS_ Geopolitical Briefing——每个工作日自动抓取 13 个全球新闻源，AI 筛选出最重要的 8 条，生成专业简报，发送到订阅者邮箱。

**核心洞察：** 好的 AI 产品背后，逻辑都是可拆解的。你不需要发明新技术，只需要把现有工具组合好。

---

## 第一章：拆解目标产品

### 1.1 看懂它在做什么

拿到一个你想复刻的 AI 产品，先问三个问题：

1. **输入是什么？**（数据从哪里来）
2. **AI 做了什么？**（怎么处理数据）
3. **输出是什么？**（用户得到什么）

以 news.smol.ai 为例：
- 输入：互联网上的 AI 新闻（RSS 订阅源）
- AI：筛选重要性、生成摘要
- 输出：每日邮件简报

### 1.2 拆解技术栈

不需要懂代码，但要能识别用了哪类工具：

| 功能 | 工具类型 | 我们选的工具 |
|------|----------|-------------|
| 抓取新闻 | RSS 解析库 | feedparser（Python） |
| AI 摘要 | 大语言模型 API | Claude / DeepSeek / GLM |
| 发送邮件 | Newsletter 平台 | Buttondown |
| 自动运行 | CI/CD 定时任务 | GitHub Actions |
| 落地页 | 静态网站托管 | Vercel |

### 1.3 确定你的差异化

不要做一模一样的——找一个垂直领域：
- news.smol.ai → AI 新闻
- 我们做的 → 地缘政治
- 你可以做 → 金融 / 医疗 / 法律 / 你所在行业的专业简报

---

## 第二章：搭建后端流水线

### 2.1 整体架构

```
RSS 源（13个）→ 抓取过滤 → AI 筛选摘要 → 生成 HTML → 发送邮件
```

每个工作日 UTC 06:00（阿姆斯特丹时间 08:00）自动运行。

### 2.2 数据源选择（RSS 订阅源）

我们选了 13 个覆盖全球地缘政治的新闻源：

- Reuters World News
- BBC World
- Al Jazeera English
- Foreign Policy
- The Diplomat
- War on the Rocks
- Council on Foreign Relations
- Politico World
- Financial Times World
- South China Morning Post
- Middle East Eye
- Defense News
- Breaking Defense

**选源原则：**
- 覆盖不同地区视角（西方、中东、亚太）
- 包含专业媒体（不只是大众媒体）
- 有 RSS 输出（大多数主流媒体都有）

### 2.3 AI 摘要配置

**Prompt 核心设计：**
1. 角色定义：资深地缘政治分析师
2. 任务：从所有文章中选出 8 条最重要的
3. 输出格式：JSON（标题、来源、URL、摘要、"为什么重要"）
4. 严格约束：不能编造内容，只能用提供的文章

**支持三个 AI 提供商**（灵活切换，防止单点故障）：
- Anthropic Claude（默认，质量最高）
- DeepSeek（成本低，速度快）
- 智谱 GLM（国内备用）

### 2.4 邮件发送

使用 Buttondown 平台：
- 免费计划支持到一定订阅数量
- 提供 API 接口，可程序化创建草稿和发送
- 支持 HTML 邮件，样式兼容各邮件客户端

**发送流程：**
1. 程序创建草稿（status: draft）
2. 切换状态为 about_to_send
3. Buttondown 进入发送队列，自动投递

---

## 第三章：自动化运行

### 3.1 GitHub Actions 定时任务

```yaml
on:
  schedule:
    - cron: '0 6 * * 1-5'   # 每周一到周五 UTC 06:00
  workflow_dispatch:          # 支持手动触发
```

**注意时区：**
- 夏令时（CEST, UTC+2）：cron 设 `0 6`
- 冬令时（CET, UTC+1）：cron 设 `0 7`

### 3.2 密钥管理

所有 API Key 存放在 GitHub Secrets（加密存储，不出现在代码里）：
- `ANTHROPIC_API_KEY`
- `DEEPSEEK_API_KEY`
- `BUTTONDOWN_API_KEY`

可以公开的配置放在 GitHub Variables：
- `AI_MODEL` = claude
- `SEND_MODE` = send

### 3.3 测试流程（三步走）

| 阶段 | 设置 | 效果 |
|------|------|------|
| 第一步：本地验证 | `DRY_RUN=true` | 只抓取 + AI 摘要，不发邮件 |
| 第二步：草稿检查 | `SEND_MODE=draft` | 创建草稿，在 Buttondown 里肉眼检查 |
| 第三步：正式发送 | `SEND_MODE=send` | GitHub Actions 全自动发送 |

---

## 第四章：搭建前端落地页

### 4.1 为什么需要落地页

Buttondown 自带订阅页，但不够专业。独立落地页让你能：
- 展示品牌调性
- 加入 CEO 推荐语等信任信号
- 展示邮件内容预览（提高转化率）
- 完全控制设计

### 4.2 技术选择

纯 HTML + CSS，无需框架：
- 单文件，易于维护
- 可托管在 GitHub Pages 或 Vercel
- 加载快，对搜索引擎友好

**设计原则：**
- 颜色与邮件模板保持一致（深海军蓝 `#1a1a2e` + 蓝色 `#3a5fc8`）
- Georgia 衬线字体，体现专业感
- 移动端响应式

### 4.3 关键页面元素

1. **Hero 区块**：大标题 + 一句话价值主张 + 订阅表单
2. **信任信号**：CEO 推荐语 + 照片
3. **内容预览**：Gmail 风格的邮件模拟展示
4. **话题覆盖**：标签展示覆盖领域
5. **运作说明**：3 步说明产品逻辑

### 4.4 订阅表单的正确做法

**❌ 错误做法：** 直接 form submit 到 Buttondown，用户看到 Buttondown 的报错页面，体验差。

**✅ 正确做法：** JavaScript 拦截提交 → 发给自己的服务器函数 → 服务器函数调用 Buttondown API → 返回友好提示。

三种情况分别处理：
- ✅ 成功：「请查收确认邮件」
- 📬 已订阅：「您已订阅，请查收确认邮件」
- ⚠️ 出错：「请稍后重试」

> **为什么要用服务器函数中转？** 因为 API Key 不能暴露在前端代码里，任何人都能查看网页源代码。服务器函数运行在 Vercel 的服务器上，API Key 以环境变量形式存储，用户看不到。

### 4.5 部署到 Vercel

1. 把代码推送到 GitHub
2. Vercel 连接 GitHub 仓库，自动部署
3. 每次 push 代码，Vercel 自动重新部署
4. 在 Vercel 环境变量里存放 API Key（不能放在代码里！）

---

## 第五章：常见坑与解决方案

| 问题 | 原因 | 解决 |
|------|------|------|
| AI 输出不是合法 JSON | 模型输出了 markdown 代码块包裹 | 先 strip \`\`\` 再 `json.loads()` |
| 中文字符编码错误 | Python 默认 ASCII 编码 | `ensure_ascii=True` 或设置 `PYTHONIOENCODING=utf-8` |
| GitHub push 被拒绝 | 需要 workflow 权限 | 用 Classic Token，勾选 repo + workflow 权限 |
| Vercel 部署被 Block | git commit 邮箱与 GitHub 账号不匹配 | `git config user.email` 设置正确邮箱 |
| 订阅表单 404 | Buttondown 用户名填错 | username ≠ newsletter name，在 Settings → General 确认 |
| 订阅报错「无法处理」 | 账号邮箱未验证 | 检查注册邮箱的验证邮件 |
| 图片在 Vercel 不显示 | 外部网站禁止 hotlink | 把图片文件直接上传到 GitHub 仓库 |

---

## 第六章：成本与规模

### 6.1 运行成本估算（每月）

| 项目 | 免费额度 | 超出费用 |
|------|---------|---------|
| GitHub Actions | 2000 分钟/月 | $0.008/分钟 |
| Claude API | 按量计费 | ~$0.01–0.05/天 |
| Buttondown | 免费至 100 订阅者 | $9/月起 |
| Vercel | 免费计划够用 | $20/月起 |

**结论：** 前期（< 100 订阅者）基本免费，每天 AI 费用约 ¥0.1–0.4。

### 6.2 扩展方向

- **多语言版本**：同样的流水线，换新闻源 + 改 prompt，做中文版
- **垂直行业**：医疗、金融、科技——任何需要信息聚合的领域
- **付费订阅**：Buttondown 支持付费墙，可以做 Premium 版
- **企业内部版**：用内部新闻源 + 私有部署，做公司内部简报

---

## 附录：工具清单

| 工具 | 用途 | 链接 |
|------|------|------|
| Buttondown | Newsletter 平台 | buttondown.email |
| Anthropic | Claude API | console.anthropic.com |
| DeepSeek | 备用 AI API | platform.deepseek.com |
| GitHub | 代码托管 + Actions | github.com |
| Vercel | 前端托管 | vercel.com |
| feedparser | RSS 解析（Python 库） | pypi.org/project/feedparser |

---

## 总结：复刻一个 AI 产品的通用框架

```
1. 拆解   →  搞清楚输入、AI处理、输出三个环节
2. 选源   →  找到你领域的数据来源（RSS / API / 爬虫）
3. 写Prompt →  定义 AI 的角色、任务、输出格式
4. 连接平台 →  用现成 SaaS 工具（不要自己造轮子）
5. 自动化  →  GitHub Actions 定时跑，全程无人值守
6. 做门面  →  一个落地页让产品看起来像产品
7. 测试   →  先 dry run，再草稿，再正式发送
```

> **最重要的一句话：** 你不需要是工程师，你需要的是把对的工具连接在一起的能力，以及不怕报错的勇气。
