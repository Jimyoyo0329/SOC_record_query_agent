from openai import OpenAI
api_key = "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"

# 初始化 OpenAI 客戶端
client = OpenAI(api_key=api_key)

def call_gpt_api(messages):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7,
        max_tokens=800,
    )
    return response.choices[0].message