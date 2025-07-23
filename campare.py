import pandas as pd
from utils import row_to_text, dataframe_to_texts

def compare_texts(df: pd.DataFrame, index: int):
    # 存入時用的文本（dataframe_to_texts 會批次轉換）
    texts = dataframe_to_texts(df)
    stored_text = texts[index]

    # 查詢時用的文本 (用 row_to_text 一筆比對)
    query_text = row_to_text(df.iloc[index])

    print(f"--- Index {index} 原始資料欄位 ---")
    print(df.iloc[index])
    print("\n--- 存入資料庫的文本 (dataframe_to_texts) ---")
    print(stored_text)
    print("\n--- 查詢時用的文本 (row_to_text) ---")
    print(query_text)

    if stored_text == query_text:
        print("\n✅ 兩者文本完全相同！")
    else:
        print("\n❌ 兩者文本不相同！")
        # 簡單顯示差異位置 (逐字比較)
        for i, (c1, c2) in enumerate(zip(stored_text, query_text)):
            if c1 != c2:
                print(f"差異字元在位置 {i}: 存入='{c1}' vs 查詢='{c2}'")
                break
        if len(stored_text) != len(query_text):
            print(f"兩文本長度不同：存入長度={len(stored_text)}，查詢長度={len(query_text)}")

# 範例用法：
if __name__ == "__main__":
    # 讀取原始資料（CSV/Excel）
    df = pd.read_excel("data_0721.xlsx")  # 或 pd.read_excel("your_file.xlsx")

    compare_texts(df, index=0)  # 比對第0筆資料
