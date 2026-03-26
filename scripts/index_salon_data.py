#!/usr/bin/env python3
import sqlite3
import json
import sys
from pathlib import Path

# Add project root to sys path
sys.path.append(str(Path(__file__).parent.parent))
from utils.quantum_search import QuantumSearch

def main():
    db_path = Path(__file__).parent.parent / "db" / "salon.db"
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return
        
    print(f"🔄 Connecting to {db_path}...")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS conversations")
    cursor.execute("""
        CREATE TABLE conversations (
            id TEXT PRIMARY KEY,
            topic TEXT,
            summary TEXT,
            tags TEXT,
            timestamp TIMESTAMP
        )
    """)
    conn.commit()
    
    # Init QuantumSearch
    search = QuantumSearch(str(db_path))
    
    # 1. Index Services
    cursor.execute("SELECT id, name, price, duration_minutes, description FROM services")
    services = cursor.fetchall()
    for s in services:
        doc_id = f"service_{s['id']}"
        topic = f"Услуга: {s['name']}"
        summary = f"Стоимость: {s['price']} сом. Длительность: {s['duration_minutes']} мин. Описание: {s['description']}"
        tags = ["услуга", "прайс", "цена", s['name'].lower()]
        search.add_document(doc_id, topic, summary, tags)
    print(f"✅ Indexed {len(services)} services")

    # 2. Index Masters
    cursor.execute("SELECT id, name, specialty, experience_years, rating, bio FROM masters")
    masters = cursor.fetchall()
    for m in masters:
        doc_id = f"master_{m['id']}"
        topic = f"Мастер: {m['name']} ({m['specialty']})"
        summary = f"Опыт: {m['experience_years']} лет. Рейтинг: {m['rating']}⭐. Описание: {m['bio']}"
        tags = ["мастер", "специалист", "сотрудник", m['name'].lower(), m['specialty'].lower()]
        search.add_document(doc_id, topic, summary, tags)
    print(f"✅ Indexed {len(masters)} masters")
    
    # 3. Index FAQ
    cursor.execute("SELECT id, question, answer FROM faq")
    faqs = cursor.fetchall()
    for f in faqs:
        doc_id = f"faq_{f['id']}"
        topic = f"Частый вопрос: {f['question']}"
        summary = f['answer']
        tags = ["faq", "вопрос", "ответ", "справка"]
        search.add_document(doc_id, topic, summary, tags)
    print(f"✅ Indexed {len(faqs)} FAQ rules")
    
    # 4. Index Working Hours
    cursor.execute("SELECT day_of_week, open_time, close_time FROM working_hours")
    hours = cursor.fetchall()
    summary = "Мы работаем по следующему расписанию:\n"
    for h in hours:
        summary += f"- {h['day_of_week']}: {h['open_time']} - {h['close_time']}\n"
    search.add_document("working_hours", "Расписание работы и часы открытия", summary, ["время", "часы", "график", "расписание", "открыто", "закрыто"])
    print("✅ Indexed working hours")

    conn.close()
    search.close()
    print("🚀 All salon data successfully indexed into Quantum Search Engine!")

if __name__ == "__main__":
    main()
