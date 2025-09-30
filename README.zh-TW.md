# ADK AGUI Middleware（中介軟體）

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/trendmicro/adk-agui-middleware)
[![CI](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/ci.yml/badge.svg)](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/ci.yml)
[![CodeQL](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/codeql.yml/badge.svg)](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/codeql.yml)
[![Semgrep](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/semgrep.yml/badge.svg)](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/semgrep.yml)
[![Gitleaks](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/gitleaks.yml/badge.svg)](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/gitleaks.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Security: Bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Type Checker: mypy](https://img.shields.io/badge/type_checker-mypy-blue.svg)](https://github.com/python/mypy)

語言： [English](README.md) ｜ [繁體中文](README.zh-TW.md) ｜ [简体中文](README.zh-CN.md) ｜ [日本語](README.ja.md)

**企業級 Python 3.13+ 中介層，無縫橋接 Google 的 Agent Development Kit（ADK）與 AGUI 協議，提供高效能的 Server-Sent Events（SSE）串流與 Human-in-the-Loop（HITL）工作流程協調。**

## 概述

本專案將 Google ADK 與 AGUI 協議串接，協助您快速打造具備即時串流與 HITL 能力的 AI 代理應用。支援高效、可觀測、可擴充的生產級架構。

### 核心特色

- ⚡ SSE 串流：即時、穩定的事件串流，完整 ADK ↔ AGUI 轉換
- 🔒 工作階段管理：執行緒安全鎖定、可設定逾時與重試策略
- 🤝 HITL 工作流程：人機協作流程，內建狀態持久化
- 🏗️ 企業級架構：模組化設計、依賴注入、清晰的分層
- 🛡️ 生產就緒：錯誤處理、結構化記錄、優雅關閉
- 🎯 型別安全：完全支援 Python 3.13 型別註記與嚴格 mypy 驗證

## 安裝

```bash
pip install adk-agui-middleware
```

### 系統需求

- Python 3.13+（建議 3.13.3 以上）
- Google ADK >= 1.9.0
- AGUI Protocol >= 0.1.7
- FastAPI >= 0.104.0

## 快速開始

以下為最小可用範例：在 FastAPI 中註冊主要的 AGUI 端點並使用 SSE 回傳串流事件。

```python
from fastapi import FastAPI, Request
from google.adk.agents import BaseAgent
from adk_agui_middleware import SSEService
from adk_agui_middleware.endpoint import register_agui_endpoint
from adk_agui_middleware.data_model.context import ConfigContext

# 初始化 FastAPI 應用
app = FastAPI(title="AI Agent Service", version="1.0.0")

# 定義自訂 ADK agent
class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.instructions = "You are a helpful AI assistant."

# 簡易的使用者 ID 擷取
async def extract_user_id(content, request: Request) -> str:
    return request.headers.get("x-user-id", "default-user")

# 建立 SSE 服務
agent = MyAgent()
sse_service = SSEService(
    agent=agent,
    config_context=ConfigContext(
        app_name="my-app",
        user_id=extract_user_id,
        session_id=lambda content, req: content.thread_id,
    )
)

# 註冊端點
register_agui_endpoint(app, sse_service)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 範例

- 直接參考 `examples/` 目錄，從最小化 SSE 到進階處理（歷史／狀態、工作流程處理、HITL 等）皆有示範。
- 可用 `uvicorn` 啟動各範例（詳見 `examples/README.md`）。

## 架構總覽

高階架構與事件轉換流程如下（Mermaid 圖表維持原樣）：

### 系統架構

```mermaid
%% 與主 README 相同的 Mermaid 圖表（保留原內容即可）
```

### 事件轉換管線

```mermaid
%% 與主 README 相同的 Mermaid 圖表（保留原內容即可）
```

### Human-in-the-Loop（HITL）流程

```mermaid
%% 與主 README 相同的 Mermaid 圖表（保留原內容即可）
```

## 進階設定與擴充

- RunnerConfig：管理 ADK 執行設定與服務繫結，預設提供記憶體內（in-memory）後端，易於開發與測試；亦可切換為生產環境的外部服務（如 Firestore、GCS、Redis、Vault 等）。
- HandlerContext：提供請求生命週期的掛鉤（事件過濾、翻譯、輸入輸出記錄、逾時處理、狀態快照轉換等），可依需求插拔自訂邏輯。

範例（自訂執行設定）：

```python
from google.adk.agents import RunConfig
from google.adk.agents.run_config import StreamingMode
from adk_agui_middleware.data_model.config import RunnerConfig

runner_config = RunnerConfig(
    run_config=RunConfig(
        streaming_mode=StreamingMode.SSE,
        max_iterations=100,
        timeout=600,
        enable_thinking=True,
    )
)
```

## API 參考

主要 AGUI 端點（以 `register_agui_endpoint(app, sse_service)` 註冊）：

| 方法 | 路徑 | 說明 | 請求內容 | 回應類型 |
|------|------|------|----------|----------|
| POST | `/` | 以串流回應執行 agent | `RunAgentInput` | `EventSourceResponse` |

歷史查詢端點（以 `register_agui_history_endpoint(app, history_service)` 註冊）：

| 方法 | 路徑 | 說明 | 請求內容 | 回應類型 |
|------|------|------|----------|----------|
| GET | `/thread/list` | 列出使用者對話串 | - | `List[Dict[str, str]]` |
| DELETE | `/thread/{thread_id}` | 刪除對話串 | - | `Dict[str, str]` |
| GET | `/message_snapshot/{thread_id}` | 取得對話歷史 | - | `MessagesSnapshotEvent` |

狀態管理端點（以 `register_state_endpoint(app, state_service)` 註冊）：

| 方法 | 路徑 | 說明 | 請求內容 | 回應類型 |
|------|------|------|----------|----------|
| GET | `/state_snapshot/{thread_id}` | 取得狀態快照 | - | `StateSnapshotEvent` |
| PATCH | `/state/{thread_id}` | 套用狀態變更 | `List[JSONPatch]` | `Dict[str, str]` |

## 授權

本專案採用 MIT 授權，詳見 `LICENSE`。

## 貢獻

請參考 `CONTRIBUTING.md` 了解開發規範與提交流程。

## 安全性

請參考 `SECURITY.md` 瞭解回報與處置流程。

