# query.py

import pandas as pd
from chromadb import PersistentClient
from embedding import load_embedding_model, embed_texts
from utils import row_to_text
from llm_utils import generate_note_from_example

CHROMA_DIR = "data/chroma_db"

def get_chroma_client():
    print(f"📁 使用的 Chroma 資料夾: {CHROMA_DIR}")
    return PersistentClient(path=CHROMA_DIR)

# ✅ 通用查詢邏輯
def query_similar_notes(row: pd.Series, top_k=3):
    query_text = row_to_text(row)
    embedding_model = load_embedding_model()
    query_vector = embed_texts(embedding_model, [query_text])[0].tolist()

    client = get_chroma_client()
    collection = client.get_collection(name="alerts")

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    return query_text, results

# ✅ 實際使用筆記（不回傳 debug 訊息）
def find_and_generate_note(new_row: pd.Series, top_k=3, threshold=0.5) -> str:
    query_text, results = query_similar_notes(new_row, top_k)

    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        similarity = 1 - dist
        if similarity >= threshold and "note" in meta and meta["note"]:
            return generate_note_from_example(meta["note"], query_text)

    return "⚠️ 找不到相似的筆記來生成註解。"

# ✅ 用於 debug 顯示詳情
def debug_query_note(new_row: pd.Series, top_k=3, threshold=0.3):
    query_text, results = query_similar_notes(new_row, top_k)
    print(f"[Query Text]: {query_text}")

    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        similarity = 1 - dist
        print(f"Doc: {doc[:30]}... Similarity: {similarity:.4f} Note: {meta.get('note', '')[:30]}...")  # 印出部分內容，避免太長
        if similarity >= threshold and "note" in meta and meta["note"]:
            example_note = meta["note"]
            new_note = generate_note_from_example(example_note, query_text)
            return new_note, {
                "query_text": query_text,
                "similarity": similarity,
                "example_note": example_note,
            }

    return "⚠️ 無法找到足夠相似的筆記來生成註解。", {
        "query_text": query_text,
        "similarity": 0.0,
        "example_note": "(無匹配資料)"
    }
