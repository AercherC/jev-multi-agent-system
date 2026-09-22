#!/usr/bin/env python
"""jev_system_eval.py —— 评测 OpenJev 工具路由（route_tool）的准确率。

背景
----
Jev 已被集成到 Agent 内部：ReAct 第一步如果 LLM 没调工具，由 route_tool 从候选工具
（query_order / search_faq / none）中选一个，返回工具名则强制重试一次工具调用。

本脚本测的是这个**工具路由层**本身准不准——即 route_tool 对每类问题选对工具。
与 deepseek_tool_eval 同逻辑、同用例，只是被测对象从 DeepSeek 换成 Jev。

跑法：``uv run python experiments/jev_system_eval.py``（需 TYPESAFE_API_KEY）
"""

from __future__ import annotations

from dataclasses import dataclass

from customer_service.core.jev_router import JevRouter


@dataclass
class Case:
    text: str
    expect: str | None  # 期望工具名；None 表示不应调工具
    category: str


CASES: list[Case] = [
    # 订单类 → query_order
    Case("查一下订单 ORD20240001", "query_order", "order"),
    Case("订单 ORD20240002 发货了吗", "query_order", "order"),
    Case("ORD20240003 到哪了", "query_order", "order"),
    Case("帮我看看 ORD20240001 的物流", "query_order", "order"),
    Case("查个单子 ORD20240002", "query_order", "order"),
    Case("ORD20240003 现在什么状态", "query_order", "order"),
    Case("订单 ORD20240001 物流信息", "query_order", "order"),
    Case("ORD20240002 还没到吗", "query_order", "order"),
    Case("帮我查 ORD20240003", "query_order", "order"),
    Case("订单号 ORD20240001 查一下", "query_order", "order"),
    Case("我的单子 ORD20240002 怎么样了", "query_order", "order"),
    Case("ORD20240001 配送到哪了", "query_order", "order"),
    Case("查 ORD20240003 的发货情况", "query_order", "order"),
    Case("ORD20240001 运单号多少", "query_order", "order"),
    Case("订单 ORD20240002 状态查询", "query_order", "order"),
    # FAQ 类 → search_faq
    Case("支持7天无理由退货吗", "search_faq", "faq"),
    Case("配送多久到", "search_faq", "faq"),
    Case("支持微信支付吗", "search_faq", "faq"),
    Case("运费多少", "search_faq", "faq"),
    Case("有会员折扣吗", "search_faq", "faq"),
    Case("支持花呗分期吗", "search_faq", "faq"),
    Case("你们卖什么商品", "search_faq", "faq"),
    Case("能货到付款吗", "search_faq", "faq"),
    Case("快速配送次日达吗", "search_faq", "faq"),
    Case("正品保障吗", "search_faq", "faq"),
    Case("退换货政策是什么", "search_faq", "faq"),
    Case("满多少免运费", "search_faq", "faq"),
    Case("怎么付款", "search_faq", "faq"),
    Case("金卡会员多少折扣", "search_faq", "faq"),
    Case("发顺丰吗", "search_faq", "faq"),
    # 闲聊类 → 不应调工具
    Case("今天天气真好", None, "chitchat"),
    Case("你叫什么名字", None, "chitchat"),
    Case("谢谢你", None, "chitchat"),
    Case("讲个笑话", None, "chitchat"),
    Case("你是机器人吗", None, "chitchat"),
    Case("现在几点了", None, "chitchat"),
    Case("帮我写首诗", None, "chitchat"),
    Case("今天星期几", None, "chitchat"),
    Case("你能做什么", None, "chitchat"),
    Case("再见", None, "chitchat"),
]


def main() -> None:
    router = JevRouter()
    if not router.enabled:
        print("⚠️ 未配置 TYPESAFE_API_KEY")
        return

    by_cat: dict[str, dict[str, int]] = {}
    for case in CASES:
        got = router.route_tool(case.text, ["query_order", "search_faq"])
        ok = got == case.expect
        cat = by_cat.setdefault(case.category, {"correct": 0, "total": 0})
        cat["total"] += 1
        if ok:
            cat["correct"] += 1
        mark = "✓" if ok else "✗"
        print(
            f"{mark} expect={str(case.expect):12s} got={str(got):12s} "
            f"{case.category:9s} | {case.text}"
        )

    total_ok = sum(r["correct"] for r in by_cat.values())
    total = sum(r["total"] for r in by_cat.values())
    print("\n===== Jev 路由准确率 =====")
    for cat, r in by_cat.items():
        print(f"  {cat:9s} {r['correct']}/{r['total']} = {r['correct']/r['total']:.0%}")
    print(f"  {'ALL':9s} {total_ok}/{total} = {total_ok/total:.0%}")


if __name__ == "__main__":
    main()