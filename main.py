import streamlit as st
import pandas as pd
from query import find_and_generate_note, debug_query_note, debug_query_with_details
from io import BytesIO

st.set_page_config(page_title="Threat Note Generator", layout="wide")
st.title("⚠️ 資安告警筆記自動生成器")

uploaded_file = st.file_uploader("請上傳一筆新的 CSV 或 Excel 檔案", type=["csv", "xlsx"])

def load_uploaded_file(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    elif file.name.endswith(".xlsx"):
        return pd.read_excel(file)
    return None

if uploaded_file:
    new_data = load_uploaded_file(uploaded_file)
    if new_data is not None:
        # 將物件欄位全部轉成字串，避免 NaN 等影響查詢
        for col in new_data.columns:
            if new_data[col].dtype == "object":
                new_data[col] = new_data[col].astype(str)

        st.subheader("🔎 預覽上傳內容")
        st.dataframe(new_data)

        # 新增空 note 欄位，用來存結果
        new_data["note"] = ""

        if st.button("🚀 開始比對與生成筆記（含除錯資訊）"):
            st.subheader("📌 生成結果")

            for idx, row in new_data.iterrows():
                with st.expander(f"第 {idx+1} 筆資料"):
                    # 產生結果與 debug dict
                    result, debug = debug_query_with_details(row)

                    # 更新 DataFrame note 欄位
                    new_data.at[idx, "note"] = result

                    st.markdown("#### ✅ 生成的 note")
                    st.markdown(result)

                    st.markdown("#### 🧪 查詢與相似度資訊")
                    if "query_text" in debug:
                        # 格式化 query_text 讓它每個欄位換行，方便閱讀
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

            # 下載區塊
            st.subheader("⬇️ 下載含筆記的檔案")

            file_type = uploaded_file.name.split(".")[-1].lower()
            if file_type == "csv":
                csv = new_data.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "📥 下載 CSV",
                    data=csv,
                    file_name="generated_notes.csv",
                    mime="text/csv"
                )
            else:
                output = BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    new_data.to_excel(writer, index=False, sheet_name="Results")

                    workbook = writer.book
                    worksheet = writer.sheets["Results"]

                    center_format = workbook.add_format({
                        "align": "center",
                        "valign": "vcenter"
                    })
                    wrap_format = workbook.add_format({
                        "text_wrap": True,
                        "valign": "top",
                        "align": "center"
                    })

                    for col_idx, col_name in enumerate(new_data.columns):
                        if col_name == "note":
                            worksheet.set_column(col_idx, col_idx, 50, wrap_format)
                        else:
                            worksheet.set_column(col_idx, col_idx, 20, center_format)

                    for row_num in range(1, len(new_data) + 1):
                        worksheet.set_row(row_num, 80)

                st.download_button(
                    "📥 下載 Excel",
                    data=output.getvalue(),
                    file_name="generated_notes.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
