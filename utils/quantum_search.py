#!/usr/bin/env python3
"""
Quantum Search System - BM25 + Cosine Similarity
Двухуровневый поиск для долгосрочной памяти

Использует:
1. BM25 - классический поиск по ключевым словам (точность)
2. Cosine Similarity - смысловой поиск через embeddings (релевантность)
"""

import sqlite3
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple
import json

# Опциональные зависимости для embedding
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("⚠️  sklearn not installed. Install with: pip install scikit-learn")

class QuantumSearch:
    """
    Гибридный поисковик с BM25 и Cosine Similarity
    """
    
    def __init__(self, db_path: str = "quantum.db"):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._setup_fts()  # Включаем FTS5 для BM25
    
    def _setup_fts(self):
        """Создаём FTS5 таблицы для быстрого BM25 поиска"""
        cur = self.conn.cursor()
        
        # FTS5 таблица для разговоров
        cur.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts 
            USING fts5(
                id,
                topic,
                summary,
                tags,
                content='conversations',
                content_rowid='id'
            )
        """)
        
        # Синхронизируем FTS таблицу
        cur.execute("""
            INSERT INTO conversations_fts (id, topic, summary, tags)
            SELECT id, topic, summary, tags FROM conversations
            WHERE id NOT IN (SELECT id FROM conversations_fts)
        """)
        
        self.conn.commit()
    
    # ============================================
    # 1. BM25 ПОИСК (классический, быстрый)
    # ============================================
    
    def search_bm25(self, query: str, table: str = "conversations", limit: int = 5) -> List[Dict]:
        """
        BM25 поиск - классический поиск по ключевым словам.
        
        Использует SQLite FTS5 для быстрого поиска.
        BM25 - это формула которая работает в Google, Elasticsearch и т.д.
        
        Args:
            query: Поисковый запрос ("салон расписание")
            table: Таблица для поиска
            limit: Максимум результатов
        
        Returns:
            Список документов отсортированных по релевантности
        
        Example:
            >>> search = QuantumSearch()
            >>> results = search.search_bm25("как автоматизировать салон?")
            >>> for doc in results:
            ...     print(f"{doc['id']}: {doc['summary']}")
        """
        
        cur = self.conn.cursor()
        
        # FTS5 нативно использует BM25
        try:
            cur.execute(f"""
                SELECT 
                    rank,
                    id,
                    topic,
                    summary,
                    tags
                FROM {table}_fts
                WHERE {table}_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (self._prepare_query(query), limit))
            
            results = []
            for row in cur.fetchall():
                results.append({
                    'id': row['id'],
                    'topic': row['topic'],
                    'summary': row['summary'],
                    'tags': json.loads(row['tags'] or '[]'),
                    'score': 1.0 / (1.0 + abs(row['rank']))  # Нормализуем rank в score
                })
            
            return results
        
        except Exception as e:
            print(f"❌ BM25 search error: {e}")
            return []
    
    # ============================================
    # 2. COSINE SIMILARITY ПОИСК (смысловой)
    # ============================================
    
    def search_semantic(self, query: str, table: str = "conversations", limit: int = 5) -> List[Dict]:
        """
        Cosine Similarity поиск - поиск по смыслу.
        
        Превращает запрос и документы в векторы, затем ищет похожие.
        Это как Google: понимает что "смартфон" и "мобильный телефон" - это одно.
        
        Args:
            query: Поисковый запрос ("как записать клиента?")
            table: Таблица для поиска
            limit: Максимум результатов
        
        Returns:
            Список документов отсортированных по релевантности (0-1)
        
        Example:
            >>> results = search.search_semantic("автоматизация салона")
            >>> for doc in results:
            ...     print(f"{doc['id']}: relevance={doc['score']:.2f}")
        """
        
        if not HAS_SKLEARN:
            print("⚠️  sklearn required for semantic search")
            return []
        
        cur = self.conn.cursor()
        
        # Получаем все документы
        cur.execute(f"""
            SELECT id, topic, summary, tags 
            FROM {table}
            ORDER BY datetime('now') DESC
            LIMIT 1000
        """)
        
        docs = cur.fetchall()
        if not docs:
            return []
        
        # Подготавливаем тексты для векторизации
        doc_texts = [
            f"{d['topic']} {d['summary']} {d['tags']}"
            for d in docs
        ]
        
        # Создаём TF-IDF векторы
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words=None,  # Используем свои stop words для кириллицы
            min_df=1,
            max_df=1.0
        )
        
        try:
            doc_vectors = vectorizer.fit_transform(doc_texts)
            query_vector = vectorizer.transform([query])
            
            # Считаем косинусное сходство
            similarities = cosine_similarity(query_vector, doc_vectors)[0]
            
            # Сортируем по релевантности (убывание)
            top_indices = np.argsort(similarities)[::-1][:limit]
            
            results = []
            for idx in top_indices:
                score = float(similarities[idx])
                if score > 0.05:  # Только если есть хоть какое-то совпадение
                    results.append({
                        'id': docs[idx]['id'],
                        'topic': docs[idx]['topic'],
                        'summary': docs[idx]['summary'],
                        'tags': json.loads(docs[idx]['tags'] or '[]'),
                        'score': score
                    })
            
            return results
        
        except Exception as e:
            print(f"❌ Semantic search error: {e}")
            return []
    
    # ============================================
    # 3. HYBRID SEARCH (комбинированный)
    # ============================================
    
    def search_hybrid(self, query: str, limit: int = 5, bm25_weight: float = 0.3, semantic_weight: float = 0.7) -> List[Dict]:
        """
        Гибридный поиск - комбинирует BM25 и Cosine Similarity.
        
        Best of both worlds:
        - BM25 находит точные совпадения (если вы ищете "артикул 12345")
        - Cosine находит похожее по смыслу (если вы ищете "красная туфля")
        
        Args:
            query: Поисковый запрос
            limit: Максимум результатов
            bm25_weight: Вес BM25 (0-1)
            semantic_weight: Вес Cosine (0-1)
        
        Returns:
            Список документов с комбинированным score
        
        Example:
            >>> results = search.search_hybrid("автоматизировать запись в салон")
            >>> for doc in results:
            ...     print(f"{doc['id']}: {doc['score']:.2f}")
        """
        
        # Получаем результаты от обоих алгоритмов
        bm25_results = self.search_bm25(query, limit=limit*2)
        semantic_results = self.search_semantic(query, limit=limit*2) if HAS_SKLEARN else []
        
        # Нормализуем и комбинируем
        combined = {}
        
        for doc in bm25_results:
            combined[doc['id']] = {
                **doc,
                'bm25_score': doc['score'],
                'semantic_score': 0
            }
        
        for doc in semantic_results:
            if doc['id'] in combined:
                combined[doc['id']]['semantic_score'] = doc['score']
            else:
                combined[doc['id']] = {
                    **doc,
                    'bm25_score': 0,
                    'semantic_score': doc['score']
                }
        
        # Вычисляем итоговый score
        for doc_id, data in combined.items():
            data['score'] = (
                data['bm25_score'] * bm25_weight +
                data['semantic_score'] * semantic_weight
            )
        
        # Сортируем и возвращаем
        results = sorted(combined.values(), key=lambda x: x['score'], reverse=True)[:limit]
        
        return results
    
    # ============================================
    # HELPER METHODS
    # ============================================
    
    def _prepare_query(self, query: str) -> str:
        """Подготавливаем запрос для FTS5 BM25"""
        # Простая подготовка: убираем спецсимволы
        return query.replace('"', '').replace("'", "").strip()
    
    def add_document(self, doc_id: str, topic: str, summary: str, tags: List[str] = None):
        """Добавить документ в БД и индексы"""
        cur = self.conn.cursor()
        
        cur.execute("""
            INSERT INTO conversations (id, topic, summary, tags, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            doc_id,
            topic,
            summary,
            json.dumps(tags or []),
            datetime.now()
        ))
        
        # Обновляем FTS индекс
        cur.execute("""
            INSERT INTO conversations_fts (id, topic, summary, tags)
            VALUES (?, ?, ?, ?)
        """, (
            doc_id,
            topic,
            summary,
            json.dumps(tags or [])
        ))
        
        self.conn.commit()
    
    def close(self):
        """Закрыть БД"""
        self.conn.close()


# ============================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ
# ============================================

if __name__ == "__main__":
    search = QuantumSearch()
    
    # Добавляем тестовые документы
    search.add_document(
        "doc1",
        "salon_scheduling",
        "Система автоматизации записи для салонов красоты. Клиенты бронируют через Telegram.",
        ["salon", "scheduling", "automation", "telegram"]
    )
    
    search.add_document(
        "doc2",
        "cafe_ordering",
        "Голосовой бот для кафе. Берёт заказы, создаёт расписание столиков.",
        ["cafe", "voice", "ordering", "schedule"]
    )
    
    search.add_document(
        "doc3",
        "ecommerce_search",
        "Поисковая система для интернет-магазина с рекомендациями товаров.",
        ["ecommerce", "search", "recommendations"]
    )
    
    # Тестируем поиск
    query = "как автоматизировать запись клиентов?"
    
    print(f"\n🔍 Searching for: '{query}'\n")
    
    print("=" * 50)
    print("1. BM25 (точный поиск)")
    print("=" * 50)
    for doc in search.search_bm25(query):
        print(f"  [{doc['id']}] {doc['topic']}")
        print(f"    Score: {doc['score']:.2f}")
        print(f"    Summary: {doc['summary'][:50]}...")
        print()
    
    print("=" * 50)
    print("2. Cosine Similarity (смысловой поиск)")
    print("=" * 50)
    for doc in search.search_semantic(query):
        print(f"  [{doc['id']}] {doc['topic']}")
        print(f"    Score: {doc['score']:.2f}")
        print(f"    Summary: {doc['summary'][:50]}...")
        print()
    
    print("=" * 50)
    print("3. Hybrid (комбинированный)")
    print("=" * 50)
    for doc in search.search_hybrid(query):
        print(f"  [{doc['id']}] {doc['topic']}")
        print(f"    Combined Score: {doc['score']:.2f}")
        print(f"    Summary: {doc['summary'][:50]}...")
        print()
    
    search.close()
