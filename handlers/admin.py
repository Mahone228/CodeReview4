from aiogram import Router, types, F
from aiogram.filters import Command, Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from handlers.commands import db, format_term_message
from utils.pagination import get_paginated_keyboard

router = Router()

ADMIN_ID = 664778092

class AdminState(StatesGroup):
    waiting_for_ban_id = State()
    waiting_for_term_update = State()

class IsAdminFilter(Filter):
    async def __call__(self, event: types.Message | types.CallbackQuery) -> bool:
        return event.from_user.id == ADMIN_ID

# захист маршрутів у цьому обробнику фільтрацією на рівні маршрутизатора
# це гарантує, що не-адміни просто проваляться до наступного маршрутизатора замість відхилення події
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


@router.message(F.text == "⚙️ Адмін панель")
async def admin_menu_handler(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Користувачі (Бан)", callback_data="admin_users")
    builder.button(text="🔧 Модерація термінів", callback_data="admin_terms")
    builder.adjust(1)
    
    await message.answer("🛠 <b>Адмін Панель</b>\nОберіть дію:", reply_markup=builder.as_markup())


@router.callback_query(F.data == "admin_users")
async def admin_users_handler(callback: types.CallbackQuery, state: FSMContext) -> None:
    await admin_users_page(callback.message.edit_text, 0)
    await callback.answer()

@router.callback_query(F.data.startswith("page_users_"))
async def admin_users_page_cb(callback: types.CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.split("page_users_")[1])
    try:
        await admin_users_page(callback.message.edit_text, page)
    except Exception:
        pass
    await callback.answer()

async def admin_users_page(send_method, page: int):
    # пагінація відображає лише перші 50 записів з бази
    users = await db.get_recent_users()
    if not users:
        await send_method("Немає користувачів.")
        return
        
    # використовуємо логіку пагінації для текстового списку, як просив користувач
    per_page = 10
    start_idx = page * per_page
    end_idx = start_idx + per_page
    current_users = users[start_idx:end_idx]
    
    msg = f"👥 <b>Користувачі (стор. {page+1}):</b>\n\n"
    for u in current_users:
        banned = " [ЗАБАНЕНИЙ]" if await db.is_banned(u['user_id']) else ""
        msg += f"• @{u['username']} (ID: <code>{u['user_id']}</code>){banned}\n"
        
    builder = InlineKeyboardBuilder()
    
    # кастомна навігація сторінок для текстового повідомлення
    total_pages = (len(users) + per_page - 1) // per_page
    nav_row = []
    if total_pages > 1:
        if page > 0: nav_row.append(builder.button(text="⬅️", callback_data=f"page_users_{page-1}").buttons[-1])
        if page < total_pages - 1: nav_row.append(builder.button(text="➡️", callback_data=f"page_users_{page+1}").buttons[-1])
    
    builder.button(text="🔨 Забанити юзера", callback_data="admin_ban_prompt")
    
    # розміщуємо навігацію в один рядок, а кнопку бану під нею
    if nav_row:
        builder.adjust(len(nav_row), 1)
    else:
        builder.adjust(1)
        
    await send_method(msg, reply_markup=builder.as_markup())

@router.callback_query(F.data == "admin_ban_prompt")
async def admin_ban_prompt(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer("Напиши ID користувача для бану:")
    await state.set_state(AdminState.waiting_for_ban_id)
    await callback.answer()

@router.message(AdminState.waiting_for_ban_id, F.text)
async def admin_ban_process(message: types.Message, state: FSMContext) -> None:
    try:
        user_id = int(message.text.strip())
        if user_id == ADMIN_ID:
            await message.answer("❌ Себе забанити не можна!")
            return
            
        await db.ban_user(user_id)
        await message.answer(f"✅ Користувача {user_id} забанено. Він більше не зможе додавати терміни.")
    except ValueError:
        await message.answer("❌ Некоректний ID. Введи число.")
    await state.clear()


@router.callback_query(F.data == "admin_terms")
async def admin_terms_handler(callback: types.CallbackQuery, state: FSMContext) -> None:
    await admin_terms_page(callback.message.edit_text, 0)
    await callback.answer()

@router.callback_query(F.data.startswith("page_mod_"))
async def admin_terms_page_cb(callback: types.CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.split("page_mod_")[1])
    try:
        await admin_terms_page(callback.message.edit_text, page)
    except Exception:
        pass
    await callback.answer()

async def admin_terms_page(send_method, page: int):
    terms = await db.list_terms()
    if not terms:
        await send_method("Немає термінів.")
        return
        
    kbd = get_paginated_keyboard(terms, page, 10, 'id', 'name', 'mod_show', 'page_mod')
    await send_method("🔧 Оберіть термін для модерації:", reply_markup=kbd)

@router.callback_query(F.data.startswith("mod_show_"))
async def mod_show_term(callback: types.CallbackQuery, state: FSMContext) -> None:
    term_id = int(callback.data.split("mod_show_")[1])
    term = await db.get_term_by_id(term_id)
    if not term:
        await callback.answer("Термін не знайдено", show_alert=True)
        return
        
    msg = await format_term_message(term)
    
    builder = InlineKeyboardBuilder()
    # кнопки редагування
    builder.button(text="✏️ Назва", callback_data=f"mod_edit_{term_id}_name")
    builder.button(text="✏️ Опис", callback_data=f"mod_edit_{term_id}_definition")
    builder.button(text="✏️ Простими", callback_data=f"mod_edit_{term_id}_simple")
    # кнопка видалення
    builder.button(text="🗑 Видалити", callback_data=f"mod_del_{term_id}")
    builder.adjust(3, 1)
    
    await callback.message.answer(msg, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("mod_del_"))
async def mod_del_term(callback: types.CallbackQuery, state: FSMContext) -> None:
    term_id = int(callback.data.split("mod_del_")[1])
    await db.delete_term(term_id)
    await callback.message.edit_text(callback.message.html_text + "\n\n<b>[🗑 ТЕРМІН ВИДАЛЕНО]</b>")
    await callback.answer("Термін видалено!", show_alert=True)

@router.callback_query(F.data.startswith("mod_edit_"))
async def mod_edit_prompt(callback: types.CallbackQuery, state: FSMContext) -> None:
    _, _, term_id, field = callback.data.split("_")
    await state.update_data(mod_term_id=int(term_id), mod_field=field)
    await callback.message.answer(f"Напиши новий текст для поля <b>{field}</b>:")
    await state.set_state(AdminState.waiting_for_term_update)
    await callback.answer()

@router.message(AdminState.waiting_for_term_update, F.text)
async def mod_edit_process(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    term_id = data['mod_term_id']
    field = data['mod_field']
    new_value = message.text.strip()
    
    await db.update_term(term_id, field, new_value)
    
    await message.answer(f"✅ Термін оновлено! Нове значення збережено.")
    # показуємо це знову
    term = await db.get_term_by_id(term_id)
    if term:
        msg = await format_term_message(term)
        await message.answer("Поточний вигляд:\n" + msg)
    await state.clear()
