import os
import re
from typing import List
from sqlalchemy import inspect  
from openai import OpenAI
from langchain_community.utilities.sql_database import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_chroma import Chroma
from langchain.chat_models import ChatOpenAI
from rag_model.embedding_utils import MyEmbedding
from langchain.chains.llm import LLMChain
from langchain_core.prompts import PromptTemplate

# ==== 設定 ====
CHROMA_PATH = os.path.abspath("data2")
SQLITE_PATH = "sqlite:///SOC.db"
### 如果要公開要記得把key 放到環境變數
OPENAI_API_KEY = "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"
TOP_K = 4

# ==== 初始化 ====
client = OpenAI(api_key=OPENAI_API_KEY)
llm = ChatOpenAI(model_name="gpt-4o", temperature=0, openai_api_key=OPENAI_API_KEY)
embedding = MyEmbedding()
vectorstore = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding)
sql_db = SQLDatabase.from_uri(SQLITE_PATH)

# ==== 取得欄位名稱 ====
def get_column_names(db: SQLDatabase, table_name: str) -> List[str]:
    inspector = inspect(db._engine)
    columns = inspector.get_columns(table_name)
    return [col["name"] for col in columns]

# ==== SQL Prompt ====
sql_prompt = PromptTemplate.from_template("""
你是一位資安資料庫分析師，請根據使用者問題產出 SQLite 查詢語法。
⚠️ 規則：
1. 只能使用SELECT，不要使用其他語法。。
2. 若使用者有明確指定欄位名稱，請只查詢那些欄位。
3. 請使用 SQLite 語法。
4. 僅回傳 SQL 查詢語法，不要加上說明或格式標記。
                                          
使用者問題：{question}
資料庫結構：
{schema}

請產出查詢語法：
""")

schema = sql_db.get_table_info()
sql_chain = LLMChain(llm=llm, prompt=sql_prompt)

# ==== 清理 SQL 查詢 ====
def clean_sql_query(raw_sql: str) -> str:
    raw_sql = raw_sql.strip()
    raw_sql = re.sub(r"^```(?:sqlite|sql)?\s*", "", raw_sql, flags=re.IGNORECASE)
    raw_sql = re.sub(r"\s*```$", "", raw_sql, flags=re.IGNORECASE)
    raw_sql = re.sub(r"^SQLQuery[:：]\s*", "", raw_sql, flags=re.IGNORECASE)
    raw_sql = raw_sql.splitlines()[0].strip()
    if not raw_sql.endswith(";"):
        raw_sql += ";"
    return raw_sql

