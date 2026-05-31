<p align="center">
  <img src="https://img.shields.io/badge/Version-v1.0.0-blue?style=flat-square" alt="Version" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-green?style=flat-square" alt="Python" />
  <img src="https://img.shields.io/badge/License-MIT-orange?style=flat-square" alt="License" />
  <img src="https://img.shields.io/badge/PRs-Welcome-brightgreen?style=flat-square" alt="PRs Welcome" />
</p>

<p align="center">
  <a href="#zh-cn">简体中文</a> &nbsp;|&nbsp;
  <a href="#zh-tw">繁體中文</a> &nbsp;|&nbsp;
  <a href="#english">English</a>
</p>

---

<h1 id="zh-cn">🚀 TaskPilot-CLI</h1>

<p align="center">
  <strong>轻量级终端 AI 任务智能编排与执行引擎</strong><br/>
  <em>用 YAML 定义流水线，让 AI 任务像飞行航线一样精准执行</em>
</p>

## 📖 项目介绍

TaskPilot-CLI 是一款面向开发者的轻量级终端工具，让你通过 YAML 文件定义复杂的多步骤 AI 任务流水线。它会自动解析任务间的依赖关系，并行执行独立任务，并在失败时智能重试——一切都在终端中优雅呈现。

> 💡 **灵感来源**：设计理念借鉴了 AI Agent 编排框架（如 OpenAI Symphony），但聚焦于轻量化终端体验。无需复杂的项目结构，一个 YAML 文件即可起飞。

## ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 📝 **YAML 流水线定义** | 零代码编排，用 YAML 描述你的 AI 任务流程 |
| 🕸️ **DAG 依赖解析** | 自动分析步骤依赖，构建有向无环图，并行执行独立任务 |
| 🤖 **多 LLM 后端** | 支持 OpenAI、Anthropic、本地模型等多种大语言模型 |
| 🧩 **7 种步骤类型** | `llm_call` / `http_request` / `shell_command` / `script` / `condition` / `transform` / `parallel` |
| 🔄 **失败重试与超时控制** | 自动重试失败的步骤，灵活设置超时时间 |
| 🔀 **条件执行** | 根据上游结果动态决定是否执行下游步骤 |
| 📊 **Rich TUI 仪表盘** | 终端内实时可视化执行进度，优雅且直观 |
| 📜 **执行历史记录** | 自动保存每次执行记录，支持 JSON 结果导出 |
| 🌍 **环境变量与模板变量** | 灵活的环境变量注入与 `{{variable}}` 模板变量系统 |

## 🛠️ 技术栈

- **Python 3.10+** — 核心运行时
- **Rich** — 终端 UI 与富文本渲染
- **PyYAML** — YAML 解析引擎
- **httpx**（可选）— HTTP 请求支持

## ⚡ 快速开始

### 📦 安装

```bash
# 从 GitHub 直接安装
pip install git+https://github.com/gitstq/TaskPilot-CLI.git

# 或者克隆后本地安装
git clone https://github.com/gitstq/TaskPilot-CLI.git
cd TaskPilot-CLI
pip install -e .
```

### 🎯 基本使用

```bash
# 初始化示例流水线
taskpilot init

# 执行流水线
taskpilot run pipeline.yaml

# 验证流水线语法
taskpilot validate pipeline.yaml

# 查看流水线详情
taskpilot show pipeline.yaml

# 查看执行历史
taskpilot history
```

### 📋 YAML 流水线示例

```yaml
name: my-pipeline
description: My first pipeline
llm:
  provider: openai
  model: gpt-4o-mini
variables:
  url: "https://api.example.com"
steps:
  - name: fetch
    type: http_request
    config:
      url: "{{url}}"
      method: GET

  - name: analyze
    type: llm_call
    depends_on: [fetch]
    config:
      prompt: "Analyze: {{fetch}}"

  - name: report
    type: transform
    depends_on: [analyze]
    config:
      transform: template
      template: "Result: {{analyze}}"
```

## 🔧 环境变量配置

| 变量名 | 说明 |
|--------|------|
| `TASKPILOT_OPENAI_API_KEY` | OpenAI API 密钥 |
| `TASKPILOT_LLM_API_KEY` | 通用 LLM API 密钥（兼容多种后端） |
| `TASKPILOT_OPENAI_API_BASE` | 自定义 API 端点（适用于代理或本地部署） |

## 🧠 设计思路

TaskPilot-CLI 的核心哲学是 **「声明式编排，自动化执行」**：

1. **YAML 即代码** — 用人类可读的 YAML 描述任务流程，无需编写脚本
2. **依赖自动解析** — 通过 DAG 算法自动分析 `depends_on` 关系，最大化并行度
3. **结果自动传递** — 上游步骤的输出自动注入到下游步骤的 `{{step_name}}` 模板中
4. **优雅降级** — 失败不意味着崩溃，重试机制与条件执行让流水线具备弹性
5. **终端原生** — 拒绝繁重的 Web UI，一切在终端中完成，符合开发者直觉

