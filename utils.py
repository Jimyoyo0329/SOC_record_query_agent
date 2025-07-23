# utils.py

import pandas as pd

# 將每一列轉換成純文字格式，排除 'time' 欄
def row_to_text(row: pd.Series) -> str:
    parts = []
    for col, val in row.items():
        if col == "time":
            continue
        if pd.isna(val):
            val_str = ""
        else:
            val_str = str(val).strip()
        parts.append(f"{col}: {val_str}")
    return " | ".join(parts)

# 批次轉換整個 DataFrame
def dataframe_to_texts(df: pd.DataFrame) -> list:
    return [row_to_text(row) for _, row in df.iterrows()]