# ==== 產出摘要與異同比較 ====
def summarize_rows(rows: List[tuple], columns: List[str], user_query: str):
    summaries = []
    for idx, row in enumerate(rows, 1):
        metadata = dict(zip(columns, row)) if columns else {f"col{i}": v for i, v in enumerate(row)}
        raw_info = "\n".join([f"- {k}: {v if v else '無資料'}" for k, v in metadata.items()])
        user_prompt = f"""
        【第 {idx} 筆事件摘要】

        【使用者問題】
        {user_query}

        【事件資料】
        {raw_info}

        請產出結構化摘要，讓內容清晰易讀，不要加入其他說明。
        """
        system_prompt = """
            你是一位資安分析師，請根據提供的事件資料產出清晰且結構化的摘要報告。  
            ⚠️ 規則：  
            1. 根據資料欄位名稱及其對應值動態生成摘要，不要硬套欄位名稱。  
            2. 每筆事件請前置標題：【第 N 筆事件摘要】。  
            3. 輸出結果精簡越好，避免冗長描述。
            4. 若資料中包含「note」或類似備註欄位，請使用以下格式產生事件背景與事件大綱：  
            【第 N 筆事件摘要】  
            ### 事件背景
            - 時間: ...（若有）  
            - 告警名稱: ...（若有）  
            - 來源 IP: ...（若有）  
            - 目的 IP: ...（若有）  
            - 相關網域: ...（若有）  

            ### 事件大綱
            - 負責人員或單位: （若從備註中可提取）
            - 事件概述: （摘取備註的主要描述）
            - 檢查結果: （若有）
            - 結論: （根據備註內容合理推論。若備註提及已關閉、非惡意、工作開發等情況，可提出推測結論；若無明確線索，請省略。）  

            5. 若資料中沒有「note」或類似備註欄位，請直接以簡潔的條列式格式列出所有欄位名稱與其對應值，不用套用事件背景和事件大綱格式。


        """
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
                    {"role": "user", "content": [{"type": "text", "text": user_prompt}]}
                ],
                temperature=0.1,
                max_tokens=500
            )
            summary = response.choices[0].message.content.strip()
            summaries.append(summary)
        except Exception as e:
            summaries.append(f"❌ 第 {idx} 筆摘要失敗：{e}")

    # 比較
    if len(summaries) >= 2:
        summary_text = "\n".join([f"第{i+1}筆：\n{s}" for i, s in enumerate(summaries)])
        comparison_prompt = f"""
        【使用者問題】
        {user_query}

        【事件摘要】
        {summary_text}

        請協助比較這些事件的異同，規則如下：
        1. 先將多筆資料用表格方式呈現
        2. 請產出條列式說明
         - 共同點
         - 不同點
        """
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": [{"type": "text", "text": "你是一位資安分析師，請針對多筆事件進行比較。"}]},
                    {"role": "user", "content": [{"type": "text", "text": comparison_prompt}]}
                ],
                temperature=0.5,
                max_tokens=800
            )
            result = response.choices[0].message.content.strip()
            summaries.append(result)
        except Exception as e:
            summaries.append(f"❌ 事件比較失敗：{e}")
    return summaries

# ==== 向量查詢 fallback ====
def vector_fallback_search(query: str) -> List[str]:
    docs = vectorstore.similarity_search(query, k=TOP_K)
    return [doc.page_content for doc in docs]

# ==== 主查詢流程 ====
def dual_query(user_query: str):
    print(f"\n🔧 使用者原始查詢語句：\n{user_query}\n")

    try:
        raw_sql_result = sql_chain.invoke({"question": user_query, "schema": schema})
        raw_sql_query = raw_sql_result["text"]
        print(f"\n🧠 清理前的 SQL 查詢語法：\n{raw_sql_query}\n")
        sql_query = clean_sql_query(raw_sql_query)
        print(f"\n🧠 清理後的 SQL 查詢語法：\n{sql_query}\n") 

        result = sql_db.run(sql_query)
        print(f"\n📦 SQL 查詢結果原始輸出：\n{result}\n")

        if isinstance(result, str):
            try:
                result = eval(result)
                print("📦 SQL 查詢結果已轉換為 list")
            except Exception as e:
                print("⚠️ SQL 查詢結果無法解析：", e)
                raise ValueError("SQL 查詢無資料")

        if not isinstance(result, list) or not all(isinstance(row, tuple) for row in result):
            print("⚠️ SQL 查詢結果格式異常：", result)
            raise ValueError("SQL 查詢無資料")

        print(f"\n✅ 查詢成功，共取得 {len(result)} 筆資料。\n")

        # ✅ 使用 SQLAlchemy inspector 抓欄位名稱
        table_names = re.findall(r"FROM\s+([^\s;]+)", sql_query, flags=re.IGNORECASE)
        table_name = table_names[0] if table_names else None
        cols = get_column_names(sql_db, table_name) if table_name else []

        # ✅ 輸出欄位與第一筆資料
        if result:
            print("👉 欄位:", cols)
            print("👉 第一筆資料:", result[0])
        else:
            print("👉 查無資料")

        summaries = summarize_rows(result, cols, user_query)
        if summaries:
            print("已完成大綱")
            print(summaries)
        return "\n\n---\n\n".join(summaries)

    except Exception as e:
        print(f"\n⚠️ SQL 查詢失敗：{e}\n")
        docs = vector_fallback_search(user_query)
        return docs if docs else ["❌ 查無結果"]

