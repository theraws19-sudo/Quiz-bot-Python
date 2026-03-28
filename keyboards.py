from telebot import types


LETTERS = ["A", "B", "C", "D"]


def main_menu() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        types.KeyboardButton("🎮 Начать викторину"),
        types.KeyboardButton("🏆 Таблица лидеров"),
        types.KeyboardButton("📊 Моя статистика"),
        types.KeyboardButton("❓ Помощь"),
    )
    return kb


def categories(category_list: list) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    for cat in category_list:
        kb.add(types.InlineKeyboardButton(cat, callback_data=f"cat_{cat}"))
    kb.add(types.InlineKeyboardButton("🎲 Случайная категория", callback_data="cat_random"))
    return kb


def answers(options: list, question_idx: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(
            f"{LETTERS[i]}. {opt}",
            callback_data=f"ans_{question_idx}_{i}"
        )
        for i, opt in enumerate(options)
    ]
    kb.add(*buttons)
    return kb


def after_game() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🔄 Играть снова", callback_data="play_again"),
        types.InlineKeyboardButton("🏆 Лидеры", callback_data="show_leaders"),
    )
    return kb   