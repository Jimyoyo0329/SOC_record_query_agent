import pandas as pd
import argparse
import os
from chromadb import PersistentClient
from embedding import load_embedding_model, embed_texts
from utils import dataframe_to_texts

CHROMA_DIR = "data/chroma_db"

def get_chroma_client():
    os.makedirs(CHROMA_DIR, exist_ok=True)
    return PersistentClient(path=CHROMA_DIR)

def read_file(filepath: str) -> pd.DataFrame:
    if filepath.endswith(".csv"):
        return pd.read_csv(filepath)
    elif filepath.endswith(".xlsx"):
        return pd.read_excel(filepath)
    else:
        raise ValueError("❌ 不支援的檔案格式，請提供 .csv 或 .xlsx 檔案")

def ingest_to_chroma(filepath: str):
    df = read_file(filepath)
    texts = dataframe_to_texts(df)
    embedding_model = load_embedding_model()
    embeddings = embed_texts(embedding_model, texts)

    client = get_chroma_client()
    collection = client.get_or_create_collection(name="alerts")

    for i, (text, vector) in enumerate(zip(texts, embeddings)):
        metadata = {
            k: str(v).strip() if pd.notna(v) else "nan"
            for k, v in df.iloc[i].to_dict().items()
            if k != "time"
        }

        print(f"Index {i} metadata note: {metadata.get('note')}")
        collection.add(
            documents=[text],
            # SentenceTransformer 這樣的 embedding 模型，產生出來的 vector可能是：numpy.ndarray
            # 但Chroma 的 collection.add() 方法要求的是：純 Python list 格式的向量
            embeddings=[vector.tolist()],
            metadatas=[metadata],
            ids=[f"doc_{i}"]
        )

    # ⚠️ 不再需要 persist()，因為 PersistentClient 會自動儲存
    # client.persist()

    print(f"✅ 成功匯入 {len(df)} 筆資料到 Chroma（檔案: {filepath}）")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="要匯入的 CSV 或 Excel 檔案路徑 (.csv or .xlsx)")
    args = parser.parse_args()
    ingest_to_chroma(args.file)