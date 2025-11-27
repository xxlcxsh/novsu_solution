import torch
import pandas as pd
import os
import traceback
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any 
from sentence_transformers import SentenceTransformer
# Предполагается, что BM25 импортирует нужные классы/функции
from BM25 import TwoStageSearch, search_BM25_global
import pickle

# ВАЖНО: Убедитесь, что FAISSStore, Reranker, load_llm и generate_answer 
# доступны через импорты, которые вы используете.
try:
    from faiss_store import FAISSStore, Reranker, get_context_hybrid
    from llm import load_llm, generate_answer 
except ImportError as e:
    print(f"RAG Import Error: {e}. Убедитесь, что 'faiss_store.py' и 'llm.py' доступны.")
    FAISSStore, Reranker, get_context_hybrid, load_llm, generate_answer = None, None, None, None, None

# --- КОНФИГУРАЦИЯ ---
LLM_MODEL = "models/qwen3_06b"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
VECTOR_STORE_TEXT_PATH = Path("data/vector_store_text")
VECTOR_STORE_TABLE_PATH = Path("data/vector_store_table")

# Глобальные переменные для хранения инициализированных ресурсов (загружаются один раз)
LLM_RESOURCES: Dict[str, Any] = {
    "tokenizer": None,
    "model": None,
    "store_text": None,   # TEXT FAISS Store
    "store_tables": None, # TABLES FAISS Store (Optional)
    "emb_model": None,
    "reranker": None,
    "searcher": None,
    "all_payloads": None  # Payloads для BM25
}
# --------------------


def initialize_rag_resources() -> bool:
    """Инициализирует все тяжелые RAG-ресурсы при запуске сервера."""
    print("--- Инициализация Qwen RAG ресурсов ---")

    if load_llm is None:
        print("Не удалось импортировать RAG-модули. Проверьте faiss_store.py и llm.py.")
        return False

    try:
        # 1. Загружаем payloads для TEXT и TABLES
        with open(VECTOR_STORE_TEXT_PATH / "payloads.pkl", "rb") as f:
            text_payloads = pickle.load(f)
        
        # Загружаем TABLES (С обработкой отсутствия)
        table_payloads: List[Dict[str, Any]] = []
        try:
            with open(VECTOR_STORE_TABLE_PATH / "payloads.pkl", "rb") as f:
                table_payloads = pickle.load(f)
                # Добавляем поле 'type' для BM25, если оно не было добавлено при индексировании
                for payload in table_payloads:
                    if 'type' not in payload:
                        payload['type'] = 'table'
        except FileNotFoundError:
            print("Табличный индекс не найден. Инициализация только текстового поиска.")

        # all_payloads для BM25 (текст + таблицы)
        all_payloads = text_payloads + table_payloads 

        all_text_chunks = [p["text"] for p in all_payloads]

        # 2. Загружаем FAISS stores
        store_text = FAISSStore(VECTOR_STORE_TEXT_PATH, payloads=text_payloads).load_embds()
        
        store_tables = None
        if table_payloads:
            # Передаем table_payloads в FAISSStore для инициализации
            store_tables = FAISSStore(VECTOR_STORE_TABLE_PATH, payloads=table_payloads).load_embds()

        # 3. Инициализация BM25 (на всех документах)
        searcher = TwoStageSearch(n_gram_size=3)
        searcher.fit(all_text_chunks)

        # 4. Модель эмбеддингов
        emb_model = SentenceTransformer(
            "models/multilingual-e5-large",
            local_files_only=True,
            device=DEVICE
        )

        # 5. Reranker
        reranker = Reranker("models/cross-encoder/ms-marco-MiniLM-L-6-v2")

        # 6. LLM
        tokenizer, model = load_llm(LLM_MODEL)

        # 7. Сохраняем все глобально
        LLM_RESOURCES.update({
            "tokenizer": tokenizer,
            "model": model,
            "store_text": store_text,
            "store_tables": store_tables, 
            "emb_model": emb_model,
            "reranker": reranker,
            "searcher": searcher,
            "all_payloads": all_payloads
        })

        print("--- Qwen RAG ресурсы успешно инициализированы ---")
        return True

    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА: Ошибка инициализации RAG: {e}")
        traceback.print_exc()
        return False


