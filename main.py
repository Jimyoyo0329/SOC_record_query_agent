import streamlit as st
import pandas as pd
from query import (find_and_generate_note_from_sql, 
                   query_by_alert_signature, 
                   query_by_domain, 
                   query_by_src_ip,
                   query_by_dest_ip,
                   query_by_dest_port,
                   query_by_src_port,
                   query_by_payload,
                   query_by_note,
                   format_event_metadata)                  
from llm_utils import generate_event_outline, generate_outline_from_table
from rag_model.call_api import call_gpt_api
from rag_model.need_retrieval import need_retrieval
from io import BytesIO
#from new_rag import *
from rag_model.rag_core import dual_query

st.set_page_config(page_title="SOC_record_query_agent", layout="wide")

def load_uploaded_file(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    elif file.name.endswith(".xlsx"):
        return pd.read_excel(file)
    return None


st.title("SOC 安全事件問答 AI")

uploaded_file = st.file_uploader("請上傳 SOC 事件檔案（CSV 或 Excel）", type=["csv", "xlsx"])

# === 多筆事件根據欄位過濾一鍵生成備註區塊 ===
if uploaded_file:
    # 初始化 session_state 查詢結果與觸發旗標
    if "domain_results" not in st.session_state:
        st.session_state["domain_results"] = {}
    if "src_ip_results" not in st.session_state:
        st.session_state["src_ip_results"] = {}
    if "alert_sig_results" not in st.session_state:
        st.session_state["alert_sig_results"] = {}

    if "alert_sig_triggered" not in st.session_state:
        st.session_state["alert_sig_triggered"] = False
    if "domain_triggered" not in st.session_state:
        st.session_state["domain_triggered"] = False
    if "src_ip_triggered" not in st.session_state:
        st.session_state["src_ip_triggered"] = False

    df = load_uploaded_file(uploaded_file)

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str)

    st.subheader("上傳事件預覽")
    st.dataframe(df)

    df["note"] = ""

    if st.button("產生筆記"):
        st.subheader("生成結果")
        for idx, row in df.iterrows():
            with st.expander(f"第 {idx+1} 筆資料"):
                result = find_and_generate_note_from_sql(row)
                df.at[idx, "note"] = result

                st.markdown("#### 生成的 Note")
                st.markdown(result)

                st.markdown("#### 原始資料")
                st.code(row.to_string(), language="text")

        st.subheader("下載含筆記的檔案")
        file_type = uploaded_file.name.split(".")[-1].lower()
        if file_type == "csv":
            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("下載 CSV", data=csv, file_name="generated_notes.csv", mime="text/csv")
        else:
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="Results")
                workbook = writer.book
                worksheet = writer.sheets["Results"]
                center_format = workbook.add_format({"align": "center", "valign": "vcenter"})
                wrap_format = workbook.add_format({"text_wrap": True, "valign": "top", "align": "center"})
                for col_idx, col_name in enumerate(df.columns):
                    if col_name == "note":
                        worksheet.set_column(col_idx, col_idx, 50, wrap_format)
                    else:
                        worksheet.set_column(col_idx, col_idx, 20, center_format)
                for row_num in range(1, len(df) + 1):
                    worksheet.set_row(row_num, 80)
            st.download_button(
                "下載 Excel",
                data=output.getvalue(),
                file_name="generated_notes.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    # 查詢按鈕區
    st.markdown("### 選擇要使用哪個欄位進行過往紀錄查詢")
    col1, col2, col3, col4, col5, col6, col7  = st.columns(7)

    with col1:
        if st.button("alert_signature"):
            st.session_state["alert_sig_triggered"] = True
            st.session_state["alert_sig_results"] = {}
            for idx, row in df.iterrows():
                alert_sig = row.get("alert.signature", "").strip()
                if not alert_sig:
                    continue
                all_metadata = query_by_alert_signature(alert_sig)
                st.session_state["alert_sig_results"][idx] = {
                    "alert_sig": alert_sig,
                    "metadata": all_metadata,
                }
            st.success("alert_signature 查詢完成")

    with col2:
        if st.button("domain"):
            st.session_state["domain_triggered"] = True
            st.session_state["domain_results"] = {}
            for idx, row in df.iterrows():
                domain = row.get("domain", "").strip()
                if not domain:
                    continue
                all_metadata = query_by_domain(domain)
                st.session_state["domain_results"][idx] = {
                    "domain": domain,
                    "metadata": all_metadata,
                }
            st.success("Domain 查詢完成")

    with col3:
        if st.button("src_ip"):
            st.session_state["src_ip_triggered"] = True
            st.session_state["src_ip_results"] = {}
            for idx, row in df.iterrows():
                src_ip = row.get("src_ip", "").strip()
                if not src_ip:
                    continue
                all_metadata = query_by_src_ip(src_ip)
                st.session_state["src_ip_results"][idx] = {
                    "src_ip": src_ip,
                    "metadata": all_metadata,
                }
            st.success("src_ip 查詢完成")

    with col4:
        if st.button("dest_ip"):
            st.session_state["dest_ip_triggered"] = True
            st.session_state["dest_ip_results"] = {}
            for idx, row in df.iterrows():
                dest_ip = row.get("dest_ip", "").strip()
                if not dest_ip:
                    continue
                all_metadata = query_by_dest_ip(dest_ip)
                st.session_state["dest_ip_results"][idx] = {
                    "dest_ip": dest_ip,
                    "metadata": all_metadata,
                }
            st.success("dest_ip 查詢完成")

    with col5:
        if st.button("dest_port"):
            st.session_state["dest_port_triggered"] = True
            st.session_state["dest_port_results"] = {}
            for idx, row in df.iterrows():
                dest_port = row.get("dest_port", "").strip()
                if not dest_port:
                    continue
                all_metadata = query_by_dest_port(dest_port)
                st.session_state["dest_port_results"][idx] = {
                    "dest_port": dest_port,
                    "metadata": all_metadata,
                }
            st.success("dest_port 查詢完成")

    with col6:
        if st.button("src_port"):
            st.session_state["src_port_triggered"] = True
            st.session_state["src_port_results"] = {}
            for idx, row in df.iterrows():
                src_port = row.get("src_port", "").strip()
                if not src_port:
                    continue
                all_metadata = query_by_src_port(src_port)
                st.session_state["src_port_results"][idx] = {
                    "src_port": src_port,
                    "metadata": all_metadata,
                }
            st.success("src_port 查詢完成")
    with col7:
        if st.button("payload"):
            st.session_state["payload_triggered"] = True
            st.session_state["payload_results"] = {}
            for idx, row in df.iterrows():
                payload = row.get("payload", "").strip()
                if not payload:
                    continue
                all_metadata = query_by_payload(payload)
                st.session_state["payload_results"][idx] = {
                    "payload": payload,
                    "metadata": all_metadata,
                }
            st.success("payload 查詢完成")

    # 顯示查詢結果
    

    if st.session_state.get("alert_sig_triggered") and st.session_state.get("alert_sig_results"):
        st.markdown("---")
        st.markdown("### Alert Signature 查詢結果")
        for idx, result in st.session_state["alert_sig_results"].items():
            alert_sig = result["alert_sig"]
            all_metadata = result["metadata"]
            with st.expander(f"第 {idx+1} 筆事件: {alert_sig}"):
                if not all_metadata:
                    st.warning("查無相符的事件")
                    continue
                st.markdown(f"共找到 {len(all_metadata)} 筆事件：")
                for i, meta in enumerate(all_metadata):
                    metadata_text = format_event_metadata(meta)
                    outline = generate_event_outline(metadata_text)
                    st.markdown(f"---\n#### 第 {i+1} 筆事件摘要")
                    st.code(metadata_text, language="text")
                    st.markdown(outline)

    if st.session_state.get("domain_triggered") and st.session_state.get("domain_results"):
        st.markdown("---")
        st.markdown("### Domain 查詢結果")
        for idx, result in st.session_state["domain_results"].items():
            domain = result["domain"]
            all_metadata = result["metadata"]
            with st.expander(f"第 {idx+1} 筆事件 Domain: {domain}"):
                if not all_metadata:
                    st.warning("查無相符的事件")
                    continue
                st.markdown(f"共找到 {len(all_metadata)} 筆事件：")
                for i, meta in enumerate(all_metadata):
                    metadata_text = format_event_metadata(meta)
                    outline = generate_event_outline(metadata_text)
                    st.markdown(f"---\n#### 第 {i+1} 筆事件摘要")
                    st.code(metadata_text, language="text")
                    st.markdown(outline)

    if st.session_state.get("src_ip_triggered") and st.session_state.get("src_ip_results"):
        st.markdown("---")
        st.markdown("### Source IP 查詢結果")
        for idx, result in st.session_state["src_ip_results"].items():
            src_ip = result["src_ip"]
            all_metadata = result["metadata"]
            with st.expander(f"第 {idx+1} 筆事件 Source IP: {src_ip}"):
                if not all_metadata:
                    st.warning("查無相符的事件")
                    continue
                st.markdown(f"共找到 {len(all_metadata)} 筆事件：")
                for i, meta in enumerate(all_metadata):
                    metadata_text = format_event_metadata(meta)
                    outline = generate_event_outline(metadata_text)
                    st.markdown(f"---\n#### 第 {i+1} 筆事件摘要")
                    st.code(metadata_text, language="text")
                    st.markdown(outline)
    
    if st.session_state.get("dest_ip_triggered") and st.session_state.get("dest_ip_results"):
        st.markdown("---")
        st.markdown("### Destination IP 查詢結果")
        for idx, result in st.session_state["dest_ip_results"].items():
            dest_ip = result["dest_ip"]
            all_metadata = result["metadata"]
            with st.expander(f"第 {idx+1} 筆事件 Destination IP: {dest_ip}"):
                if not all_metadata:
                    st.warning("查無相符的事件")
                    continue
                st.markdown(f"共找到 {len(all_metadata)} 筆事件：")
                for i, meta in enumerate(all_metadata):
                    metadata_text = format_event_metadata(meta)
                    outline = generate_event_outline(metadata_text)
                    st.markdown(f"---\n#### 第 {i+1} 筆事件摘要")
                    st.code(metadata_text, language="text")
                    st.markdown(outline)
    if st.session_state.get("dest_port_triggered") and st.session_state.get("dest_port_results"):
        st.markdown("---")
        st.markdown("### Destination Port 查詢結果")
        for idx, result in st.session_state["dest_port_results"].items():
            dest_port = result["dest_port"]
            all_metadata = result["metadata"]
            with st.expander(f"第 {idx+1} 筆事件 Destination Port: {dest_port}"):
                if not all_metadata:
                    st.warning("查無相符的事件")
                    continue
                st.markdown(f"共找到 {len(all_metadata)} 筆事件：")
                for i, meta in enumerate(all_metadata):
                    metadata_text = format_event_metadata(meta)
                    outline = generate_event_outline(metadata_text)
                    st.markdown(f"---\n#### 第 {i+1} 筆事件摘要")
                    st.code(metadata_text, language="text")
                    st.markdown(outline)
    if st.session_state.get("src_port_triggered") and st.session_state.get("src_port_results"):
        st.markdown("---")
        st.markdown("### Source Port 查詢結果")
        for idx, result in st.session_state["src_port_results"].items():
            src_port = result["src_port"]
            all_metadata = result["metadata"]
            with st.expander(f"第 {idx+1} 筆事件 Source Port: {src_port}"):
                if not all_metadata:
                    st.warning("查無相符的事件")
                    continue
                st.markdown(f"共找到 {len(all_metadata)} 筆事件：")
                for i, meta in enumerate(all_metadata):
                    metadata_text = format_event_metadata(meta)
                    outline = generate_event_outline(metadata_text)
                    st.markdown(f"---\n#### 第 {i+1} 筆事件摘要")
                    st.code(metadata_text, language="text")
                    st.markdown(outline)

    if st.session_state.get("payload_triggered") and st.session_state.get("payload_results"): 
        st.markdown("---")
        st.markdown("### Payload 查詢結果")
        for idx, result in st.session_state["payload_results"].items():
            payload = result["payload"]
            all_metadata = result["metadata"]
            with st.expander(f"第 {idx+1} 筆事件 Payload: {payload}"):
                if not all_metadata:
                    st.warning("查無相符的事件")
                    continue
                st.markdown(f"共找到 {len(all_metadata)} 筆事件：")
                for i, meta in enumerate(all_metadata):
                    metadata_text = format_event_metadata(meta)
                    outline = generate_event_outline(metadata_text)
                    st.markdown(f"---\n#### 第 {i+1} 筆事件摘要")
                    st.code(metadata_text, language="text")
                    st.markdown(outline)
# === 多筆事件，根據欄位過濾，一鍵生成備註區塊 ===



# === RAG 持續對話區塊 ===
st.markdown("---")
st.markdown("## 💬 RAG 問答（多輪對話模式）")

if "rag_chat_history" not in st.session_state:
    st.session_state["rag_chat_history"] = []



def handle_user_query():
    query = st.session_state["rag_user_input"].strip()
    if not query:
        return

    # 加入使用者問題到對話紀錄
    st.session_state["rag_chat_history"].append({"role": "user", "content": query})

    # 🔍 判斷是否需要查資料
    if need_retrieval(query):
        print("🔍 需要資料檢索，開始提取實體與 smart_query")

        # 从 rag.py 调用 dual_query 函数进行查询，并得到摘要结果
        assistant_reply = dual_query(query)
        
        if not assistant_reply:
            assistant_reply = "❌ 查無相似事件，請嘗試其他問題。"
    else:
        print("💬 不需資料檢索，走一般 GPT 問答")
        system_prompt = "你是一位資安分析師，根據上下文回答使用者的問題，如果不是IT、資安的問題、網路等資訊議題，請回答你不知道。"
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(st.session_state["rag_chat_history"][-6:])
        messages.append({"role": "user", "content": query})

        # 调用 GPT API 获取回复（根据实际需要，你可能需要自定义该函数）
        response = call_gpt_api(messages)
        assistant_reply = response.content.strip()

    # 加入 AI 回覆到對話歷史
    st.session_state["rag_chat_history"].append({"role": "assistant", "content": assistant_reply})
    st.session_state["rag_user_input"] = ""  # 清空用户输入框



# ✅ 使用 chat_input 固定在畫面底部
user_input = st.chat_input("請輸入你的問題")
if user_input:
    st.session_state["rag_user_input"] = user_input
    handle_user_query()

col_reset, _ = st.columns([1, 5])
with col_reset:
    if st.button("🗑️ 清除對話"):
        st.session_state["rag_chat_history"] = []
        # 不用改 rag_user_input，清空輸入框會自動處理

if st.session_state["rag_chat_history"]:
    st.markdown("### 🧠 對話紀錄")
    for i, msg in enumerate(st.session_state["rag_chat_history"]):
        role = " 使用者" if msg["role"] == "user" else " AI回覆"
        with st.chat_message(msg["role"]):
            st.markdown(f"**{role}**：\n\n{msg['content']}", unsafe_allow_html=True)


