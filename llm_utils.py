import os
from openai import OpenAI
from typing import Optional



# 從環境變數中取得 API 金鑰（請先設定 OPENAI_API_KEY）
api_key = "KEY"

# 初始化 OpenAI 客戶端
client = OpenAI(api_key=api_key)

# 產生新note
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

請產出新note，並且幫我進行重點整理：
"""

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

# 產生相似事件大綱
def generate_event_outline(metadata_text: str) -> str:
    system_prompt = "你是一位資安分析師，請閱讀以下事件資訊，產生一段詳細大綱，包含事件背景與調查結果重點。"

    user_prompt = f"""
以下為一筆事件的詳細資訊，請根據提供的欄位與原始註解，幫我撰寫一段結構清楚的大綱說明。

注意：
- **僅產出以下格式的內容，其他補充說明請省略**
- 各段標題與條列項請**保持一致**，不要更動文字或順序
- 若原始欄位中某些值為空，也請保留欄位但標示為「無」

---

【事件資料】
{metadata_text}

---

請依下列格式產出結果（直接開始填內容，不要加註解）：

#### 事件背景
- 告警名稱: 
- 來源 IP: 
- 目的 IP: 
- 相關網域: 

#### 事件大綱
- 負責人員或單位: 
- 事件概述: 
- 檢查結果: 
- 結論: 
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.5,
        max_tokens=500
    )

    return response.choices[0].message.content.strip()



