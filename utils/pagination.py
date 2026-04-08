import math
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_paginated_keyboard(items: list, page: int, per_page: int, id_field: str, name_field: str, prefix: str, page_prefix: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с пагинацией для списков.
    - prefix: префикс для коллбэка самой кнопки (например 'show' даст 'show_15')
    - page_prefix: префикс для кнопок навигации (например 'page_terms_1')
    """
    start_idx = page * per_page
    end_idx = start_idx + per_page
    current_items = items[start_idx:end_idx]
    
    keyboard = []
    
    # кнопки елементів (по 1 в рядку)
    for item in current_items:
        cb_val = f"{prefix}_{item[id_field]}"
        keyboard.append([InlineKeyboardButton(text=str(item[name_field]), callback_data=cb_val[:64])])
        
    total_pages = math.ceil(max(len(items), 1) / per_page)
    
    # кнопки навігації
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"{page_prefix}_{page-1}"))
        else:
            nav_row.append(InlineKeyboardButton(text="—", callback_data="ignore"))
            
        nav_row.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="ignore"))
        
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"{page_prefix}_{page+1}"))
        else:
            nav_row.append(InlineKeyboardButton(text="—", callback_data="ignore"))
            
        keyboard.append(nav_row)
        
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
