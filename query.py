import pandas as pd
from chromadb import PersistentClient
from embedding import load_embedding_model, embed_texts
from utils import row_to_text
from llm_utils import generate_note_from_example

CHROMA_DIR = "data/chroma_db"

def get_chroma_client():
    print(f"📁 使用的 Chroma 資料夾: {CHROMA_DIR}")
    return PersistentClient(path=CHROMA_DIR)

def build_metadata_filter(row: pd.Series, fields: list) -> dict:
    conditions = []
    for f in fields:
        val = row.get(f)
        if val is not None:
            val_str = str(val).strip()
            # 過濾空值與 NaN 字串
            if val_str != "" and val_str.lower() != "nan":
                conditions.append({f: val_str})
    if not conditions:
        return {}
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}

def query_similar_notes(row: pd.Series, top_k=3):
    query_text = row_to_text(row)
    embedding_model = load_embedding_model()
    query_vector = embed_texts(embedding_model, [query_text])[0].tolist()

    client = get_chroma_client()
    collection = client.get_collection(name="alerts")

    # 欲過濾的欄位
    filter_fields = ["src_ip", "dest_ip", "dest_port", "domain"]
    metadata_filter = build_metadata_filter(row, filter_fields)

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
        where=metadata_filter if metadata_filter else None
    )
    return query_text, results

def find_and_generate_note(new_row: pd.Series, top_k=3, threshold=0.5) -> str:
    query_text, results = query_similar_notes(new_row, top_k)

    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        similarity = 1 - dist
        if similarity >= threshold and "note" in meta and meta["note"]:
            return generate_note_from_example(meta["note"], query_text)

    return "⚠️ 找不到相似的筆記來生成註解。"

def debug_query_note(new_row: pd.Series, top_k=3, threshold=0.3):
    query_text, results = query_similar_notes(new_row, top_k)
    print(f"[Query Text]: {query_text}")

    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        similarity = 1 - dist
        print(f"Doc: {doc[:30]}... Similarity: {similarity:.4f} Note: {meta.get('note', '')[:30]}...")
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

# === 超級詳細 Debug ===
def debug_query_with_details(row: pd.Series, top_k=5, threshold=0.3):
    print(f"\n=== [Debug Query] ===")
    query_text = row_to_text(row)
    print(f"Query text:\n{query_text}")

    embedding_model = load_embedding_model()
    query_vector = embed_texts(embedding_model, [query_text])[0].tolist()

    client = get_chroma_client()
    collection = client.get_collection(name="alerts")

    filter_fields = ["src_ip", "dest_ip", "dest_port", "domain"]
    metadata_filter = build_metadata_filter(row, filter_fields)
    print(f"Metadata filter for query:\n{metadata_filter}")

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
        where=metadata_filter if metadata_filter else None
    )

    doc_list = results.get("documents", [[]])[0]
    meta_list = results.get("metadatas", [[]])[0]
    dist_list = results.get("distances", [[]])[0]

    print(f"Total results found: {len(doc_list)}\n")

    for i, (doc, meta, dist) in enumerate(zip(doc_list, meta_list, dist_list)):
        similarity = 1- dist
        print(f"Result #{i}:")
        print(f"  Similarity: {similarity:.4f}")
        print(f"  Note: {meta.get('note', '')[:100]}")
        print(f"  Metadata: {meta}")
        print(f"  Document text preview: {doc[:100]}...\n")

    # 新增：用找到的範例筆記產生新的筆記
    for meta, dist in zip(meta_list, dist_list):
        similarity = 1 - dist
        if similarity >= threshold and meta.get("note"):
            print(f"Found note above threshold ({threshold}), ready for LLM generation.")
            # 用範例筆記呼叫 LLM 產生新筆記
            new_note = generate_note_from_example(meta["note"], query_text)
            print(f"\n🆕 Generated new note:\n{new_note}")
            return new_note, {
                "query_text": query_text,
                "similarity": similarity,
                "example_note": meta["note"]
            }

    print("⚠️ 無法找到足夠相似的筆記來生成註解。")
    return "⚠️ 無法找到足夠相似的筆記來生成註解。", {
        "query_text": query_text,
        "similarity": 0.0,
        "example_note": "(無匹配資料)"
    }
