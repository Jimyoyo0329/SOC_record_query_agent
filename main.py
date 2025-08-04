import streamlit as st
import pandas as pd
from query import (
    find_and_generate_note,
    debug_query_with_details,
    query_by_alert_signature,
    format_event_metadata,
    query_by_src_ip,
    query_by_domain,
)
from llm_utils import generate_event_outline
from io import BytesIO

st.set_page_config(page_title="Alert Summarizer", layout="wide")
st.title("📊 多筆告警事件自動摘要")

uploaded_file = st.file_uploader("請上傳含多筆事件的 CSV 或 Excel 檔案", type=["csv", "xlsx"])


def load_uploaded_file(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    elif file.name.endswith(".xlsx"):
        return pd.read_excel(file)
    return None


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

    st.subheader("🔍 上傳事件預覽")
    st.dataframe(df)

    df["note"] = ""

    if st.button("🚀 開始比對與生成筆記（含除錯資訊）"):
        st.subheader("📌 生成結果")
        for idx, row in df.iterrows():
            with st.expander(f"第 {idx+1} 筆資料"):
                result, debug = debug_query_with_details(row)
                df.at[idx, "note"] = result

                st.markdown("#### ✅ 生成的 note")
                st.markdown(result)

                st.markdown("#### 🧪 查詢與相似度資訊")
                if "query_text" in debug:
                    st.code(debug["query_text"].replace(" | ", "\n"), language="text")
                else:
                    st.code(str(row), language="text")

                st.write(f"總相似度: `{debug.get('similarity', 0.0):.4f}`")

                if "source_meta" in debug:
                    meta = debug["source_meta"]
                    st.write("##### 各欄位相似度（若有嵌入）")
                    for key in ["ip", "domain", "query", "src_ip", "dest_ip"]:
                        score_key = f"{key}_score"
                        if score_key in meta:
                            st.write(f"- `{key}` 相似度: `{meta[score_key]:.4f}`")

                st.markdown("參考 note：")
                st.markdown(debug.get("example_note", "(無參考資料)"))

        st.subheader("⬇️ 下載含筆記的檔案")
        file_type = uploaded_file.name.split(".")[-1].lower()
        if file_type == "csv":
            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("📥 下載 CSV", data=csv, file_name="generated_notes.csv", mime="text/csv")
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
                "📥 下載 Excel",
                data=output.getvalue(),
                file_name="generated_notes.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    # 🚨 查詢按鈕區（獨立觸發）
    st.markdown("### 🔧 選擇查詢方式")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🚀 產生筆記"):
            st.session_state["start_generate"] = True

    with col2:
        if st.button("📚 alert_signature"):
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
            st.success("✅ alert_signature 查詢完成，請往下查看結果")

    with col3:
        if st.button("🌐 Domain"):
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
            st.success("✅ Domain 查詢完成，請往下查看結果")

    with col4:
        if st.button("📡 src_ip"):
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
            st.success("✅ src_ip 查詢完成，請往下查看結果")

    # --- 分隔線 & 結果呈現 ---

    # alert_signature 結果區
    if st.session_state.get("alert_sig_triggered") and st.session_state.get("alert_sig_results"):
        st.markdown("---")
        st.markdown("### 🧠 **Alert Signature 查詢結果**")
        for idx, result in st.session_state["alert_sig_results"].items():
            alert_sig = result["alert_sig"]
            all_metadata = result["metadata"]
            with st.expander(f"📌 第 {idx+1} 筆事件: {alert_sig}"):
                if not all_metadata:
                    st.warning("查無相符的事件")
                    continue
                st.markdown(f"共找到 **{len(all_metadata)}** 筆相同 alert 的歷史事件：")
                for i, meta in enumerate(all_metadata):
                    metadata_text = format_event_metadata(meta)
                    outline = generate_event_outline(metadata_text)
                    st.markdown(f"---\n#### ✅ 第 {i+1} 筆事件摘要")
                    st.code(metadata_text, language="text")
                    st.markdown(outline)

    # domain 結果區
    if st.session_state.get("domain_triggered") and st.session_state.get("domain_results"):
        st.markdown("---")
        st.markdown("### 🌐 **Domain 查詢結果**")
        for idx, result in st.session_state["domain_results"].items():
            domain = result["domain"]
            all_metadata = result["metadata"]
            with st.expander(f"📌 第 {idx+1} 筆事件 Domain: {domain}"):
                if not all_metadata:
                    st.warning("查無相符的事件")
                    continue
                st.markdown(f"共找到 **{len(all_metadata)}** 筆相同 Domain 的歷史事件：")
                for i, meta in enumerate(all_metadata):
                    metadata_text = format_event_metadata(meta)
                    outline = generate_event_outline(metadata_text)
                    st.markdown(f"---\n#### ✅ 第 {i+1} 筆事件摘要")
                    st.code(metadata_text, language="text")
                    st.markdown(outline)

    # src_ip 結果區
    if st.session_state.get("src_ip_triggered") and st.session_state.get("src_ip_results"):
        st.markdown("---")
        st.markdown("### 📡 **Source IP 查詢結果**")
        for idx, result in st.session_state["src_ip_results"].items():
            src_ip = result["src_ip"]
            all_metadata = result["metadata"]
            with st.expander(f"📌 第 {idx+1} 筆事件 Source IP: {src_ip}"):
                if not all_metadata:
                    st.warning("查無相符的事件")
                    continue
                st.markdown(f"共找到 **{len(all_metadata)}** 筆相同 src_ip 的歷史事件：")
                for i, meta in enumerate(all_metadata):
                    metadata_text = format_event_metadata(meta)
                    outline = generate_event_outline(metadata_text)
                    st.markdown(f"---\n#### ✅ 第 {i+1} 筆事件摘要")
                    st.code(metadata_text, language="text")
                    st.markdown(outline)
