from typing import List
from embedding import load_embedding_model, embed_texts

class MyEmbedding:
    def __init__(self, model=None):
        self.model = model or load_embedding_model()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        vectors = embed_texts(self.model, texts)
        return [vec.tolist() if hasattr(vec, 'tolist') else list(vec) for vec in vectors]

    def embed_query(self, text: str) -> List[float]:
        vectors = embed_texts(self.model, [text])
        vec = vectors[0]
        return vec.tolist() if hasattr(vec, 'tolist') else list(vec)