# ADK AGUI Middleware（中间件）

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/trendmicro/adk-agui-middleware)
[![CI](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/ci.yml/badge.svg)](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/ci.yml)
[![CodeQL](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/codeql.yml/badge.svg)](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/codeql.yml)
[![Semgrep](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/semgrep.yml/badge.svg)](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/semgrep.yml)
[![Gitleaks](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/gitleaks.yml/badge.svg)](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/gitleaks.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Security: Bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Type Checker: mypy](https://img.shields.io/badge/type_checker-mypy-blue.svg)](https://github.com/python/mypy)

语言： [English](README.md) ｜ [繁體中文](README.zh-TW.md) ｜ [简体中文](README.zh-CN.md) ｜ [日本語](README.ja.md)

**企业级 Python 3.13+ 中间层，连接 Google 的 Agent Development Kit（ADK）与 AGUI 协议，提供高性能的 Server-Sent Events（SSE）流式传输与 Human-in-the-Loop（HITL）工作流编排。**

## 概述

本项目将 Google ADK 与 AGUI 协议桥接，帮助你快速构建具备实时流式传输与 HITL 能力的 AI 代理应用。支持高效、可观测、可扩展的生产级架构。

### 关键特性

- ⚡ SSE 流式：稳定、低延迟事件流，完整 ADK ↔ AGUI 转换
- 🔒 会话管理：线程安全的锁定、可配置超时与重试机制
- 🤝 HITL 工作流：内置人机协同流程与状态持久化
- 🏗️ 企业级架构：模块化设计、依赖注入、清晰分层
- 🛡️ 生产就绪：完善的错误处理、结构化日志、优雅关闭
- 🎯 类型安全：完整 Python 3.13 类型注解与严格 mypy 校验

## 安装

```bash
pip install adk-agui-middleware
```

### 系统要求

- Python 3.13+（建议 3.13.3 以上）
- Google ADK >= 1.9.0
- AGUI Protocol >= 0.1.7
- FastAPI >= 0.104.0

## 快速开始

下面是最小可用示例：在 FastAPI 中注册主要 AGUI 端点并用 SSE 返回流式事件。

```python
from fastapi import FastAPI, Request
from google.adk.agents import BaseAgent
from adk_agui_middleware import SSEService
from adk_agui_middleware.endpoint import register_agui_endpoint
from adk_agui_middleware.data_model.context import ConfigContext

# 初始化 FastAPI 应用
app = FastAPI(title="AI Agent Service", version="1.0.0")

# 定义自定义 ADK agent
class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.instructions = "You are a helpful AI assistant."

# 简单的用户 ID 提取
async def extract_user_id(content, request: Request) -> str:
    return request.headers.get("x-user-id", "default-user")

# 创建 SSE 服务
agent = MyAgent()
sse_service = SSEService(
    agent=agent,
    config_context=ConfigContext(
        app_name="my-app",
        user_id=extract_user_id,
        session_id=lambda content, req: content.thread_id,
    )
)

# 注册端点
register_agui_endpoint(app, sse_service)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 示例

- 参见 `examples/` 目录，从最小化 SSE 到进阶能力（历史/状态、生命周期钩子、HITL 等）均有示例。
- 使用 `uvicorn` 可直接启动各示例（详见 `examples/README.md`）。

## 架构总览

高层架构与事件转换流程如下（Mermaid 图保持与主 README 一致）：

### 系统架构

```mermaid
%% 与主 README 相同的 Mermaid 图表（保留原内容即可）
```

### 事件转换管线

```mermaid
%% 与主 README 相同的 Mermaid 图表（保留原内容即可）
```

### Human-in-the-Loop（HITL）流程

```mermaid
%% 与主 README 相同的 Mermaid 图表（保留原内容即可）
```

## 高级配置与扩展

- RunnerConfig：管理 ADK 运行配置与服务绑定，默认提供内存型后端（便于开发/测试）；也可切换为生产环境外部服务（如 Firestore、GCS、Redis、Vault 等）。
- HandlerContext：提供请求生命周期钩子（事件过滤、翻译、输入输出记录、超时处理、状态快照转换等），可按需插拔自定义逻辑。

示例（自定义运行配置）：

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

## API 参考

主要 AGUI 端点（使用 `register_agui_endpoint(app, sse_service)` 注册）：

| 方法 | 路径 | 说明 | 请求体 | 响应类型 |
|------|------|------|--------|----------|
| POST | `/` | 以流式响应执行 agent | `RunAgentInput` | `EventSourceResponse` |

历史查询端点（使用 `register_agui_history_endpoint(app, history_service)` 注册）：

| 方法 | 路径 | 说明 | 请求体 | 响应类型 |
|------|------|------|--------|----------|
| GET | `/thread/list` | 列出用户会话线程 | - | `List[Dict[str, str]]` |
| DELETE | `/thread/{thread_id}` | 删除会话线程 | - | `Dict[str, str]` |
| GET | `/message_snapshot/{thread_id}` | 获取会话历史 | - | `MessagesSnapshotEvent` |

状态管理端点（使用 `register_state_endpoint(app, state_service)` 注册）：

| 方法 | 路径 | 说明 | 请求体 | 响应类型 |
|------|------|------|--------|----------|
| GET | `/state_snapshot/{thread_id}` | 获取状态快照 | - | `StateSnapshotEvent` |
| PATCH | `/state/{thread_id}` | 应用状态变更 | `List[JSONPatch]` | `Dict[str, str]` |

## 许可

本项目基于 MIT 许可，详见 `LICENSE`。

## 贡献

请参见 `CONTRIBUTING.md` 了解规范与提交流程。

## 安全

请参见 `SECURITY.md` 了解安全政策与漏洞报告流程。

