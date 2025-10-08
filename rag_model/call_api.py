from openai import OpenAI
api_key = "KEY"

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
