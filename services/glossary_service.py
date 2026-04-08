from storage.database import Database
from typing import Dict, List, Optional, Tuple

class GlossaryService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def list_terms_formatted(self) -> str:
        data = await self.db.list_terms()
        if not data:
            return "Поки що немає термінів."
        return "\n".join([f"• {term['name']}" for term in data])

    async def define_term(self, text_query: str) -> str:
        if not text_query or not text_query.strip():
            return "❌ Будь ласка, введи назву терміна."

        term = await self.db.get_term_by_name(text_query.strip())
        if term:
            return term["name"]
            
        return f"❌ Термін <b>{text_query}</b> не знайдено."