import pandas as pd
from chromadb import PersistentClient
from embedding import load_embedding_model, embed_texts
from utils import row_to_text
from llm_utils import generate_note_from_example

CHROMA_DIR = "data/chroma_db"

def get_chroma_client():
    return PersistentClient(path=CHROMA_DIR)

def build_metadata_filter(row: pd.Series, fields: list) -> dict:
    conditions = []
    for f in fields:
        val = row.get(f)
        if val is not None:
            if f in ["src_ip", "dest_ip", "domain"]:
                val_str = str(val).strip()
                if val_str != "":
                    conditions.append({f: val_str})
            elif f in ["dest_port", "src_port"]:
                try:
                    val_int = int(val)
                    conditions.append({f: val_int})
                except:
                    pass
    if not conditions:
        return {}
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}

def debug_test_query(num_samples=5, top_k=3):
    client = get_chroma_client()
    collection = client.get_collection(name="alerts")

    # 取前 num_samples 筆資料當查詢用
    data = collection.get(limit=num_samples)
    documents = data["documents"]
    metadatas = data["metadatas"]

    embedding_model = load_embedding_model()

    filter_fields = ["src_ip", "dest_ip", "dest_port", "domain"]

    for i in range(num_samples):
        print("="*40)
        meta = metadatas[i]
        print(f"Sample #{i} metadata:")
        for k, v in meta.items():
            print(f"  {k} ({type(v).__name__}): {v}")

        # 將 metadata 轉成 pd.Series 方便後續用
        row = pd.Series(meta)

        # 建立過濾條件
        metadata_filter = build_metadata_filter(row, filter_fields)
        print("Metadata filter for query:", metadata_filter)

        # 產生查詢文字
        query_text = row_to_text(row)
        query_vector = embed_texts(embedding_model, [query_text])[0].tolist()

        # 查詢
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
            where=metadata_filter
        )

        docs = results["documents"][0]
        metas = results["metadatas"][0]
        dists = results["distances"][0]

        print(f"Query text: {query_text}")
        print(f"Found {len(docs)} results:")

        if len(docs) == 0:
            print("  ⚠️ No results returned")
        for j, (doc, m, dist) in enumerate(zip(docs, metas, dists)):
            sim = 1 - dist
            note = m.get("note", "")
            print(f"  Result #{j}: sim={sim:.4f}, note={note[:50]}")

        print("\n")

if __name__ == "__main__":
    debug_test_query()
