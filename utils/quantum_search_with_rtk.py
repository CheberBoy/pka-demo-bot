#!/usr/bin/env python3
"""
Quantum Search + RTK Integration
Гибридный поисковик с автоматической очисткой контекста

Использует:
1. Quantum Search (BM25 + Cosine Similarity) для поиска
2. RTK (Runtime Tool Kit) для сжатия результатов
3. Combo = идеальный баланс: быстрый поиск + чистый контекст
"""

import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple
from quantum_search import QuantumSearch


class QuantumSearchWithRTK:
    """
    Объединяет Quantum Search и RTK для оптимального использования контекста
    
    Workflow:
    1. Пользователь задаёт вопрос
    2. Quantum Search находит релевантные документы
    3. RTK сжимает результаты (убирает мусор)
    4. Возвращаем компактный результат
    5. Контекст остаётся ЧИСТЫМ ✨
    """
    
    def __init__(self, db_path: str = "quantum.db"):
        self.quantum = QuantumSearch(db_path)
        self.rtk_available = self._check_rtk()
        self.compression_stats = {
            "total_searches": 0,
            "tokens_saved": 0,
            "avg_compression": 0
        }
    
    def _check_rtk(self) -> bool:
        """Проверяем доступность RTK"""
        try:
            result = subprocess.run(
                ['rtk', '--help'],
                capture_output=True,
                timeout=2
            )
            available = result.returncode == 0
            if available:
                print("✅ RTK available - context compression enabled")
            else:
                print("⚠️  RTK not available - using uncompressed results")
            return available
        except Exception as e:
            print(f"⚠️  RTK check failed: {e}")
            return False
    
    # ============================================
    # RTK COMPRESSION METHODS
    # ============================================
    
    def _rtk_smart_summary(self, text: str) -> str:
        """
        Использует RTK 'smart' command для создания 2-строчного резюме
        
        Уменьшает текст с 300 слов до 20-30 слов!
        
        Args:
            text: Исходный текст
        
        Returns:
            Компактное резюме (2 строки макс)
        """
        
        if not self.rtk_available:
            return text[:100] + "..."
        
        try:
            result = subprocess.run(
                ['rtk', 'smart'],
                input=text.encode(),
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                summary = result.stdout.decode().strip()
                return summary if summary else text[:100]
            else:
                return text[:100]
        
        except Exception as e:
            print(f"⚠️  RTK summary error: {e}")
            return text[:100]
    
    def _rtk_json_structure(self, data: Dict) -> str:
        """
        Показывает структуру JSON без значений (только ключи)
        Идеально для понимания структуры без засорения
        
        Args:
            data: JSON объект
        
        Returns:
            Компактная структура
        """
        
        if not self.rtk_available:
            return json.dumps(data, indent=2)[:200]
        
        try:
            result = subprocess.run(
                ['rtk', 'json'],
                input=json.dumps(data).encode(),
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return result.stdout.decode().strip()
            else:
                return json.dumps(data)
        
        except Exception as e:
            print(f"⚠️  RTK json error: {e}")
            return json.dumps(data)
    
    # ============================================
    # HYBRID SEARCH WITH COMPRESSION
    # ============================================
    
    def search_smart(self, query: str, limit: int = 3, compress: bool = True) -> List[Dict]:
        """
        Smart search: Quantum Search + RTK compression
        
        Это ГЛАВНЫЙ МЕТОД - используй его!
        
        Args:
            query: Поисковый запрос
            limit: Макс результатов
            compress: Использовать RTK для сжатия
        
        Returns:
            Список результатов (компактные!)
        
        Example:
            >>> search = QuantumSearchWithRTK()
            >>> results = search.search_smart("как работает салон?")
            >>> for doc in results:
            ...     print(f"{doc['id']}: {doc['summary_short']}")
        """
        
        # Шаг 1: Поиск через Quantum Search
        results = self.quantum.search_hybrid(query, limit=limit)
        
        if not results:
            return []
        
        # Шаг 2: Сжатие через RTK (если включен)
        if compress and self.rtk_available:
            for result in results:
                # Сжимаем длинное резюме
                original_len = len(result['summary'])
                result['summary_short'] = self._rtk_smart_summary(result['summary'])
                result['summary_original'] = result['summary']  # сохраняем на случай
                
                # Статистика
                compressed_len = len(result['summary_short'])
                reduction = 100 * (1 - compressed_len / max(original_len, 1))
                result['compression_ratio'] = f"{reduction:.1f}%"
                
                self.compression_stats["tokens_saved"] += original_len - compressed_len
        
        self.compression_stats["total_searches"] += 1
        
        return results
    
    def search_with_context_limit(self, query: str, max_tokens: int = 500) -> List[Dict]:
        """
        Поиск с максимальным лимитом токенов в результатах
        
        Гарантирует что результаты не превысят token limit!
        
        Args:
            query: Поисковый запрос
            max_tokens: Максимум токенов в ответе
        
        Returns:
            Результаты которые уложены в token limit
        """
        
        results = self.search_smart(query, limit=10)  # ищем больше
        
        total_tokens = 0
        filtered_results = []
        
        for result in results:
            # Примерно 1 токен = 4 символа
            result_tokens = len(result.get('summary_short', result['summary'])) // 4
            
            if total_tokens + result_tokens <= max_tokens:
                filtered_results.append(result)
                total_tokens += result_tokens
            else:
                break
        
        return filtered_results
    
    # ============================================
    # ADVANCED METHODS
    # ============================================
    
    def search_and_explain(self, query: str) -> Dict:
        """
        Поиск + объяснение почему это релевантно
        
        Для обучения: показывает WT BM25 и Cosine помогли найти результат
        """
        
        results = self.search_smart(query, limit=1)
        
        if not results:
            return {"error": "No results found"}
        
        top_result = results[0]
        
        return {
            "query": query,
            "result_id": top_result['id'],
            "summary": top_result['summary_short'],
            "relevance_score": f"{top_result['score']:.2%}",
            "why_relevant": self._explain_relevance(query, top_result),
            "compression_saved": top_result.get('compression_ratio', '0%')
        }
    
    def _explain_relevance(self, query: str, result: Dict) -> str:
        """
        Объясняет почему результат релевантен запросу
        
        Простое объяснение алгоритмов
        """
        
        score = result['score']
        bm25_score = result.get('bm25_score', 0)
        semantic_score = result.get('semantic_score', 0)
        
        if bm25_score > 0.7:
            return f"🎯 Точное совпадение ключевых слов (BM25: {bm25_score:.2%})"
        elif semantic_score > 0.7:
            return f"🧠 Смысловое совпадение (Cosine: {semantic_score:.2%})"
        else:
            return f"✓ Комбинированная релевантность ({score:.2%})"
    
    def get_compression_stats(self) -> Dict:
        """
        Статистика сжатия контекста
        
        Показывает сколько токенов мы сэкономили!
        """
        
        if self.compression_stats["total_searches"] == 0:
            return {"error": "No searches yet"}
        
        return {
            "total_searches": self.compression_stats["total_searches"],
            "tokens_saved": self.compression_stats["tokens_saved"],
            "avg_tokens_per_search": self.compression_stats["tokens_saved"] // max(self.compression_stats["total_searches"], 1),
            "rtk_available": self.rtk_available
        }
    
    # ============================================
    # BATCH OPERATIONS
    # ============================================
    
    def search_batch(self, queries: List[str]) -> List[List[Dict]]:
        """
        Поиск для множественных запросов
        Полезно для анализа расписания вопросов
        """
        
        results = []
        for query in queries:
            result = self.search_smart(query, limit=1)
            results.append(result)
        
        return results
    
    def close(self):
        """Закрыть БД"""
        self.quantum.close()


# ============================================
# USAGE EXAMPLES
# ============================================

if __name__ == "__main__":
    print("\n🚀 Quantum Search + RTK Integration Demo\n")
    print("=" * 60)
    
    search = QuantumSearchWithRTK()
    
    # Добавляем тестовые документы
    search.quantum.add_document(
        "salon_1",
        "Services & Pricing",
        """Наш салон предлагает полный спектр услуг красоты. 
        Стрижка волос: 500 сом. Окрашивание: 2000 сом. 
        Маникюр: 600 сом. Педикюр: 700 сом. 
        Брови: 400 сом. Мы используем только качественные материалы. 
        Все мастера имеют сертификаты и многолетний опыт. 
        Приходите и убедитесь сами в качестве наших услуг!""",
        ["salon", "services", "pricing", "beauty"]
    )
    
    search.quantum.add_document(
        "salon_2",
        "Working Hours & Schedule",
        """Мы открыты с 9:00 до 19:00 каждый день. 
        Перерыв на обед с 13:00 до 14:00. 
        Запись по телефону: +996 555 123 456. 
        Или через Telegram бота нашего салона. 
        Расписание мастеров обновляется каждый день. 
        Свободные слоты: 30 минут.""",
        ["salon", "schedule", "hours", "booking"]
    )
    
    search.quantum.add_document(
        "salon_3",
        "Master Info",
        """Наши мастера: Айгуль (колорист), Динара (парикмахер), 
        Назгуль (мастер маникюра). Все имеют опыт 5+ лет. 
        Проводим обучение каждый месяц. 
        Все сертифицированы международными стандартами.""",
        ["masters", "staff", "specialists"]
    )
    
    # ============================================
    # TEST 1: Simple search
    # ============================================
    print("\n📌 TEST 1: Simple Smart Search")
    print("-" * 60)
    
    query = "сколько стоит стрижка?"
    results = search.search_smart(query)
    
    for result in results:
        print(f"\n✓ Result: {result['id']}")
        print(f"  Relevance: {result['score']:.2%}")
        print(f"  Compressed: {result.get('compression_ratio', 'N/A')}")
        print(f"  Summary: {result['summary_short']}")
    
    # ============================================
    # TEST 2: Search with explanation
    # ============================================
    print("\n\n📌 TEST 2: Search with Explanation")
    print("-" * 60)
    
    query = "когда вы открыты?"
    explanation = search.search_and_explain(query)
    
    print(f"Query: {explanation['query']}")
    print(f"Why relevant: {explanation['why_relevant']}")
    print(f"Tokens saved: {explanation['compression_saved']}")
    
    # ============================================
    # TEST 3: Token-limited search
    # ============================================
    print("\n\n📌 TEST 3: Token-Limited Search (max 200 tokens)")
    print("-" * 60)
    
    query = "салон услуги мастера расписание"
    results = search.search_with_context_limit(query, max_tokens=200)
    
    print(f"Found {len(results)} results within 200-token limit")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['id']}")
        print(f"   {result['summary_short'][:100]}...")
    
    # ============================================
    # STATS
    # ============================================
    print("\n\n📊 Compression Statistics")
    print("-" * 60)
    
    stats = search.get_compression_stats()
    print(f"Total searches: {stats['total_searches']}")
    print(f"Tokens saved: {stats['tokens_saved']}")
    print(f"Avg tokens/search: {stats['avg_tokens_per_search']}")
    print(f"RTK available: {'✅ Yes' if stats['rtk_available'] else '❌ No'}")
    
    print("\n" + "=" * 60)
    print("✨ Demo complete!")
    
    search.close()
