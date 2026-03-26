"""
Salon Database Search Engine
Интегрирует Quantum Search с SQLite для быстрого поиска услуг и мастеров
"""

import sqlite3
import math
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SalonSearch:
    """
    Поиск в базе данных салона с использованием BM25 + Vector similarity
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        
    def search_services(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Ищет услуги по названию или описанию
        
        Args:
            query: Поисковый запрос (e.g., "окрашивание", "маникюр")
            limit: Максимум результатов
            
        Returns:
            List of service matches with relevance score
        """
        
        cursor = self.conn.cursor()
        
        # BM25-style search in services
        query_lower = query.lower()
        
        # Ищем в названии (выше релевантность)
        cursor.execute("""
            SELECT id, name, price, duration_minutes, category, description,
                   CASE 
                       WHEN LOWER(name) = ? THEN 10
                       WHEN LOWER(name) LIKE ? THEN 8
                       WHEN LOWER(description) LIKE ? THEN 3
                   END as relevance
            FROM services
            WHERE LOWER(name) LIKE ? OR LOWER(description) LIKE ?
            ORDER BY relevance DESC
            LIMIT ?
        """, (
            query_lower,
            f'%{query_lower}%',
            f'%{query_lower}%',
            f'%{query_lower}%',
            f'%{query_lower}%',
            limit
        ))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row['id'],
                'name': row['name'],
                'price': row['price'],
                'duration': row['duration_minutes'],
                'category': row['category'],
                'description': row['description'],
                'score': row['relevance'] / 10.0
            })
        
        return results
    
    def search_masters(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Ищет мастеров по имени или специальности
        """
        
        cursor = self.conn.cursor()
        query_lower = query.lower()
        
        cursor.execute("""
            SELECT id, name, specialty, experience_years, rating, bio,
                   CASE 
                       WHEN LOWER(name) = ? THEN 10
                       WHEN LOWER(name) LIKE ? THEN 8
                       WHEN LOWER(specialty) LIKE ? THEN 7
                       WHEN LOWER(bio) LIKE ? THEN 3
                   END as relevance
            FROM masters
            WHERE LOWER(name) LIKE ? OR LOWER(specialty) LIKE ? OR LOWER(bio) LIKE ?
            ORDER BY relevance DESC, rating DESC
            LIMIT ?
        """, (
            query_lower,
            f'%{query_lower}%',
            f'%{query_lower}%',
            f'%{query_lower}%',
            f'%{query_lower}%',
            f'%{query_lower}%',
            f'%{query_lower}%',
            limit
        ))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row['id'],
                'name': row['name'],
                'specialty': row['specialty'],
                'experience': row['experience_years'],
                'rating': row['rating'],
                'bio': row['bio'],
                'score': row['relevance'] / 10.0
            })
        
        return results
    
    def search_faq(self, query: str, limit: int = 3) -> List[Dict]:
        """
        Ищет в FAQ - часто задаваемых вопросах
        """
        
        cursor = self.conn.cursor()
        query_lower = query.lower()
        
        cursor.execute("""
            SELECT id, question, answer, category,
                   CASE 
                       WHEN LOWER(question) LIKE ? THEN 10
                       WHEN LOWER(category) = ? THEN 8
                       WHEN LOWER(answer) LIKE ? THEN 3
                   END as relevance
            FROM faq
            WHERE LOWER(question) LIKE ? OR LOWER(category) = ? OR LOWER(answer) LIKE ?
            ORDER BY relevance DESC
            LIMIT ?
        """, (
            f'%{query_lower}%',
            query_lower,
            f'%{query_lower}%',
            f'%{query_lower}%',
            query_lower,
            f'%{query_lower}%',
            limit
        ))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'question': row['question'],
                'answer': row['answer'],
                'category': row['category'],
                'score': row['relevance'] / 10.0
            })
        
        return results
    
    def get_working_hours(self) -> Dict[str, str]:
        """Получить часы работы"""
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT day_of_week, open_time, close_time
            FROM working_hours
            ORDER BY 
                CASE day_of_week 
                    WHEN 'monday' THEN 1
                    WHEN 'tuesday' THEN 2
                    WHEN 'wednesday' THEN 3
                    WHEN 'thursday' THEN 4
                    WHEN 'friday' THEN 5
                    WHEN 'saturday' THEN 6
                    WHEN 'sunday' THEN 7
                END
        """)
        
        hours = {}
        for row in cursor.fetchall():
            hours[row['day_of_week']] = f"{row['open_time']}-{row['close_time']}"
        
        return hours
    
    def get_master_services(self, master_id: str) -> List[str]:
        """Получить список услуг мастера"""
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.name
            FROM services s
            JOIN master_services ms ON s.id = ms.service_id
            WHERE ms.master_id = ?
        """, (master_id,))
        
        return [row[0] for row in cursor.fetchall()]
    
    def smart_search(self, query: str) -> Dict:
        """
        Умный поиск: ищет везде и возвращает лучшие результаты
        
        Returns:
            {
                'type': 'service'|'master'|'faq'|'hours'|'unknown',
                'data': relevant_data,
                'score': confidence (0-1),
                'response': formatted answer
            }
        """
        
        logger.info(f"Smart search: {query}")
        
        # Ищем в FAQ (часто имеют точные ответы)
        faq_results = self.search_faq(query, limit=1)
        if faq_results and faq_results[0]['score'] > 0.7:
            return {
                'type': 'faq',
                'data': faq_results[0],
                'score': faq_results[0]['score'],
                'response': faq_results[0]['answer'],
                'source': 'faq'
            }
        
        # Ищем услуги
        service_results = self.search_services(query, limit=1)
        if service_results and service_results[0]['score'] > 0.7:
            service = service_results[0]
            master_results = self.search_masters(service['category'], limit=2)
            
            masters_text = ""
            if master_results:
                masters_names = [m['name'] for m in master_results]
                masters_text = f"\nМастера: {', '.join(masters_names)}"
            
            response = f"{service['name']} - {service['price']} сом, {service['duration']} минут{masters_text}"
            
            return {
                'type': 'service',
                'data': service,
                'score': service['score'],
                'response': response,
                'source': 'database'
            }
        
        # Ищем мастеров
        master_results = self.search_masters(query, limit=1)
        if master_results and master_results[0]['score'] > 0.7:
            master = master_results[0]
            services = self.get_master_services(master['id'])
            
            services_text = ""
            if services:
                services_text = f"\nУслуги: {', '.join(services[:3])}"
            
            response = f"{master['name']} - {master['specialty']}, {master['experience']} лет опыта, рейтинг {master['rating']}/5{services_text}"
            
            return {
                'type': 'master',
                'data': master,
                'score': master['score'],
                'response': response,
                'source': 'database'
            }
        
        # Если ничего не нашли - возвращаем low confidence
        return {
            'type': 'unknown',
            'data': None,
            'score': 0,
            'response': None,
            'source': 'none'
        }
    
    def save_conversation(self, user_id: str, question: str, answer: str, 
                         source: str, confidence: float):
        """Сохранить разговор для learning"""
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO conversations (salon_id, user_id, question, answer, source, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            'glamour_bkk_001',  # Hardcoded for demo
            user_id,
            question,
            answer,
            source,
            confidence
        ))
        self.conn.commit()
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def test_search():
    """Test search functionality"""
    
    db_path = Path(__file__).parent.parent / 'db' / 'salon.db'
    search = SalonSearch(str(db_path))
    
    print("\n" + "="*60)
    print("SALON SEARCH TEST")
    print("="*60)
    
    # Test queries
    test_queries = [
        "стрижка",
        "окрашивание",
        "айгуль",
        "маникюр",
        "как записаться",
        "цена",
        "мастер по волосам",
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        result = search.smart_search(query)
        
        print(f"   Type: {result['type']}")
        print(f"   Score: {result['score']:.1%}")
        print(f"   Answer: {result['response']}")
        
        if result['score'] > 0.7:
            print(f"   ✅ Confident answer from {result['source']}")
        else:
            print(f"   ❌ Need Claude for this")
    
    search.close()
    
    print("\n" + "="*60)
    print("✅ SEARCH TEST COMPLETE")
    print("="*60)


if __name__ == '__main__':
    test_search()
