from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from storage.database import Database
from utils.pagination import get_paginated_keyboard

router = Router()
db = Database()

class SearchState(StatesGroup):
    waiting_for_term = State()

class AddTermState(StatesGroup):
    waiting_for_name = State()
    waiting_for_definition = State()
    waiting_for_simple = State()


def main_keyboard(user_id: int = 0) -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="📚 Список термінів"), KeyboardButton(text="🔍 Знайти термін")],
        [KeyboardButton(text="➕ Додати термін"), KeyboardButton(text="📊 Моя статистика")]
    ]
    if user_id == 664778092:
        kb.append([KeyboardButton(text="⚙️ Адмін панель")])
    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
    )

async def format_term_message(term: dict) -> str:
    avg_rating, rating_count = await db.get_term_rating(term['id'])
    
    msg = f"<b>{term['name']}</b>\n\n"
    msg += f"<b>Опис:</b> {term['definition']}\n"
    if term.get('simple'):
         msg += f"<b>Простими словами:</b> {term['simple']}\n\n"
    
    msg += f"👤 <b>Додав(ла):</b> @{term['author_username']}\n"
    if rating_count > 0:
        msg += f"⭐️ <b>Рейтинг:</b> {avg_rating}/5 (Оцінок: {rating_count})"
    else:
        msg += f"⭐️ <b>Рейтинг:</b> Ще немає оцінок"
        
    return msg

def get_rating_keyboard(term_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.button(text=f"{i}⭐️", callback_data=f"rate_{term_id}_{i}")
    builder.adjust(5)
    return builder.as_markup()


@router.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "👋 Вітаю! Я Inter-Tech Glossary Bot.\n"
        "Обери дію нижче:",
        reply_markup=main_keyboard(message.from_user.id),
    )


@router.message(Command("help"))
async def help_handler(message: types.Message) -> None:
    await message.answer(
        "/start — запуск бота\n"
        "/help — список команд\n"
        "📚 Список термінів — показати всі терміни\n"
        "🔍 Знайти термін — пошук терміна\n"
        "➕ Додати термін — додати свій термін\n"
        "📊 Моя статистика — подивитись рейтинг автора"
    )

