import faiss
import numpy as np
import pickle
from sentence_transformers import SentenceTransformer,CrossEncoder
from pathlib import Path

VECTOR_STORE_PATH = Path("vector_store_multilingual_800chunksize_150overlap")

class FAISSStore:
    def __init__(self, vector_store_path=VECTOR_STORE_PATH, payloads=None):
        self.vector_store_path = vector_store_path
        self.index = None
        self.embeddings = None
        self.payloads = None
        self.ids = None

    def load_embds(self):
        if self.payloads is None:  # fallback для обратной совместимости
            with open(self.vector_store_path / "payloads.pkl", "rb") as f:
                self.payloads = pickle.load(f)
        self.embeddings = np.load(self.vector_store_path / "embeddings.npy")
        self.index = faiss.read_index(str(self.vector_store_path / "faiss.index"))
        self.ids = list(range(len(self.payloads)))
        return self

    def search(self, query_emb, top_k=3):
        scores, indices = self.index.search(query_emb[np.newaxis, :], top_k)
        results = []
        score_list = scores[0]
        for rank, idx in enumerate(indices[0]):
            if idx == -1:
                continue
            results.append({
                "payload": self.payloads[idx],
                "score": float(score_list[rank])   # <----- ДОБАВИЛИ SCORE
            })
        return scores[0], results

class Reranker:
    def __init__(self, model_path):
        self.model = CrossEncoder(model_path, local_files_only=True)

    def rerank(self, query, candidates, top_n=3):
        if not candidates:
            return [], [], []
        pairs = []
        original_indices = []
        for i, c in enumerate(candidates):
            pairs.append((query, c['payload']['text']))
            original_indices.append(i)

        scores = self.model.predict(pairs)
        scored = sorted(
            zip(scores, candidates, original_indices),
            key=lambda x: x[0],
            reverse=True
        )
        top_scores = [s for s, _, _ in scored[:top_n]]
        top_candidates = [c for _, c, _ in scored[:top_n]]

        return top_candidates, top_scores


# faiss_store.py

# ... (импорты и классы FAISSStore, Reranker остаются без изменений) ...

def get_context_hybrid(
    query, 
    store_text, 
    store_tables, 
    emb_model, 
    reranker, 
    top_faiss=25, 
    top_final=3, 
    use_tables=False # <--- Флаг для включения таблиц
):
    """Гибридный поиск, объединяющий результаты из текстового и табличного индексов."""
    
    query_emb = emb_model.encode([query])[0]
    all_faiss_results = []
    
    # 1. Поиск в текстовом хранилище (всегда включено)
    # Поиск в текстовом хранилище (text_store)
    # Мы ищем с запасом (top_faiss * 2), так как у нас два источника
    _,text_results = store_text.search(query_emb, top_k=top_faiss) 
    all_faiss_results.extend(text_results)
    
    # 2. Поиск в табличном хранилище (только если флаг включен)
    if use_tables and store_tables is not None:
        _,table_results = store_tables.search(query_emb, top_k=top_faiss)
        
        # Добавляем тип документа, чтобы reranker видел откуда пришел документ
        for doc in table_results:
             doc['payload']['type'] = 'table'
        
        all_faiss_results.extend(table_results)
    all_faiss_results = sorted(all_faiss_results, key=lambda x: x['score'], reverse=True)
    
    # 3. Rerank
    final_results, _ = reranker.rerank(
        query, all_faiss_results[:top_faiss], top_n=top_final
    )
    
    context = "\n\n".join(doc['payload']['text'] for doc in final_results)
    
    return context, final_results

# Переименуй старую функцию get_context, если она еще где-то используется, или удали ее.