def get_rag_answer(history: List[tuple], user_query: str, use_tables: bool = False):
    """
    Основная функция RAG, использующая гибридный поиск по тексту и таблицам.
    """
    tokenizer = LLM_RESOURCES["tokenizer"]
    model = LLM_RESOURCES["model"]
    store_text = LLM_RESOURCES["store_text"]
    store_tables = LLM_RESOURCES["store_tables"]
    emb_model = LLM_RESOURCES["emb_model"]
    reranker = LLM_RESOURCES["reranker"]
    searcher = LLM_RESOURCES["searcher"]
    all_payloads = LLM_RESOURCES["all_payloads"]
    
    try:
        # Проверка, что LLM-ресурсы инициализированы
        if not all([tokenizer, model, store_text, emb_model, reranker, searcher]):
             return {"answer": "RAG ресурсы не инициализированы.", "source_documents": []}

        # 1. ГИБРИДНЫЙ ПОИСК (Vector + Rerank)
        # Получаем топ-2 документа, прошедших Reranker
        context_str, payload_docs = get_context_hybrid(
            user_query,
            store_text,
            store_tables,
            emb_model,
            reranker,
            top_faiss=25, 
            top_final=2,
            use_tables=use_tables 
        )

        # 2. BM25 ПОИСК
        # BM25 ищет по всем документам (text + tables), но в этом контексте 
        # нам нужно только текстовое дополнение
        bm25_candidates_raw = search_BM25_global(searcher, user_query, all_payloads)
        
        final_docs = []
        if payload_docs:
            final_docs.extend(payload_docs)
            reranker_doc_id = payload_docs[0]['payload'].get('id')
        else:
            reranker_doc_id = None


        # Находим лучший документ из BM25, который отличается от топ-1 Reranker
        bm25_doc = None
        for doc in bm25_candidates_raw:
            # ID может отсутствовать, если вы его не добавляете при индексировании
            doc_id = doc["payload"].get("id")
            
            # Проверяем, что документ: 
            # 1) не является тем же, что и топ-1 Reranker ИЛИ топ-1 Reranker отсутствует
            # 2) если таблицы отключены, то тип должен быть "text"
            is_distinct = (doc_id is None) or (doc_id != reranker_doc_id)
            is_allowed = use_tables or (doc["payload"].get("type", "text") == "text")

            if is_distinct and is_allowed:
                bm25_doc = doc
                # Добавляем его в финальный список, если он еще не там
                is_already_in_final = any(
                    d['payload'].get('id') == bm25_doc['payload'].get('id') 
                    for d in final_docs
                )
                if not is_already_in_final:
                    final_docs.append(bm25_doc)
                break
        
        # Если ничего не нашли
        if not final_docs:
             return {"answer": "Я не нашел информацию по вашему запросу.", "source_documents": []}
             
        # Склеиваем контекст из финальных документов
        context = "\n\n".join([d["payload"]["text"] for d in final_docs])

        # ГЕНЕРАЦИЯ ОТВЕТА
        answer = generate_answer(
            tokenizer,
            model,
            history,
            user_query,
            context
        )

        # Подготовка данных о источниках для фронтенда
        source_documents = [
            {
                "filepath": d["payload"]["source"],
                "content": d["payload"]["text"],
                # Добавляем тип, чтобы фронтенд мог стилизовать его
                "type": d["payload"].get("type", "text") 
            }
            for d in final_docs
        ]

        return {
            "answer": answer,
            "source_documents": source_documents
        }

    except Exception as e:
        print("RAG ERROR:", e)
        traceback.print_exc()
        return {
            "answer": "Произошла критическая ошибка при обработке запроса RAG.",
            "source_documents": []
        }