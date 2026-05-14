# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Prime Directives (Karpathy's 4 Rules)

### 1. Think Before Coding — 先想再写
**Don't assume. Don't hide confusion. Surface tradeoffs.**
- 先陈述假设。不确定就问。
- 有多个解释时，列出来让用户选。
- 有更简单的方案时，说出来。
- 如果不够明确，停下来。命名困惑之处。
- 不确认的不要写。先讨论清楚再动手。

### 2. Simplicity First — 简单优先
**Minimum code that solves the problem. Nothing speculative.**
- 别加没被要求的功能
- 别为只用一次的代码建抽象
- 别加没被要求的"灵活性"或"可配置性"
- 别处理不可能发生的错误场景
- 如果 200 行能砍到 50 行，重写
- 三个相似行 > 一个过早的抽象

### 3. Surgical Changes — 手术式修改
**Touch only what you must. Clean up only your own mess.**
- 别"优化"旁边没让你动的代码、注释、格式
- 别重构没坏的东西
- 匹配现有风格，即使你不喜欢
- 发现死代码？提一句——别删
- 测试：每个改动行都能追溯到用户的具体要求

### 4. Goal-Driven Execution — 目标驱动的执行
**Define success criteria. Loop until verified.**
- "加验证" → "写测试覆盖无效输入，让它们通过"
- "修 bug" → "写测试重现它，然后让测试通过"
- "重构 X" → "确保重构前后测试都通过"
- LLM 最强的是循环迭代直到满足目标
- 给它成功标准，让它跑，别告诉它怎么做

## User Profile
- 考研生，目标 400 分（政70/英80/数一125/408 125）
- 学 AI 方向，目标浙大/南大/中科院等 985
- 技术栈：Python/FastAPI、JavaScript/Vue/React、PostgreSQL（Go 不懂，CGO/编译器不熟）
- 开发环境：WSL2 Ubuntu，项目放 ~/ 下（不用 /mnt/d/，跨文件系统极慢）
- 偏好：简洁代码，不写冗余注释，不过度设计
- 学习：借这个项目学计算机，每次改动需要解释清楚，边做边学

## Global Rules
- 所有项目优先用 WSL 原生路径 (~/...)，不用 /mnt/d/
- 修改代码后只做最少验证，不全量跑测试
- 需要长期记住的信息写入 memory
- 每日工作记录写入 /mnt/d/life_management/2026/

### 迁移/开发工作流
- **每次迁移板块前**：完整解释要做什么、为什么这样做、涉及哪些文件和概念，等用户确认再做
- **解释方式**：用类比（已知解释未知），不假设用户懂 Go/CGO/编译器/协议细节
- **做完后**：用 2-3 句话总结实际做了什么、学到了什么
- **git 同步**：不在每次修改后手动 push。每晚 11 点 cron 自动提交并 push 当天所有修改到 GitHub
- **每日收尾**：在 `/mnt/d/life_management/2026/` 当天日志末尾追加今日工作内容
- **通过对话持续观察用户的知识水平**，更新 `[[user-cs-knowledge]]` memory

---

## Project: SiYuan Note (思源笔记)

### Build & Run

```bash
# Kernel (Go, needs CGO + FTS5)
cd kernel
CGO_ENABLED=1 go build -tags fts5 -o siyuan-kernel .

# Frontend (TypeScript, webpack multi-target)
cd app
pnpm install
npx webpack --mode development              # Electron renderer → stage/build/app/
npx webpack --mode development --config webpack.desktop.js  # Browser → stage/build/desktop/
npx webpack --mode development --config webpack.mobile.js   # Mobile → stage/build/mobile/
pnpm run build                               # All targets, production

# Run kernel (dev mode — kernel auto-serves frontend from app/stage/build/)
siyuan-kernel --mode=dev --port=6806 --workspace=<workspace_dir> --wd=<path/to/app>

# Run Electron desktop (after kernel is running)
cd app
NODE_ENV=development npx electron ./electron/main.js
```

Kernel API endpoint: `http://127.0.0.1:6806`. All endpoints are POST with JSON body. No-auth endpoints: `/api/system/version`, `/api/system/bootProgress`.

### Architecture

```
┌─────────────────────────────────────────────────┐
│  app/ (Electron + TypeScript + Webpack)         │
│  ├── src/          TS source, Protyle editor    │
│  ├── electron/     Electron main process        │
│  ├── appearance/   Themes, icons, i18n, fonts   │
│  └── stage/build/  Webpack output (3 targets)   │
│       ├── app/       Electron renderer          │
│       ├── desktop/   Browser (BROWSER flag)     │
│       └── mobile/    Mobile webview             │
└──────────────────────┬──────────────────────────┘
                       │ HTTP + WebSocket (127.0.0.1:6806)
┌──────────────────────┴──────────────────────────┐
│  kernel/ (Go, Gin framework)                    │
│  ├── main.go        Entry, boot sequence        │
│  ├── server/        HTTP server + WebSocket     │
│  ├── api/           Route handlers (gin)        │
│  ├── model/         Core business logic (60+ files) │
│  ├── sql/           SQLite with FTS5 fulltext   │
│  ├── filesys/       Virtual file tree (.sy JSON) │
│  ├── cache/         In-memory cache             │
│  ├── bazaar/        Community plugin/theme mgmt │
│  ├── search/        Full-text search engine     │
│  ├── conf/          Config struct definitions   │
│  ├── util/          Globals (WorkspaceDir,      │
│  │                  ServerPort) + shared helpers │
│  ├── av/            Attribute View system       │
│  ├── task/          Async task queue            │
│  └── job/           Cron scheduler              │
└─────────────────────────────────────────────────┘
```

### Key Patterns

- **Auth**: Most API endpoints go through `model.CheckAuth` → `model.CheckAdminRole` → handler chain. See `kernel/api/router.go`.
- **Database**: SQLite via `github.com/88250/go-sqlite3` (custom fork with FTS5). DB path: `WorkspaceDir/temp/siyuan.db`. Schema auto-migrated in `sql.InitDatabase()`.
- **Workspace**: Data directory layout — `conf/`, `data/` (assets, templates, widgets, plugins, emojis, public), `temp/`, `repo/`, `history/`.
- **Frontend**: Webpack with `ifdef-loader` to toggle `BROWSER` / `MOBILE` flags at compile time. Desktop target has `BROWSER: true` for web APIs; Electron target uses `BROWSER: false` for Node.js APIs.
- **Kernel → Frontend**: Kernel serves `/stage/build/{desktop,app,mobile}/` from the working directory's `stage/build/`. Request routing picks target based on user config + device.
- **WebSocket**: Used for real-time push (reload UI, broadcast messages). Managed via `github.com/olahol/melody`.
- **Testing**: Only one test file: `kernel/model/asset_content_test.go`. Run with `go test ./...` in kernel/.

### Important Dependencies

- `github.com/88250/lute` — Markdown parser/Protyle engine (core rendering)
- `github.com/siyuan-note/dejavu` — Data sync/repo
- `github.com/siyuan-note/riff` — File storage format
- `github.com/siyuan-note/filelock` — Cross-platform file locking
- `github.com/88250/pdfcpu` — PDF export (custom fork)
