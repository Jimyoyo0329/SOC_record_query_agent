import pandas as pd
from sqlalchemy import create_engine, MetaData, Table, select, and_
from llm_utils import generate_note_from_example

# SQLite 位置，根據你的實際檔案路徑
SQLITE_PATH = "sqlite:///SOC.db"
TABLE_NAME = "SOC_data"  # 你的資料表名稱

# 建立連線
engine = create_engine(SQLITE_PATH)
metadata = MetaData()
alerts_table = Table(TABLE_NAME, metadata, autoload_with=engine)

def build_sql_filter(row: pd.Series, fields: list):
    """從 DataFrame Row 建立 SQL 條件"""
    conditions = []
    for field in fields:
        value = row.get(field)
        if pd.notna(value) and str(value).strip().lower() != "nan":
            conditions.append(alerts_table.c[field] == str(value).strip())
    return and_(*conditions) if conditions else None

def query_similar_records(row: pd.Series, top_k: int = 3):
    """從 SQLite 查詢與 row 欄位相符的記錄"""
    filter_fields = ["src_ip", "dest_ip", "dest_port", "domain"]
    condition = build_sql_filter(row, filter_fields)

    stmt = select(alerts_table)
    if condition is not None:
        stmt = stmt.where(condition)
    stmt = stmt.limit(top_k)

    with engine.connect() as conn:
        result = conn.execute(stmt)
        return [dict(r._mapping) for r in result]

def find_and_generate_note_from_sql(row: pd.Series, top_k=3):
    """查詢相符筆記並生成摘要"""
    matched_rows = query_similar_records(row, top_k=top_k)
    query_text = row.to_string()

    for match in matched_rows:
        note = match.get("note")
        if note:
            return generate_note_from_example(note, query_text)
    return "找不到相似的筆記來生成註解。"

def query_by_field(field_name: str, value: str):
    """通用欄位查詢：支援 src_ip、domain、dest_ip 等"""
    if not hasattr(alerts_table.c, field_name):
        raise ValueError(f"欄位 {field_name} 不存在於 SOC_data 資料表中。")

    stmt = select(alerts_table).where(alerts_table.c[field_name] == value)
    with engine.connect() as conn:
        result = conn.execute(stmt)
        return [dict(r._mapping) for r in result]

# 例用函式：查詢相同 alert.signature 的事件
def query_by_alert_signature(signature: str):
    return query_by_field("alert.signature", signature)

def query_by_src_ip(src_ip: str):
    return query_by_field("src_ip", src_ip)

def query_by_dest_ip(dest_ip: str):
    return query_by_field("dest_ip", dest_ip)

def query_by_domain(domain: str):
    return query_by_field("domain", domain)

def query_by_dest_port(dest_port: str):
    return query_by_field("dest_port", dest_port)

def query_by_src_port(src_port: str):
    return query_by_field("src_port", src_port)

def query_by_payload(note: str):
    return query_by_field("payload", note)

def query_by_note(note: str):
    return query_by_field("note", note)


def format_event_metadata(meta: dict) -> str:
    parts = [
        f"alert.signature: {meta.get('alert.signature', '(無)')}",
        f"Source IP: {meta.get('src_ip', 'N/A')}",
        f"Destination IP: {meta.get('dest_ip', 'N/A')}",
        f"Domain: {meta.get('domain', 'N/A')}",
        f"Destination Port: {meta.get('dest_port', 'N/A')}",
        f"Source Port: {meta.get('src_port', 'N/A')}",
        f"Timestamp: {meta.get('time', 'N/A')}",
        f"Payload: {meta.get('payload', '無')}",
        f"Note: {meta.get('note', '無')}",
    ]
    return "\n".join(parts)
