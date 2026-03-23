import json
import aiosqlite
from typing import Any, Dict, Optional
from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType


class SQLiteStorage(BaseStorage):
    """FSM storage на основе SQLite — переживает перезапуски бота"""

    def __init__(self, db_path: str = "salon.db"):
        self.db_path = db_path
        self._initialized = False

    async def _ensure_table(self):
        if self._initialized:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS fsm_state (
                    key TEXT PRIMARY KEY,
                    state TEXT,
                    data TEXT NOT NULL DEFAULT '{}'
                )
            """)
            await db.commit()
        self._initialized = True

    def _make_key(self, key: StorageKey) -> str:
        return f"{key.bot_id}:{key.chat_id}:{key.user_id}:{key.destiny}"

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        await self._ensure_table()
        state_str = state.state if hasattr(state, "state") else state
        k = self._make_key(key)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO fsm_state (key, state) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET state = excluded.state
            """, (k, state_str))
            await db.commit()

    async def get_state(self, key: StorageKey) -> Optional[str]:
        await self._ensure_table()
        k = self._make_key(key)
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT state FROM fsm_state WHERE key = ?", (k,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        await self._ensure_table()
        k = self._make_key(key)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO fsm_state (key, data) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET data = excluded.data
            """, (k, json.dumps(data)))
            await db.commit()

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        await self._ensure_table()
        k = self._make_key(key)
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT data FROM fsm_state WHERE key = ?", (k,)
            )
            row = await cursor.fetchone()
            return json.loads(row[0]) if row and row[0] else {}

    async def close(self) -> None:
        pass
