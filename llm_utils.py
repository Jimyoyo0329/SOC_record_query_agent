import os
from openai import OpenAI
from typing import Optional

# 從環境變數中取得 API 金鑰（請先設定 OPENAI_API_KEY）
api_key = "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"

# 初始化 OpenAI 客戶端
client = OpenAI(api_key=api_key)

def generate_note_from_example(example_note: str, alert_description: str) -> str:
    system_prompt = (
        "你是一位資安分析師，請根據提供的告警描述與範例筆記，生成一段語意類似、內容自然、格式一致的新註解，"
        "不要複製範例內容，可以換句話說。"
        "但是人名，以及職稱，以及組別都要保留"
    )

    user_prompt = f"""
告警描述：
{alert_description}

範例：
{example_note}

請產出新note：
"""

    # 呼叫新版 chat.completions.create API
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=300
    )

    return response.choices[0].message.content.strip()
