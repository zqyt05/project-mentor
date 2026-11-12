# ProjectMentor — PBL 项目制 AI 实战导师

**输入一个学习方向，得到一个能真正做完的实战项目 —— 不是课程大纲，而是带 DDL 的任务、随时在线的导师，和一次真正检验理解程度的复盘。**

[![CI](https://github.com/zqyt05/project-mentor/actions/workflows/ci.yml/badge.svg)](https://github.com/zqyt05/project-mentor/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.143-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-0052FF.svg)](LICENSE)

---

## 目录

- [解决什么问题](#解决什么问题)
- [核心功能](#核心功能)
- [界面预览](#界面预览)
- [设计风格](#设计风格电光蓝--双字体)
- [技术栈](#技术栈)
- [快速启动](#快速启动)
- [分享给他人试用](#分享给他人试用)
- [项目结构](#项目结构)
- [开发与测试](#开发与测试)
- [几个关键的工程决策](#几个关键的工程决策)
- [已知限制](#已知限制)
- [License](#license)

---

## 解决什么问题

在校学生和转行者学技术时，普遍卡在同一个地方：**看完了教程，但做不出东西**。

- 课程给的是**知识地图**（先学 A，再学 B），不是**交付物**（做出一件东西）
- 学完不知道自己会不会，因为没有检验环节
- 遇到问题没人可问，或者只能问通用 AI，得不到结合当前任务的回答

ProjectMentor 想复刻的是**企业里导师带新人的方式**：直接给一个真实项目做，
做的过程中答疑，做完讲一遍给导师听，导师指出你的理解偏差。

产品上有三个刻意的设计：

| 设计 | 理由 |
| --- | --- |
| **只输出项目，不输出课程大纲** | 项目自带完成标准，做完就是学会 |
| **每个任务带 DDL 与交付标准** | 没有截止日的学习计划等于没有计划 |
| **用费曼学习法收尾** | 能讲清楚才是真学会，讲不清楚说明没懂 |

---

## 核心功能

### 1. 双路径项目智能匹配

输入学习方向 + 难度，系统先判断领域类型，再走两条路径之一：

| 路径 | 触发条件 | 做法 |
| --- | --- | --- |
| **A · GitHub 开源项目** | 技术开发类方向 | 检索优质仓库 → 逐条评估对学习者的适配度 → 提取 README 摘要 |
| **B · AI 定制项目** | 通用能力类方向 | 按方向与难度生成「小而实」的实战项目 |

**关键技术点**：中文方向（如「React 前端入门」）直接拿去搜 GitHub 命中率极低。
所以领域判断这一步会**同时产出英文技术关键词和语言限定** —— 一次调用解决三件事。

优质开源项目不足 3 个时**不整体降级**，而是用 AI 定制项目补齐差额 ——
即使只找到 1–2 个高度相关的仓库，也仍然呈现给用户。

### 2. 项目拆解 + DDL 任务管理

选中项目后，AI 把项目拆成 **4–6 个阶段**、共 13–14 个任务，每个任务包含：

- 具体做什么（可执行的描述）
- 需掌握的知识点
- **可判断真假的交付标准**（不是「理解 XX」，而是「四列齐全无空行，差额为 0」）
- 建议天数与截止日期（DDL 按顺序累加）

任务**推荐按顺序推进，但不强制** —— 任意任务都能直接开始。
自主学习者可能已经掌握某部分、或想先看后面的任务再回头补，硬性门禁会把人卡住。

### 3. 双窗口隔离式场景化答疑

左侧主任务窗口 + 右侧独立答疑窗口，**分栏比例可拖拽调整**（默认 70/30，双击复位）。

关键设计：**每个任务的对话完全隔离**。
右上角的答疑上下文自动绑定当前任务，切换任务时加载该任务独立的对话历史，
且**永远不会冲掉**左侧的任务记录。

历史对话按最近 12 条截断 —— 再多的上下文收益有限，反而会稀释当前任务的焦点。

### 4. 费曼学习法复盘

全部任务完成后进入复盘环节，用「结构化技术总结 / 项目复盘博客 / 面试口述提纲」
三种形式之一，让学习者**用自己的话讲一遍**，AI 从四个维度处理：

| 维度 | 做什么 |
| --- | --- |
| 理解纠错 | 找出说错的地方，给出正确表述 |
| 遗漏补全 | 补充没提到但重要的知识点 |
| 结构优化 | 把零散的表述整理成有逻辑的文档 |
| 深化建议 | 指出可以继续深挖的方向 |

输出一份**可展示的复盘文档**，支持一键复制。

### 5. 历史项目与进度管理

所有项目持久化在本地，支持查看进度、继续学习、删除。
顶栏实时显示当前项目的完成度。

---

## 界面预览

> 截图位于 [`docs/screenshots/`](docs/screenshots/)

| 首页：极简搜索 | 项目总览 |
| --- | --- |
| ![首页](docs/screenshots/01-首页-学习方向输入.png) | ![总览](docs/screenshots/03-项目总览.png) |

| 任务列表（含交付标准与 DDL） | 费曼复盘 |
| --- | --- |
| ![任务列表](docs/screenshots/05-任务列表.png) | ![复盘](docs/screenshots/06-费曼复盘.png) |

---

## 设计风格：电光蓝 + 双字体

界面刻意避开「白底灰字安全牌」，用一套有识别度的现代设计系统：

| 要素 | 做法 |
| --- | --- |
| **标志性渐变** | `#0052FF → #4D7CFF`，出现在主按钮、标题强调词、进度条、菜单选中态、列表项目符号 |
| **反色对比区块** | 项目总览的统计条用深石板底 + 3% 点阵纹理，滚动时形成视觉节奏 |
| **双字体排版** | Calistoga（展示）+ Inter（UI/正文）+ JetBrains Mono（标签/数据） |
| **动画深度** | 装饰环 72s 旋转、浮动几何体 4–5s、脉冲指示器 2s、按钮悬停上浮 |
| **纹理** | 径向辉光（blur 150px）、Hero 径向渐变叠加、分层柔和阴影 |

**无障碍**：焦点环匹配强调色；反色区块对比度达标；全部动画尊重
`prefers-reduced-motion`；触摸目标 ≥ 44px。

**中文排版细节**：Calistoga 没有 CJK 字形，中文标题回退到 `Noto Serif SC`，
保证中英混排的调性一致 —— 否则中文会掉到系统默认字体，双字体的身份感就丢了。

---

## 技术栈

| 层级 | 技术选型 | 说明 |
| --- | --- | --- |
| 前端 | React 18 + TypeScript 5.7 + Vite 5 | 主流前端栈，TS 严格模式 |
| 前端 UI | Ant Design 5 | Layout 天然支持双窗口分栏 |
| 前端状态 | Zustand 5 | 轻量全局状态，承载双窗口联动 |
| 前端路由 | react-router-dom 6 | 首页独立全屏，其余页面走双窗口外壳 |
| 内容渲染 | react-markdown + remark-gfm + highlight.js | 渲染答疑与复盘文档，支持表格与代码高亮 |
| 后端 | Python 3.11 + FastAPI 0.143 | 全异步链路，自动生成 OpenAPI 文档 |
| ORM | SQLAlchemy 2.1（2.0 声明式风格） | SQLite，WAL 模式 |
| AI 编排 | LangChain 1.4 + langchain-openai 1.7 | 对接 DeepSeek 的 OpenAI 兼容接口 |
| AI 模型 | DeepSeek `deepseek-flash` | 推理模型，1M 上下文 |
| 第三方集成 | GitHub REST API v3 | 技术类项目检索与 README 校验 |
| 静态检查 | flake8（F 类语义检查）+ ESLint 8 + tsc | 见 [CI 配置](.github/workflows/ci.yml) |
| 容器化 | Docker 多阶段构建 + Compose | 前后端同源，镜像 451 MB |
| 环境管理 | pydantic-settings | 敏感信息全部走环境变量，禁止硬编码 |

---

## 快速启动

### 方式一：本地开发（改代码时用）

```bash
# 准备配置
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入 DEEPSEEK_API_KEY（必填）与 GITHUB_TOKEN（可选）

# 终端 1：后端（首次运行自动建表）
./scripts/start-backend.sh

# 终端 2：前端
./scripts/start-frontend.sh
```

打开 <http://127.0.0.1:5173>

依赖环境：Python 3.11、Node ≥ 22.13、pnpm。

### 方式二：Docker（一键起，推荐给别人演示）

```bash
docker compose up -d --build     # 构建并后台启动
docker compose logs -f           # 看日志
docker compose down              # 停止（保留数据卷）
```

打开 <http://127.0.0.1:8000>

容器特性：

- 前后端**同源**（后端托管前端产物），零 CORS 配置
- SQLite 落在命名卷 `projectmentor-data`，容器重建不丢数据
- **非 root 运行**（uid 10001）
- 镜像内**不含 `.env` 与数据库**（密钥通过环境变量注入，避免烘进镜像层）
- 内置健康检查

> macOS 若提示 `docker: command not found`，把 CLI 加进 PATH：
> `echo 'export PATH="$HOME/.docker/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc`

---

## 分享给他人试用

详见 **[演示部署指南](docs/演示部署指南.md)**。一句话版本：

```bash
cd frontend && pnpm build                           # 1. 构建前端
# 2. 在 backend/.env 设置 DEMO_PASSWORD=你的口令
DEMO_PASSWORD='你的口令' ./scripts/serve-demo.sh      # 3. 生产模式启动
./scripts/share-tunnel.sh                            # 4. 另开终端建隧道
```

三件必须知道的事：

1. **你的电脑就是服务器** —— 关机/休眠/关闭隧道终端都会让链接失效
2. **注意 AI 费用** —— 你的 Key 为所有访客付费。DeepSeek **不提供消费上限**，
   建议「只充值小额」（余额即硬上限），并设置应用层每日上限
   `DAILY_LLM_CALL_LIMIT=80`（0 = 不限制，本地默认）
3. **不要用 Vercel / Netlify / Render 免费层** —— `POST /api/project/start`
   实测约 51 秒，会撞上这些平台的函数超时；Cloudflare 隧道（100s）才能跑通

演示模式内置两道防护：

- **口令门禁**：HMAC 签名的 Cookie，访客身份无法伪造
- **访客数据隔离**：每个访客只能看到自己的项目，越权返回 404 而非 403（不泄露存在性）

---

## 项目结构

```
ProjectMentor/
├── backend/
│   ├── app/
│   │   ├── api/            # 路由层：只做参数校验与响应封装
│   │   │   ├── auth.py         # 演示门禁（口令登录、访客身份）
│   │   │   ├── project.py      # 项目匹配、详情、删除
│   │   │   ├── task.py         # 阶段/任务、状态流转、进度
│   │   │   ├── chat.py         # 答疑（按任务隔离的会话）
│   │   │   └── review.py       # 费曼复盘
│   │   ├── services/       # 业务逻辑层：可脱离 FastAPI 单测
│   │   │   ├── project_service.py    # 匹配 / 拆解 / 进度计算
│   │   │   ├── chat_service.py       # 上下文拼装与对话
│   │   │   ├── review_service.py     # 复盘生成
│   │   │   ├── llm_service.py        # DeepSeek 封装（含配额收口点）
│   │   │   ├── github_service.py     # GitHub 检索
│   │   │   ├── auth_service.py       # 口令与签名 Cookie
│   │   │   └── usage_service.py      # 每日 AI 调用配额
│   │   ├── models/         # SQLAlchemy 模型（6 张表）
│   │   ├── schemas/        # Pydantic 请求/响应
│   │   ├── prompts/        # 6 个 Prompt 模板（当代码资产管理）
│   │   └── utils/response.py # 统一 {code,message,data} 与全局异常处理
│   ├── tests/              # 111 个离线单测
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/            # axios 封装（统一解包、401 拦截、FormData）
│       ├── components/     # ProjectCard / TaskCard / StageTimeline / Reveal …
│       ├── layout/         # MainLayout（可拖拽分栏）/ TopBar / SideMenu / ChatPanel
│       ├── pages/          # Home / Login / Match / Overview / Tasks / Review / History
│       ├── store/          # Zustand（应用状态 + 鉴权状态）
│       └── index.css       # 设计系统（CSS 变量 + 工具类 + AntD 覆写）
├── scripts/                # 启动、演示、隧道、Key 检查
├── docs/                   # 部署指南、架构说明、截图
├── Dockerfile / docker-compose.yml
└── .github/workflows/ci.yml
```

**规模**：后端 3534 行 / 33 文件，测试 1276 行，前端 TS 3677 行 / 30 文件，
CSS 2468 行，**19 个 REST 接口**，6 张表，**111 个单测**。

---

## 开发与测试

```bash
# 后端：静态检查 + 单测
cd backend
./.venv/bin/python -m flake8 app/ tests/
./.venv/bin/python -m pytest

# 前端：类型检查 + Lint + 构建
cd frontend
./node_modules/.bin/tsc --noEmit
./node_modules/.bin/eslint . --ext ts,tsx
./node_modules/.bin/vite build
```

**测试原则：全部离线** —— 任何用例都不触发 LLM 或 GitHub 请求，
因此在没有 API Key 的环境（如 CI）下也能全部通过。

覆盖范围刻意选在「确定性逻辑」上：DDL 累加、进度边界、JSON 容错解析、
响应契约、字段清洗规则、路由补齐策略、访客隔离、每日配额。
**不测试 AI 输出质量** —— 那属于端到端验证，用 mock 去测只会自欺欺人。

CI（GitHub Actions）在每次 push/PR 时执行：flake8 静态检查 → 导入检查 → 单测；
前端 typecheck → lint → build。

---

## 几个关键的工程决策

这一节记录「为什么这么做」，比「做了什么」更有参考价值。

### 推理模型的 token 预算

`deepseek-flash` 的 `reasoning_content`（思考过程）与 `content`（正文）
**共享同一个 token 预算**。给 50 tokens 时正文直接返回空字符串。
所以默认 8192，复盘生成用 16384。

### Prompt 用 `string.Template` 而不是 `str.format`

模板里要写 JSON 示例，`str.format` 会把 `{}` 当占位符，必须全部转义，
可读性极差。`$var` 形式没有这个问题。

### JSON 输出五重容错

不信任模型输出，`extract_json()` 依次尝试：直接解析 → 剥离代码块 →
截取最外层括号 → 修复尾逗号 → 转义裸控制字符。

### 用数据库约束保证业务不变量

「双窗口隔离」不是靠前端约束，而是靠
`UniqueConstraint(project_id, scope, task_id)` —— 数据层保证。

### 归属校验收口在一个函数

所有项目读取都经过 `project_service.get_project`，因此在**这一个函数**里校验
就能覆盖全部 16 个项目级/任务级接口，而不是逐个补检查然后漏掉一个。
漏一个就是一个越权缺口，而缺口不会自己暴露。

越权返回 **404 而非 403**：403 等于确认「该 id 存在但你没权限」，会泄露存在性。

### 测试隔离必须系统性

`Settings` 会读取 `backend/.env`，本地配置会漏进测试导致莫名失败。
一开始只把个别开关置空，新增字段时又漏了。
最终改为**逐字段重置为默认值**，新增字段自动覆盖。

### 用 flake8 代替手写检查器

「函数体引用了签名里没声明的变量」这类缺陷只在接口被调用时暴露为 500，
单测不覆盖该路径就发现不了。手写 AST 检查器只能覆盖当时想到的变量名；
`flake8` 的 `F821 undefined name` 覆盖任意未定义名字。
（选 flake8 而非 pyflakes，是因为代码里有 `# noqa: F401` 标注刻意的导入副作用。）

### 镜像里不放密钥与数据

`.dockerignore` 显式排除 `.env` 与 `*.db`。镜像层一旦构建就无法撤销，
任何拿到镜像的人都能读出里面的文件 —— 密钥烘进去等于泄露。

---

## 已知限制

| 限制 | 说明 |
| --- | --- |
| 单用户本地工具 | 无账号体系。演示模式用共享口令 + 访客隔离，不是完整多租户 |
| 无数据库迁移 | 使用 `create_all`，**不会**给已有表加列。模型变更后需删库重建（有真实数据后应引入 Alembic） |
| SQLite | 适合单用户/小范围试用。并发写入已开 WAL + busy_timeout |
| 长请求同步返回 | 项目匹配 13–43s、任务拆解约 51s、复盘约 36s。没有流式输出，靠缓动进度条缓解等待焦虑 |
| 前端包 1.5 MB（gzip 465 KB） | AntD 全量引入，未做按需加载与代码分割 |
| 无前端单测 | 目前靠浏览器端到端验证 + TypeScript 类型系统兜底 |

---

## License

[MIT](LICENSE) © 2026 zqyt05