## 🤝 参与贡献

我们欢迎任何形式的贡献！无论是提交 Bug、改进文档还是贡献新功能：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 发起 Pull Request

## 📄 开源协议

本项目基于 [MIT 协议](https://opensource.org/licenses/MIT) 开源，详见 [LICENSE](LICENSE) 文件。

---

<h1 id="zh-tw">🚀 TaskPilot-CLI</h1>

<p align="center">
  <strong>輕量級終端 AI 任務智慧編排與執行引擎</strong><br/>
  <em>用 YAML 定義流水線，讓 AI 任務像飛行航線一樣精準執行</em>
</p>

## 📖 專案介紹

TaskPilot-CLI 是一款面向開發者的輕量級終端工具，讓你透過 YAML 檔案定義複雜的多步驟 AI 任務流水線。它會自動解析任務間的依賴關係，平行執行獨立任務，並在失敗時智慧重試——一切都在終端中優雅呈現。

> 💡 **靈感來源**：設計理念借鑒了 AI Agent 編排框架（如 OpenAI Symphony），但聚焦於輕量化終端體驗。無需複雜的專案結構，一個 YAML 檔案即可起飛。

## ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 📝 **YAML 流水線定義** | 零程式碼編排，用 YAML 描述你的 AI 任務流程 |
| 🕸️ **DAG 依賴解析** | 自動分析步驟依賴，建構有向無環圖，平行執行獨立任務 |
| 🤖 **多 LLM 後端** | 支援 OpenAI、Anthropic、本地模型等多種大型語言模型 |
| 🧩 **7 種步驟類型** | `llm_call` / `http_request` / `shell_command` / `script` / `condition` / `transform` / `parallel` |
| 🔄 **失敗重試與逾時控制** | 自動重試失敗的步驟，靈活設定逾時時間 |
| 🔀 **條件執行** | 根據上游結果動態決定是否執行下游步驟 |
| 📊 **Rich TUI 儀表板** | 終端內即時視覺化執行進度，優雅且直觀 |
| 📜 **執行歷史記錄** | 自動儲存每次執行記錄，支援 JSON 結果匯出 |
| 🌍 **環境變數與模板變數** | 靈活的環境變數注入與 `{{variable}}` 模板變數系統 |

## 🛠️ 技術棧

- **Python 3.10+** — 核心執行期
- **Rich** — 終端 UI 與富文本渲染
- **PyYAML** — YAML 解析引擎
- **httpx**（可選）— HTTP 請求支援

## ⚡ 快速開始

### 📦 安裝

```bash
# 從 GitHub 直接安裝
pip install git+https://github.com/gitstq/TaskPilot-CLI.git

# 或者複製後本地安裝
git clone https://github.com/gitstq/TaskPilot-CLI.git
cd TaskPilot-CLI
pip install -e .
```

### 🎯 基本使用

```bash
# 初始化範例流水線
taskpilot init

# 執行流水線
taskpilot run pipeline.yaml

# 驗證流水線語法
taskpilot validate pipeline.yaml

# 查看流水線詳情
taskpilot show pipeline.yaml

# 查看執行歷史
taskpilot history
```

### 📋 YAML 流水線範例

```yaml
name: my-pipeline
description: My first pipeline
llm:
  provider: openai
  model: gpt-4o-mini
variables:
  url: "https://api.example.com"
steps:
  - name: fetch
    type: http_request
    config:
      url: "{{url}}"
      method: GET

  - name: analyze
    type: llm_call
    depends_on: [fetch]
    config:
      prompt: "Analyze: {{fetch}}"

  - name: report
    type: transform
    depends_on: [analyze]
    config:
      transform: template
      template: "Result: {{analyze}}"
```

## 🔧 環境變數設定

| 變數名 | 說明 |
|--------|------|
| `TASKPILOT_OPENAI_API_KEY` | OpenAI API 金鑰 |
| `TASKPILOT_LLM_API_KEY` | 通用 LLM API 金鑰（相容多種後端） |
| `TASKPILOT_OPENAI_API_BASE` | 自訂 API 端點（適用於代理或本地部署） |

## 🧠 設計思路

TaskPilot-CLI 的核心哲學是 **「宣告式編排，自動化執行」**：

1. **YAML 即程式碼** — 用人類可讀的 YAML 描述任務流程，無需撰寫腳本
2. **依賴自動解析** — 透過 DAG 演算法自動分析 `depends_on` 關係，最大化平行度
3. **結果自動傳遞** — 上游步驟的輸出自動注入到下游步驟的 `{{step_name}}` 模板中
4. **優雅降級** — 失敗不等於崩潰，重試機制與條件執行讓流水線具備彈性
5. **終端原生** — 拒絕繁重的 Web UI，一切在終端中完成，符合開發者直覺

## 🤝 參與貢獻

我們歡迎任何形式的貢獻！無論是提交 Bug、改進文件還是貢獻新功能：

1. Fork 本倉庫
2. 建立特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交變更 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 發起 Pull Request

## 📄 開源協議

本專案基於 [MIT 協議](https://opensource.org/licenses/MIT) 開源，詳見 [LICENSE](LICENSE) 檔案。

---

<h1 id="english">🚀 TaskPilot-CLI</h1>

<p align="center">
  <strong>Lightweight Terminal AI Task Orchestration & Execution Engine</strong><br/>
  <em>Define pipelines in YAML, execute AI tasks with flight-plan precision</em>
</p>

## 📖 Introduction

TaskPilot-CLI is a lightweight terminal tool designed for developers to define complex multi-step AI task pipelines using YAML files. It automatically resolves task dependencies, executes independent tasks in parallel, and intelligently retries on failure — all beautifully presented right in your terminal.

> 💡 **Inspired by** AI Agent orchestration frameworks like OpenAI Symphony, but laser-focused on a lightweight terminal experience. No heavy project scaffolding needed — a single YAML file is all it takes to get airborne.

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 📝 **YAML Pipeline Definition** | Zero-code orchestration — describe your AI workflow in human-readable YAML |
| 🕸️ **DAG Dependency Resolution** | Automatically analyzes step dependencies, builds a directed acyclic graph, and runs independent tasks in parallel |
| 🤖 **Multi-LLM Backend** | Supports OpenAI, Anthropic, local models, and other large language model providers |
| 🧩 **7 Step Types** | `llm_call` / `http_request` / `shell_command` / `script` / `condition` / `transform` / `parallel` |
| 🔄 **Retry & Timeout Control** | Automatically retries failed steps with configurable timeout settings |
| 🔀 **Conditional Execution** | Dynamically decides whether to run downstream steps based on upstream results |
| 📊 **Rich TUI Dashboard** | Real-time visual execution progress inside your terminal — elegant and intuitive |
| 📜 **Execution History** | Automatically saves run records with JSON result export support |
| 🌍 **Env Vars & Template Variables** | Flexible environment variable injection and `{{variable}}` template system |

## 🛠️ Tech Stack

- **Python 3.10+** — Core runtime
- **Rich** — Terminal UI and rich text rendering
- **PyYAML** — YAML parsing engine
- **httpx** (optional) — HTTP request support

## ⚡ Quick Start

### 📦 Installation

```bash
# Install directly from GitHub
pip install git+https://github.com/gitstq/TaskPilot-CLI.git

# Or clone and install locally
git clone https://github.com/gitstq/TaskPilot-CLI.git
cd TaskPilot-CLI
pip install -e .
```

### 🎯 Basic Usage

```bash
# Initialize a sample pipeline
taskpilot init

# Run a pipeline
taskpilot run pipeline.yaml

# Validate pipeline syntax
taskpilot validate pipeline.yaml

# Show pipeline details
taskpilot show pipeline.yaml

# View execution history
taskpilot history
```

### 📋 YAML Pipeline Example

```yaml
name: my-pipeline
description: My first pipeline
llm:
  provider: openai
  model: gpt-4o-mini
variables:
  url: "https://api.example.com"
steps:
  - name: fetch
    type: http_request
    config:
      url: "{{url}}"
      method: GET

  - name: analyze
    type: llm_call
    depends_on: [fetch]
    config:
      prompt: "Analyze: {{fetch}}"

  - name: report
    type: transform
    depends_on: [analyze]
    config:
      transform: template
      template: "Result: {{analyze}}"
```

## 🔧 Environment Variables

| Variable | Description |
|----------|-------------|
| `TASKPILOT_OPENAI_API_KEY` | OpenAI API key |
| `TASKPILOT_LLM_API_KEY` | Generic LLM API key (compatible with multiple backends) |
| `TASKPILOT_OPENAI_API_BASE` | Custom API endpoint (for proxies or local deployments) |

## 🧠 Design Philosophy

TaskPilot-CLI is built on the core principle of **"Declarative Orchestration, Automatic Execution"**:

1. **YAML as Code** — Describe task flows in human-readable YAML without writing scripts
2. **Automatic Dependency Resolution** — DAG algorithms analyze `depends_on` relationships to maximize parallelism
3. **Automatic Result Passing** — Upstream step outputs are automatically injected into downstream `{{step_name}}` templates
4. **Graceful Degradation** — Failure doesn't mean collapse; retry mechanisms and conditional execution give pipelines resilience
5. **Terminal-Native** — No heavy web UI — everything happens in the terminal, matching developer intuition

## 🤝 Contributing

We welcome contributions of all kinds! Whether it's filing a bug, improving documentation, or contributing new features:

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is open-sourced under the [MIT License](https://opensource.org/licenses/MIT). See the [LICENSE](LICENSE) file for details.