@router.message(F.text == "📊 Моя статистика")
async def my_stats_handler(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    count, avg_rating = await db.get_user_stats(message.from_user.id)
    await message.answer(
        f"📊 <b>Моя статистика</b>\n\n"
        f"📝 Додано термінів: <b>{count}</b>\n"
        f"⭐️ Середній рейтинг твоїх термінів: <b>{avg_rating}/5</b>"
    )


@router.message(F.text == "➕ Додати термін")
async def add_term_handler(message: types.Message, state: FSMContext) -> None:
    if await db.is_banned(message.from_user.id):
        await message.answer("❌ Адміністратор заборонив тобі додавати нові терміни.")
        return
        
    await message.answer("✍️ Обери назву для нового терміна:\n(Наприклад: <i>Refactoring</i>)")
    await state.set_state(AddTermState.waiting_for_name)

@router.message(AddTermState.waiting_for_name, F.text)
async def process_term_name(message: types.Message, state: FSMContext) -> None:
    name = message.text.strip()
    term = await db.get_term_by_name(name)
    if term:
        await message.answer("❌ Такий термін вже існує. Спробуй іншу назву або скористайся пошуком.")
        await state.clear()
        return
        
    await state.update_data(name=name)
    await message.answer(f"✅ Назва: <b>{name}</b>\n\nТепер напиши детальне або класичне визначення для цього терміна:")
    await state.set_state(AddTermState.waiting_for_definition)

@router.message(AddTermState.waiting_for_definition, F.text)
async def process_term_definition(message: types.Message, state: FSMContext) -> None:
    await state.update_data(definition=message.text.strip())
    await message.answer("✅ Визначення збережено.\n\nТепер поясни це <b>простими словами</b> (як для новачка):")
    await state.set_state(AddTermState.waiting_for_simple)

@router.message(AddTermState.waiting_for_simple, F.text)
async def process_term_simple(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    name = data['name']
    definition = data['definition']
    simple = message.text.strip()
    
    author_id = message.from_user.id
    author_username = message.from_user.username or message.from_user.first_name
    
    success = await db.add_term(name, definition, simple, author_id, author_username)
    if success:
        await message.answer(f"🎉 Термін <b>{name}</b> успішно додано до відкритого словника!")
    else:
        await message.answer("❌ Сталася помилка: можливо, термін уже додали, поки ти писав.")
    
    await state.clear()


@router.message(F.text == "📚 Список термінів")
async def list_terms_handler(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await list_terms_page(message.answer, 0)

@router.callback_query(F.data.startswith("page_terms_"))
async def list_terms_page_cb(callback: types.CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.split("page_terms_")[1])
    try:
        await list_terms_page(callback.message.edit_text, page)
    except Exception:
        pass
    await callback.answer()

async def list_terms_page(send_method, page: int):
    terms = await db.list_terms()
    if not terms:
        await send_method("Поки що немає термінів.")
        return
    
    kbd = get_paginated_keyboard(terms, page, 10, 'id', 'name', 'show', 'page_terms')
    await send_method("Ось доступні терміни. Натисни на будь-який, щоб дізнатися значення:", reply_markup=kbd)

@router.callback_query(F.data.startswith("show_"))
async def term_show_handler(callback: types.CallbackQuery, state: FSMContext) -> None:
    term_id = int(callback.data.split("show_")[1])
    term = await db.get_term_by_id(term_id)
    if not term:
        await callback.answer("Термін не знайдено", show_alert=True)
        return
        
    msg = await format_term_message(term)
    kbd = get_rating_keyboard(term_id)
    
    await callback.message.answer(msg, reply_markup=kbd)
    await callback.answer()


@router.callback_query(F.data.startswith("rate_"))
async def term_rate_handler(callback: types.CallbackQuery, state: FSMContext) -> None:
    _, str_term_id, str_rating = callback.data.split("_")
    term_id = int(str_term_id)
    rating = int(str_rating)
    user_id = callback.from_user.id
    
    term = await db.get_term_by_id(term_id)
    if not term:
        await callback.answer("Цього терміна більше немає.", show_alert=True)
        return
        
    if term['author_id'] == user_id and user_id != 0:
        await callback.answer("Ти не можеш оцінювати свої власні терміни!", show_alert=True)
        return
    
    await db.rate_term(term_id, user_id, rating)
    await callback.answer(f"Твоя оцінка {rating}⭐️ врахована!", show_alert=True)
    
    # оновлюємо повідомлення щоб показати новий рейтинг
    msg = await format_term_message(term)
    kbd = get_rating_keyboard(term_id)
    try:
        await callback.message.edit_text(msg, reply_markup=kbd)
    except Exception:
        pass


@router.message(F.text == "🔍 Знайти термін")
async def find_term_prompt_handler(message: types.Message, state: FSMContext) -> None:
    await message.answer("Напиши назву терміна, який хочеш знайти.")
    await state.set_state(SearchState.waiting_for_term)


@router.message(SearchState.waiting_for_term, F.text)
async def define_term_handler(message: types.Message, state: FSMContext) -> None:
    await process_term_search(message.text.strip(), message.answer)
    await state.clear()


@router.message()
async def fallback_handler(message: types.Message) -> None:
    if not message.text:
        return
    await process_term_search(message.text.strip(), message.answer)
    
async def process_term_search(query: str, send_method):
    term = await db.get_term_by_name(query)
    if term:
        msg = await format_term_message(term)
        kbd = get_rating_keyboard(term['id'])
        await send_method(msg, reply_markup=kbd)
        return
        
    # підхід розумного пошуку
    matches = await db.search_terms(query)
    if matches:
        builder = InlineKeyboardBuilder()
        for m in matches:
            builder.button(text=m['name'], callback_data=f"show_{m['id']}")
        builder.adjust(1)
        await send_method(f"🔍 Я не знайшов точного збігу для <b>{query}</b>.\nМожливо, ви мали на увазі:", reply_markup=builder.as_markup())
    else:
        await send_method("❌ Будь ласка, обери дію на клавіатурі або введи коректну назву терміна.")