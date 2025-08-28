import pandas as pd
import sqlite3
import os

EXCEL_FILE = "data_0721.xlsx"           # 你的 Excel 檔案名稱
DB_FILE = "SOC.db"                # 要建立的 SQLite 檔案
TABLE_NAME = "SOC_data"                # 資料表名稱

def create_sqlite_from_excel_all_text(excel_file: str, db_file: str, table_name: str):
    # 讀取 Excel
    df = pd.read_excel(excel_file, dtype=str)  # 強制所有欄位轉為文字
    df.fillna("", inplace=True)                # 將空值補成空字串

    # 刪除舊的資料庫（如果有）
    if os.path.exists(db_file):
        os.remove(db_file)

    # 連接 SQLite 並建立資料表
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # 建立 CREATE TABLE 語句（全部欄位 TEXT）
    columns = [f'"{col}" TEXT' for col in df.columns]
    create_sql = f'CREATE TABLE "{table_name}" ({", ".join(columns)});'
    cursor.execute(create_sql)

    # 插入資料
    insert_sql = f'INSERT INTO "{table_name}" VALUES ({", ".join(["?" for _ in df.columns])});'
    for row in df.itertuples(index=False):
        cursor.execute(insert_sql, tuple(row))

    conn.commit()
    conn.close()

    print(f"✅ 成功將 `{excel_file}` 寫入 `{db_file}`，表格 `{table_name}`，所有欄位皆為 TEXT")

if __name__ == "__main__":
    create_sqlite_from_excel_all_text(EXCEL_FILE, DB_FILE, TABLE_NAME)
