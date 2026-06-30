# Backend contract

The HTTP surface kvllm guarantees so clients can depend on it. kvllm is a **chat-only** backend:
it serves **one model per process** behind an OpenAI-compatible `/v1`. Any OpenAI client works —
`openai`, `langchain_openai.ChatOpenAI`, and `trt-llm-langchain`'s `ChatTrtLlm` (a `ChatOpenAI`
subclass) by pointing `TRTLLM_CHAT_URL` at it.

This mirrors the **chat surface** of `trt-llm-langchain/docs/03-backend-contract.md`, and
deliberately **omits its control surface** (the Triton KServe v2 load/unload endpoints). kvllm has
no in-process model lifecycle: switching models means stopping one `serve` and starting another
(Sprint 3 makes that a systemd unit).

## Chat surface — OpenAI-compatible (`:8000` by default)

| Method / path | Requirement |
|---|---|
| `GET /v1/models` | Returns `{"data": [{"id": <model_key>, ...}]}`. **The `id` is the registry key** the client passes as `model=` (e.g. `qwen2.5-7b-instruct`), because kvllm serves with `--served-model-name <key>`. Exactly one entry — one model per process. |
| `POST /v1/chat/completions` | Standard OpenAI chat completion → `chat.completion` with `choices[].message.content`. Tool calling via `tools=[...]` returns `choices[].message.tool_calls` on tool-capable models (those with a `tool_parser` in the registry). |
| `POST /v1/chat/completions` (`"stream": true`) | SSE of `chat.completion.chunk` with `choices[].delta.content`. Required for `.stream()`. (Streaming **tool** turns are fragile — see Sprint 1 notes; non-streaming tool turns first.) |
| `POST /v1/completions` | Standard OpenAI text completion (legacy; chat is preferred). |

Notes:
- **API key:** sent but ignored — any non-empty string works (use `"EMPTY"`). vLLM is started
  without `--api-key`.
- **Reasoning models:** with a `reasoning_parser` (e.g. `deepseek_r1`), the `<think>` span is split
  into a non-standard `reasoning_content` field. `ChatOpenAI` ignores non-standard fields, so the
  visible `content` is the post-think answer.
- **Schema conformance:** responses follow the official OpenAI schema; clients can rely on standard
  fields only.

## What the client passes

```python
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(
    base_url="http://localhost:8000/v1",
    api_key="EMPTY",
    model="qwen2.5-7b-instruct",   # == the registry key == GET /v1/models id
)
```

## Not provided (vs the TRT-LLM backend)

- **No control surface.** No `/v2/repository/{index,load,unload}`, no readiness-per-component. One
  model is loaded for the process's lifetime.
- **No multi-model index.** `GET /v1/models` lists exactly the one served model.
- **Discovery / switching** is out-of-band: the [`models.toml`](../models.toml) registry +
  `just serve <key>`. The single-GPU switch is stop-then-start (Sprint 3: systemd).
