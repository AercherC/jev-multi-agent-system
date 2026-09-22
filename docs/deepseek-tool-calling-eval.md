# DeepSeek tool calling 实测 eval（Phase 8）

> 脚本：`experiments/deepseek_tool_eval.py` · 模型 `deepseek-chat` · 2026-07 · 40 prompt × 3 模式 = 120 次真实调用

## 想回答的问题

"让 LLM 调工具"有三种做法，哪个最可靠？

1. **`tool_calling`** — 原生 `tools` 参数（OpenAI 兼容协议）
2. **`json_mode`** — `response_format=json_object`，让 LLM 输出 `{"tool", "args"}`，自己解析
3. **`prompt_fallback`** — 纯 prompt 引导输出 `TOOL: name`，正则解析（模拟 SDK 不支持 tools 的退化路径）

## 场景设计

40 个 prompt，分三类，**每类有明确期望**：

| 类别 | 数量 | 期望调用 |
|------|------|----------|
| order（查订单） | 15 | `query_order` |
| faq（咨询） | 15 | `search_faq` |
| chitchat（闲聊） | 10 | **不调任何工具** |

## 结果

### 总成功率

| 模式 | 成功率 |
|------|--------|
| `tool_calling` | **30/40 = 75%** |
| `json_mode` | **33/40 = 82%** |
| `prompt_fallback` | **34/40 = 85%** |

### 按类别

| 模式 | order | faq | chitchat |
|------|-------|-----|----------|
| `tool_calling` | 100% (15/15) | **33% (5/15)** | 100% (10/10) |
| `json_mode` | 100% (15/15) | **53% (8/15)** | 100% (10/10) |
| `prompt_fallback` | 100% (15/15) | **60% (9/15)** | 100% (10/10) |

## 失败案例分析

### `tool_calling` / `json_mode` 的主要失败：模型"自信跳过检索"

失败案例："配送多久到""你们卖什么商品""支持 7 天退货吗"。

这些是 **faq 类**，模型**觉得自己知道答案就直接回答了**，没有调用 `search_faq`。这不是 tool calling 机制不稳，而是 RAG 的经典难题——**模型自信时倾向于跳过检索**。`tool_calling` 的 faq 63% 失败全部源于此。

> 启示：要提升 faq 召回率，应在 system prompt 里强制"咨询类问题必须先 `search_faq`"，或采用"检索优先"策略（本项目的 FAQAgent system prompt 已强调这一点）。本项目进一步用 **OpenJev 意图判断层**在 ReAct 第一步复核：LLM 漏调工具时由 `jev_router` 兜底强制触发一次（见 README 的正确率前后对比）。

### `prompt_fallback` 的 40% 失败：纯 prompt 约束不可靠

faq 类只有 **60%**——模型大量不按 `TOOL: name` 格式输出，直接给出自然语言答案，正则匹配不到 → 判为 `None`（没调工具）。

> 启示：**不要用纯 prompt 模拟 tool calling**。模型对"输出结构化指令"的遵守度远不如原生 function calling 协议。

### `chitchat` 三模式全 100%

"今天天气真好""讲个笑话""再见"等闲聊，三种模式都**正确地不调工具**。说明模型对"该不该调工具"的判断本身是可靠的，差异在于"该调时能否可靠触发"。

## 结论与对本项目的影响

1. **三种模式差异不如 tool calling 显著**：`tool_calling` 75%、`json_mode` 82%、`prompt_fallback` 85%。三者的共性短板都在 **faq 漏判**（33% / 53% / 60%）——模型"自信跳过检索"。
2. **faq 召回是核心痛点**：无论哪种模式，faq 类该调 `search_faq` 却漏掉的比例都高。原生 function calling 并不能解决"模型自以为知道答案"的问题。
3. **对策是判断层兜底，而非换调用方式**：本项目因此引入 **OpenJev 意图判断层**，在 ReAct 第一步 LLM 未调工具时用 `route_tool` 复核并强制触发。实测 faq 达到 100%（见 README）。

## 复现

```bash
uv run python experiments/deepseek_tool_eval.py   # 需 DEEPSEEK_API_KEY
```

> 样本量 40，覆盖三类典型场景。结论方向稳健；若需更细统计，可扩展 prompt 集至 100+。
