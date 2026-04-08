import pytest
import os
from storage.database import Database

@pytest.fixture
async def db():
    # Використовуємо тимчасовий файл, щоб тести не мішали оригінальній базі
    test_db_path = "test_db.sqlite3"
    
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
        
    database = Database(db_path=test_db_path)
    await database.init_db()
    
    yield database
    
    # Прибирання після тесту
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
