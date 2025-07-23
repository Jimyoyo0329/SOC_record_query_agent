# embedding.py

from sentence_transformers import SentenceTransformer

# ✅ 改成更強的多語言嵌入模型
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

_embedding_model = None

def load_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        print(f"🔍 載入嵌入模型：{MODEL_NAME}")
        _embedding_model = SentenceTransformer(MODEL_NAME)
    return _embedding_model

def embed_texts(model, texts):
    return model.encode(texts, convert_to_tensor=False, show_progress_bar=False)
