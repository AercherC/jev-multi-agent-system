"""jev_router.py —— 用 OpenJev 做工具路由。

OpenJev 是结构化决策模型，不做文本生成，只返回 choice/noul 概率。
本模块提供两类判断：
- route_tool: 从候选工具中选一个（Choice）
- should_call_tool: 判断是否该调用某个工具（Noul）

设计原则：
- 任何异常都返回 None（不强制），不阻塞主流程。
- 没配置 API Key 时也返回 None，保持向后兼容。
"""

from __future__ import annotations

import logging

import requests

from customer_service.core.llm import Settings

logger = logging.getLogger(__name__)

ROUTE_INSTRUCTIONS = (
    "用户问题应该调用哪个工具？"
    "订单查询、物流追踪、发货状态选 query_order；"
    "店铺政策、退换货、配送、支付、会员规则选 search_faq；"
    "闲聊、问候、与店铺业务无关选 none。"
)


class JevRouter:
    """OpenJev 工具路由客户端。"""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

    @property
    def enabled(self) -> bool:
        return bool(self.settings.jev_api_key)

    def route_tool(
        self,
        user_input: str,
        candidate_tools: list[str],
        *,
        timeout: float = 5.0,
    ) -> str | None:
        """从候选工具中选一个。返回工具名或 None（不调工具）。

        Args:
            user_input: 用户原始问题。
            candidate_tools: 候选工具名列表，如 ["query_order", "search_faq"]。
            timeout: HTTP 超时秒数。
        """
        if not self.enabled or not candidate_tools:
            return None

        criteria = {name: self._criteria_for(name) for name in candidate_tools}
        criteria["none"] = "闲聊、问候、与店铺业务无关"

        try:
            resp = requests.post(
                f"{self.settings.jev_base_url}/v1/systemone",
                headers={
                    "Authorization": f"Bearer {self.settings.jev_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "openjev-latest",
                    "state": user_input,
                    "questions": {
                        "tool_choice": {
                            "type": "choice",
                            "instructions": ROUTE_INSTRUCTIONS,
                            "criteria": criteria,
                        }
                    },
                },
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            choice = data["answers"]["tool_choice"]["choice"]
            logger.debug("Jev route_tool: %s -> %s", user_input, choice)
            return None if choice == "none" else choice
        except Exception as e:  # noqa: BLE001
            logger.warning("Jev route_tool 失败，返回 None: %s", e)
            return None

    def should_call_tool(
        self,
        user_input: str,
        tool_name: str,
        *,
        timeout: float = 5.0,
    ) -> bool:
        """判断是否该调用某个工具。返回 True 表示该调。

        Args:
            user_input: 用户原始问题。
            tool_name: 目标工具名。
            timeout: HTTP 超时秒数。
        """
        if not self.enabled:
            return False

        try:
            resp = requests.post(
                f"{self.settings.jev_base_url}/v1/systemone",
                headers={
                    "Authorization": f"Bearer {self.settings.jev_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "openjev-latest",
                    "state": user_input,
                    "questions": {
                        f"call_{tool_name}": {
                            "type": "noul",
                            "instructions": f"用户问题需要调用 {tool_name} 工具才能准确回答吗？",
                        }
                    },
                },
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            noul = float(data["answers"][f"call_{tool_name}"]["noul"])
            logger.debug("Jev should_call_tool(%s) noul=%.4f", tool_name, noul)
            return noul >= 0.8
        except Exception as e:  # noqa: BLE001
            logger.warning("Jev should_call_tool 失败，返回 False: %s", e)
            return False

    @staticmethod
    def _criteria_for(tool_name: str) -> str:
        return {
            "query_order": "订单查询、物流追踪、发货状态",
            "search_faq": "店铺政策、退换货、配送、支付、会员规则",
        }.get(tool_name, tool_name)