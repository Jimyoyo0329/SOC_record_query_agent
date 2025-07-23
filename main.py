import streamlit as st
import pandas as pd
from query import find_and_generate_note, debug_query_note
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
        # ✅ 解法1通用版：將所有 object 型欄位轉為字串，避免 Arrow 轉換錯誤
        for col in new_data.columns:
            if new_data[col].dtype == "object":
                new_data[col] = new_data[col].astype(str)

        st.subheader("🔎 預覽上傳內容")
        st.dataframe(new_data)

        # 建立空欄位存放生成的 note
        new_data["note"] = ""

        if st.button("🚀 開始比對與生成筆記（含除錯資訊）"):
            st.subheader("📌 生成結果")
            
            for idx, row in new_data.iterrows():
                with st.expander(f"第 {idx+1} 筆"):
                    result, debug = debug_query_note(row)
                
                    new_data.at[idx, "note"] = result

                    st.markdown("#### ✅ 生成的 note")
                    st.markdown(result)

                    # Bonus：把 " | " 轉換成換行，更容易閱讀
                    pretty_query_text = debug["query_text"].replace(" | ", "\n")

                    st.markdown("#### 🧪 相似度與參考資料")
                    st.code(pretty_query_text, language="text")
                    st.write(f"相似度: `{debug['similarity']:.4f}`")
                    st.markdown("參考 note：")
                    st.markdown(debug["example_note"])

            # 檔案轉成可下載格式
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

                    # 格式：水平、垂直置中
                    center_format = workbook.add_format({
                        "align": "center",
                        "valign": "vcenter"
                    })

                    # 格式：note 欄自動換行、垂直靠上、水平置中
                    wrap_format = workbook.add_format({
                        "text_wrap": True,
                        "valign": "top",
                        "align": "center"
                    })

                    # 設定欄寬與格式
                    for col_idx, col_name in enumerate(new_data.columns):
                        if col_name == "note":
                            worksheet.set_column(col_idx, col_idx, 50, wrap_format)
                        else:
                            worksheet.set_column(col_idx, col_idx, 20, center_format)

                    # 設定列高 (跳過表頭列)
                    for row_num in range(1, len(new_data) + 1):
                        worksheet.set_row(row_num, 80)

                st.download_button(
                    "📥 下載 Excel",
                    data=output.getvalue(),
                    file_name="generated_notes.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
