import httpx

from customer_service.core.llm import Settings

settings = Settings()
API_KEY = settings.jev_api_key

faq_questions = [
    "支持7天无理由退货吗", "配送多久到", "支持微信支付吗",
    "运费多少", "有会员折扣吗", "支持花呗分期吗",
    "你们卖什么商品", "能货到付款吗", "快速配送次日达吗",
    "正品保障吗", "退换货政策是什么", "满多少免运费",
    "怎么付款", "金卡会员多少折扣", "发顺丰吗",
]

for q in faq_questions:
    resp = httpx.post(
        f"{settings.jev_base_url}/v1/systemone",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": "openjev-latest",
            "state": q,
            "questions": {
                "should_search_faq": {
                    "type": "noul",
                    "instructions": "这是一个涉及店铺政策、规则或流程的问题吗？需要查询知识库才能回答吗？",
                }
            },
        },
        timeout=30.0,
    )
    noul = resp.json()["answers"]["should_search_faq"]["noul"]
    print(f"{'✅' if noul >= 0.8 else '❌'} {noul:.4f}  {q}")