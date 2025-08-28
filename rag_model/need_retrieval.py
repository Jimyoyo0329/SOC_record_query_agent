from rag_model.call_api import call_gpt_api

def need_retrieval(user_input: str) -> bool:
    system_prompt = """
你是一個助理，負責判斷使用者的問題是否需要從資料庫中檢索過往相似或相同事件資料。
相似事件資料通常包含以下欄位：來源 IP、目的 IP、Alert signature、domain、payload、note、告警等。
使用者的問題可能會明確提到這些欄位，也可能以隱含方式詢問相關事件
例如:
- 幫我查詢有關某某某的所有資料
- 有關 Suspicious domain reqres.in has been detected! 的資料
- 請幫我找出來源 IP 是 10.0.0.1 的所有事件
- 幫我列出時間最近的n筆資料
等等。

請根據使用者的問題內容，判斷是否需要查詢事件資料。
回答格式僅限：「YES」或「NO」

"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    response = call_gpt_api(messages)
    answer = response.content.strip().lower()
    return answer.startswith("是") or answer.startswith("yes")