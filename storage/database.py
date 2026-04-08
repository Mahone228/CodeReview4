import aiosqlite
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

class Database:
    def __init__(self, db_path: str = "data/db.sqlite3"):
        self.db_path = db_path
        Path("data").mkdir(parents=True, exist_ok=True)

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    action_type TEXT,
                    text TEXT,
                    timestamp DATETIME
                )
            """)
            # таблиця для термінів
            await db.execute("""
                CREATE TABLE IF NOT EXISTS terms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    definition TEXT,
                    simple TEXT,
                    author_id INTEGER,
                    author_username TEXT,
                    created_at DATETIME
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS term_ratings (
                    term_id INTEGER,
                    user_id INTEGER,
                    rating INTEGER,
                    PRIMARY KEY (term_id, user_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS banned_users (
                    user_id INTEGER PRIMARY KEY
                )
            """)
            await db.commit()

    async def log_action(self, user_id: int, username: str, action_type: str, text: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO user_actions (user_id, username, action_type, text, timestamp) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, action_type, text, datetime.now())
            )
            await db.commit()

    async def add_term(self, name: str, definition: str, simple: str, author_id: int, author_username: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("""
                    INSERT INTO terms (name, definition, simple, author_id, author_username, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (name, definition, simple, author_id, author_username, datetime.now()))
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False # термін з такою назвою вже існує

    async def list_terms(self) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT id, name FROM terms ORDER BY name ASC")
            return [dict(row) async for row in cursor]

    async def get_term_by_name(self, name: str) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM terms WHERE LOWER(name) = LOWER(?)", (name,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def search_terms(self, query: str) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT id, name FROM terms WHERE LOWER(name) LIKE LOWER(?) ORDER BY name ASC LIMIT 10", (f"%{query}%",))
            return [dict(row) async for row in cursor]
            
    async def get_term_by_id(self, term_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM terms WHERE id = ?", (term_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def rate_term(self, term_id: int, user_id: int, rating: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO term_ratings (term_id, user_id, rating)
                VALUES (?, ?, ?)
                ON CONFLICT(term_id, user_id) DO UPDATE SET rating=excluded.rating
            """, (term_id, user_id, rating))
            await db.commit()

    async def get_term_rating(self, term_id: int) -> Tuple[float, int]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT AVG(rating), COUNT(rating) FROM term_ratings WHERE term_id = ?", (term_id,))
            row = await cursor.fetchone()
            avg_rating = row[0] if row[0] is not None else 0.0
            count = row[1] if row[1] is not None else 0
            return (round(avg_rating, 2), count)

    async def get_user_stats(self, user_id: int) -> Tuple[int, float]:
        async with aiosqlite.connect(self.db_path) as db:
            # кількість термінів
            cursor = await db.execute("SELECT COUNT(id) FROM terms WHERE author_id = ?", (user_id,))
            term_count = (await cursor.fetchone())[0]
            
            # середній рейтинг їх термінів
            cursor = await db.execute("""
                SELECT AVG(r.rating) 
                FROM term_ratings r
                JOIN terms t ON r.term_id = t.id
                WHERE t.author_id = ?
            """, (user_id,))
            row = await cursor.fetchone()
            avg_rating = row[0] if row[0] is not None else 0.0
            
            return (term_count, round(avg_rating, 2))

    async def is_banned(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT 1 FROM banned_users WHERE user_id = ?", (user_id,))
            return await cursor.fetchone() is not None

    async def ban_user(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO banned_users (user_id) VALUES (?)", (user_id,))
            await db.commit()

    async def get_recent_users(self) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT user_id, username 
                FROM user_actions 
                WHERE user_id IS NOT NULL 
                GROUP BY user_id 
                ORDER BY MAX(timestamp) DESC 
                LIMIT 50
            """)
            return [dict(row) async for row in cursor]

    async def update_term(self, term_id: int, field: str, value: str):
        allowed_fields = ["name", "definition", "simple"]
        if field not in allowed_fields: return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE terms SET {field} = ? WHERE id = ?", (value, term_id))
            await db.commit()

    async def delete_term(self, term_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM terms WHERE id = ?", (term_id,))
            await db.execute("DELETE FROM term_ratings WHERE term_id = ?", (term_id,))
            await db.commit()
