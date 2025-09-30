# ADK AGUI Middleware（ミドルウェア）

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/trendmicro/adk-agui-middleware)
[![CI](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/ci.yml/badge.svg)](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/ci.yml)
[![CodeQL](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/codeql.yml/badge.svg)](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/codeql.yml)
[![Semgrep](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/semgrep.yml/badge.svg)](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/semgrep.yml)
[![Gitleaks](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/gitleaks.yml/badge.svg)](https://github.com/trendmicro/adk-agui-middleware/actions/workflows/gitleaks.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Security: Bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Type Checker: mypy](https://img.shields.io/badge/type_checker-mypy-blue.svg)](https://github.com/python/mypy)

言語: [English](README.md) ｜ [繁體中文](README.zh-TW.md) ｜ [简体中文](README.zh-CN.md) ｜ [日本語](README.ja.md)

**エンタープライズ向け Python 3.13+ ミドルウェア。Google の Agent Development Kit（ADK）と AGUI プロトコルを橋渡しし、高性能な Server-Sent Events（SSE）ストリーミングと Human-in-the-Loop（HITL）ワークフローのオーケストレーションを提供します。**

## 概要

本プロジェクトは、ADK と AGUI を接続し、リアルタイムなストリーミングと HITL を備えた AI エージェントアプリケーションを素早く構築できるようにします。効率的で観測可能、拡張可能なプロダクション品質のアーキテクチャを提供します。

### 主な機能

- ⚡ SSE ストリーミング: 低レイテンシかつ安定したイベント配信、ADK ↔ AGUI の双方向変換
- 🔒 セッション管理: スレッドセーフなロック、タイムアウト・リトライの設定可能
- 🤝 HITL ワークフロー: 人間参加のオーケストレーションと状態永続化
- 🏗️ エンタープライズ設計: モジュール化、DI、明確なレイヤ分離
- 🛡️ 本番運用対応: エラーハンドリング、構造化ログ、クリーンシャットダウン
- 🎯 型安全: Python 3.13 の型注釈と厳格な mypy チェック

## インストール

```bash
pip install adk-agui-middleware
```

### 必要要件

- Python 3.13+（推奨 3.13.3 以降）
- Google ADK >= 1.9.0
- AGUI Protocol >= 0.1.7
- FastAPI >= 0.104.0

## クイックスタート

最小構成のサンプルです。FastAPI に主要な AGUI エンドポイントを登録し、SSE でストリーミング応答を返します。

```python
from fastapi import FastAPI, Request
from google.adk.agents import BaseAgent
from adk_agui_middleware import SSEService
from adk_agui_middleware.endpoint import register_agui_endpoint
from adk_agui_middleware.data_model.context import ConfigContext

# FastAPI アプリの初期化
app = FastAPI(title="AI Agent Service", version="1.0.0")

# カスタム ADK エージェント
class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.instructions = "You are a helpful AI assistant."

# ユーザー ID 抽出（例）
async def extract_user_id(content, request: Request) -> str:
    return request.headers.get("x-user-id", "default-user")

# SSE サービス作成
agent = MyAgent()
sse_service = SSEService(
    agent=agent,
    config_context=ConfigContext(
        app_name="my-app",
        user_id=extract_user_id,
        session_id=lambda content, req: content.thread_id,
    )
)

# エンドポイント登録
register_agui_endpoint(app, sse_service)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## サンプル

- `examples/` ディレクトリに、最小 SSE から履歴/状態、ライフサイクル処理、HITL までの例があります。
- 各サンプルは `uvicorn` で起動可能です（詳細は `examples/README.md`）。

## アーキテクチャ概要

高レベル構成とイベント変換フロー（Mermaid 図はメイン README と同一内容を想定）:

### システムアーキテクチャ

```mermaid
%% メイン README と同じ Mermaid 図（内容は省略）
```

### イベント変換パイプライン

```mermaid
%% メイン README と同じ Mermaid 図（内容は省略）
```

### Human-in-the-Loop（HITL）フロー

```mermaid
%% メイン README と同じ Mermaid 図（内容は省略）
```

## 高度な設定と拡張

- RunnerConfig: ADK ランタイム設定とサービス構成を管理。デフォルトでインメモリ実装を用意（開発/検証に便利）。Firestore / GCS / Redis / Vault など外部サービスへの切替も可能。
- HandlerContext: リクエストライフサイクルのフック（イベントフィルタ/翻訳、入出力記録、タイムアウト処理、状態スナップショット整形など）を提供し、要件に応じて差し替え可能。

例（実行設定のカスタマイズ）:

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

## API リファレンス

メイン AGUI エンドポイント（`register_agui_endpoint(app, sse_service)` で登録）:

| メソッド | パス | 説明 | リクエストボディ | レスポンス |
|----------|------|------|------------------|------------|
| POST | `/` | ストリーミング応答でエージェント実行 | `RunAgentInput` | `EventSourceResponse` |

履歴エンドポイント（`register_agui_history_endpoint(app, history_service)` で登録）:

| メソッド | パス | 説明 | リクエストボディ | レスポンス |
|----------|------|------|------------------|------------|
| GET | `/thread/list` | ユーザーのスレッド一覧 | - | `List[Dict[str, str]]` |
| DELETE | `/thread/{thread_id}` | スレッド削除 | - | `Dict[str, str]` |
| GET | `/message_snapshot/{thread_id}` | 会話履歴の取得 | - | `MessagesSnapshotEvent` |

状態管理エンドポイント（`register_state_endpoint(app, state_service)` で登録）:

| メソッド | パス | 説明 | リクエストボディ | レスポンス |
|----------|------|------|------------------|------------|
| GET | `/state_snapshot/{thread_id}` | 状態スナップショット取得 | - | `StateSnapshotEvent` |
| PATCH | `/state/{thread_id}` | 状態変更の適用 | `List[JSONPatch]` | `Dict[str, str]` |

## ライセンス

本プロジェクトは MIT ライセンスです。詳細は `LICENSE` を参照してください。

## コントリビュート

開発規約と PR 手順は `CONTRIBUTING.md` を参照してください。

## セキュリティ

セキュリティポリシーと脆弱性報告手順は `SECURITY.md` を参照してください。

