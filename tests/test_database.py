import pytest

async def test_add_term_and_duplicate(db):
    # Успішне додавання
    res = await db.add_term("Python", "Мова програмування", "Просто мова", 123, "john")
    assert res is True
    
    # Спроба додати дублікат
    res2 = await db.add_term("Python", "Інший опис", "Інше", 123, "john")
    assert res2 is False
    
    # Перевірка що термін дійсно в базі і тільки один
    terms = await db.list_terms()
    assert len(terms) == 1
    assert terms[0]["name"] == "Python"


async def test_get_term_by_name(db):
    await db.add_term("API", "Application Programming Interface", "", 1, "admin")
    
    term = await db.get_term_by_name("api") # Має працювати навіть з маленькою літери
    assert term is not None
    assert term["name"] == "API"
    
    term_none = await db.get_term_by_name("Unknown")
    assert term_none is None


async def test_fuzzy_search(db):
    await db.add_term("Docker", "Контейнери", "", 1, "admin")
    await db.add_term("Document", "Документація", "", 1, "admin")
    await db.add_term("Apple", "Фрукт", "", 1, "admin")
    
    # Шукаємо "doc"
    results = await db.search_terms("doc")
    assert len(results) == 2
    names = [r["name"] for r in results]
    assert "Docker" in names
    assert "Document" in names
    assert "Apple" not in names


async def test_ratings_and_stats(db):
    # Юзер 100 додає термін
    await db.add_term("Git", "Система контролю версій", "", 100, "user1")
    term = await db.get_term_by_name("Git")
    term_id = term["id"]
    
    # Юзер 200 ставить оцінку 5
    await db.rate_term(term_id, 200, 5)
    
    # Той самий юзер 200 змінює оцінку на 3
    await db.rate_term(term_id, 200, 3)
    
    # Перевіряємо статистику юзера 100
    term_count, avg_rating = await db.get_user_stats(100)
    assert term_count == 1
    assert avg_rating == 3.0 # Має бути 3.0, бо оцінка перезаписалась


async def test_banning_system(db):
    # Перевірка що юзер не забанений спочатку
    assert await db.is_banned(555) is False
    
    # Банимо юзера
    await db.ban_user(555)
    assert await db.is_banned(555) is True
    
    # Спроба забанити знову (не повинна викликати помилку через унікальність)
    await db.ban_user(555)
    assert await db.is_banned(555) is True


async def test_update_and_delete_term(db):
    await db.add_term("React", "Бібліотека", "Для UI", 1, "admin")
    term = await db.get_term_by_name("React")
    term_id = term["id"]
    
    # Оновляємо просте пояснення
    await db.update_term(term_id, "simple", "Для крутого UI")
    updated_term = await db.get_term_by_id(term_id)
    assert updated_term["simple"] == "Для крутого UI"
    
    # Видаляємо термін
    await db.delete_term(term_id)
    deleted_term = await db.get_term_by_id(term_id)
    assert deleted_term is None
