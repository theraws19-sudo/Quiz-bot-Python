import json
import random
import time

import telebot

import keyboards as kb
from config import token

# ------------------------------------------------------------
# PROXY CONFIGURATION IS REMOVED – direct connection
# If you need a proxy later, you can uncomment and configure:
# from telebot import apihelper
# apihelper.proxy = {
#     'http': 'socks5://127.0.0.1:1080',
#     'https': 'socks5://127.0.0.1:1080'
# } 
# ------------------------------------------------------------

QUESTIONS_PER_GAME   = 5
POINTS_PER_CORRECT   = 10
TIME_BONUS_THRESHOLD = 10

with open("questions.json", encoding="utf-8") as f:
    QUIZ_DATA: dict = json.load(f)

CATEGORIES = list(QUIZ_DATA.keys())

bot = telebot.TeleBot(token, threaded=False)

user_sessions: dict = {}
leaderboard:   dict = {}
user_names:    dict = {}


def get_user_name(user) -> str:
    name = user.first_name
    if user.last_name:
        name += f" {user.last_name}"
    return name


def progress_bar(current: int, total: int, width: int = 10) -> str:
    filled = int(width * current / total)
    return "[" + "█" * filled + "░" * (width - filled) + "]"


def medal(rank: int) -> str:
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")


def grade_result(pct: int) -> tuple:
    if pct == 100:  return "🏆 Абсолютный чемпион!", "🌟"
    if pct >= 80:   return "🥇 Отличный результат!", "🔥"
    if pct >= 60:   return "🥈 Хороший результат!", "👍"
    if pct >= 40:   return "🥉 Неплохо, но можно лучше!", "💪"
    return "📚 Стоит подучиться!", "🤔"


def init_session(user_id: int, category: str) -> None:
    questions = random.sample(
        QUIZ_DATA[category],
        min(QUESTIONS_PER_GAME, len(QUIZ_DATA[category]))
    )
    user_sessions[user_id] = {
        "category":       category,
        "questions":      questions,
        "current":        0,
        "score":          0,
        "correct":        0,
        "wrong":          0,
        "start_time":     time.time(),
        "question_start": time.time(),
    }


def get_session(user_id: int):
    return user_sessions.get(user_id)


def end_session(user_id: int):
    return user_sessions.pop(user_id, None)


def update_leaderboard(user_id: int, name: str, score: int) -> None:
    if user_id not in leaderboard:
        leaderboard[user_id] = {"name": name, "score": 0, "games": 0, "best": 0}
    entry = leaderboard[user_id]
    entry["score"] += score
    entry["games"] += 1
    entry["name"]   = name
    if score > entry["best"]:
        entry["best"] = score


def get_top_players(n: int = 10) -> list:
    return sorted(leaderboard.items(), key=lambda x: x[1]["score"], reverse=True)[:n]


def send_question(chat_id: int, user_id: int) -> None:
    session = get_session(user_id)
    if not session:
        return

    idx   = session["current"]
    total = len(session["questions"])
    q     = session["questions"][idx]
    cat   = session["category"]

    session["question_start"] = time.time()

    text = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  {cat}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📍 Вопрос {idx + 1} из {total}  {progress_bar(idx, total)}\n"
        f"💰 Очков: {session['score']}\n\n"
        f"❓ <b>{q['question']}</b>"
    )

    bot.send_message(
        chat_id, text,
        parse_mode="HTML",
        reply_markup=kb.answers(q["options"], idx)
    )


def show_leaderboard(chat_id: int) -> None:
    top = get_top_players(10)
    if not top:
        bot.send_message(chat_id, "🏆 Таблица лидеров пока пуста. Сыграй первым!")
        return

    lines = ["🏆 <b>Таблица лидеров</b>\n"]
    for rank, (_, data) in enumerate(top, 1):
        lines.append(
            f"{medal(rank)} <b>{data['name']}</b>\n"
            f"   💎 {data['score']} очков  |  🎮 {data['games']} игр  |  ⭐ лучший: {data['best']}\n"
        )
    bot.send_message(chat_id, "\n".join(lines), parse_mode="HTML")


def show_stats(chat_id: int, user_id: int) -> None:
    data = leaderboard.get(user_id)
    if not data:
        bot.send_message(
            chat_id,
            "📊 Ты ещё не сыграл ни одной игры!\nНажми <b>🎮 Начать викторину</b>",
            parse_mode="HTML"
        )
        return

    top  = get_top_players(1000)
    rank = next((i + 1 for i, (uid, _) in enumerate(top) if uid == user_id), "?")

    text = (
        f"📊 <b>Статистика игрока {data['name']}</b>\n\n"
        f"🏆 Место в рейтинге: <b>#{rank}</b>\n"
        f"💎 Всего очков: <b>{data['score']}</b>\n"
        f"🎮 Игр сыграно: <b>{data['games']}</b>\n"
        f"⭐ Лучший результат: <b>{data['best']}</b>\n"
        f"📈 Среднее за игру: <b>{data['score'] // max(data['games'], 1)}</b>\n"
    )
    bot.send_message(chat_id, text, parse_mode="HTML")


def show_help(chat_id: int) -> None:
    text = (
        "❓ <b>Как играть в QuizMaster?</b>\n\n"
        "1️⃣ Нажми <b>🎮 Начать викторину</b>\n"
        "2️⃣ Выбери категорию (или случайную)\n"
        "3️⃣ Отвечай на вопросы, нажимая на кнопки A/B/C/D\n"
        "4️⃣ За каждый правильный ответ — <b>+10 очков</b>\n\n"
        "⚡ <b>Бонус за скорость:</b> ответишь быстрее 10 секунд — получишь дополнительные очки!\n\n"
        "📋 <b>Команды:</b>\n"
        "/quiz — начать викторину\n"
        "/top — таблица лидеров\n"
        "/stats — твоя статистика\n"
        "/help — эта справка\n\n"
        "Удачи! 🍀"
    )
    bot.send_message(chat_id, text, parse_mode="HTML")


def start_quiz_flow(chat_id: int, user_id: int) -> None:
    if get_session(user_id):
        bot.send_message(chat_id, "⚠️ У тебя уже идёт игра! Сначала заверши её.")
        return
    bot.send_message(
        chat_id,
        "🎲 <b>Выбери категорию вопросов:</b>",
        parse_mode="HTML",
        reply_markup=kb.categories(CATEGORIES)
    )


def finish_game(chat_id: int, user_id: int) -> None:
    session = end_session(user_id)
    if not session:
        return

    total    = len(session["questions"])
    correct  = session["correct"]
    wrong    = session["wrong"]
    score    = session["score"]
    cat      = session["category"]
    duration = int(time.time() - session["start_time"])

    name = user_names.get(user_id, "Игрок")
    update_leaderboard(user_id, name, score)

    pct         = int(correct / total * 100)
    grade, icon = grade_result(pct)
    bar         = progress_bar(correct, total, width=10)

    text = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  {icon} <b>ИГРА ЗАВЕРШЕНА!</b> {icon}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📚 Категория: <b>{cat}</b>\n\n"
        f"📊 <b>Результаты:</b>\n"
        f"  ✅ Правильно: <b>{correct}/{total}</b>  {bar}\n"
        f"  ❌ Неверно:  <b>{wrong}</b>\n"
        f"  ⏱ Время:    <b>{duration} сек.</b>\n\n"
        f"💎 <b>Итоговый счёт: {score} очков</b>\n\n"
        f"🏅 {grade}\n\n"
        f"📈 Всего очков в рейтинге: <b>{leaderboard[user_id]['score']}</b>"
    )

    bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=kb.after_game())


@bot.message_handler(commands=["start"])
def cmd_start(message):
    user = message.from_user
    user_names[user.id] = get_user_name(user)

    text = (
        "🎯 <b>Добро пожаловать в QuizMaster Bot!</b>\n\n"
        "Проверь свои знания в увлекательных викторинах!\n\n"
        "📚 <b>Категории:</b>\n"
        + "\n".join(f"  {cat}" for cat in CATEGORIES) +
        "\n\n"
        "🏆 Зарабатывай очки, бей рекорды и становись чемпионом!\n\n"
        "<i>Используй меню ниже для навигации 👇</i>"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=kb.main_menu())


@bot.message_handler(commands=["help"])
def cmd_help(message):
    show_help(message.chat.id)


@bot.message_handler(commands=["quiz", "start_quiz"])
def cmd_quiz(message):
    user = message.from_user
    user_names[user.id] = get_user_name(user)
    start_quiz_flow(message.chat.id, user.id)


@bot.message_handler(commands=["top", "leaderboard"])
def cmd_top(message):
    show_leaderboard(message.chat.id)


@bot.message_handler(commands=["stats", "me"])
def cmd_stats(message):
    show_stats(message.chat.id, message.from_user.id)


@bot.message_handler(func=lambda m: m.text == "🎮 Начать викторину")
def btn_quiz(message):
    user = message.from_user
    user_names[user.id] = get_user_name(user)
    start_quiz_flow(message.chat.id, user.id)


@bot.message_handler(func=lambda m: m.text == "🏆 Таблица лидеров")
def btn_top(message):
    show_leaderboard(message.chat.id)


@bot.message_handler(func=lambda m: m.text == "📊 Моя статистика")
def btn_stats(message):
    show_stats(message.chat.id, message.from_user.id)


@bot.message_handler(func=lambda m: m.text == "❓ Помощь")
def btn_help(message):
    show_help(message.chat.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("cat_"))
def handle_category(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    user_names[user_id] = get_user_name(call.from_user)

    if get_session(user_id):
        bot.answer_callback_query(call.id, "У тебя уже идёт игра! Сначала заверши её.")
        return

    raw      = call.data[4:]
    category = random.choice(CATEGORIES) if raw == "random" else raw

    if category not in QUIZ_DATA:
        bot.answer_callback_query(call.id, "Неизвестная категория!")
        return

    bot.answer_callback_query(call.id, f"Отлично! {category}")
    bot.edit_message_text(
        f"🚀 Начинаем викторину!\n\n"
        f"Категория: <b>{category}</b>\n"
        f"Вопросов: <b>{QUESTIONS_PER_GAME}</b>\n\n"
        f"Готовься! 💪",
        chat_id,
        call.message.message_id,
        parse_mode="HTML"
    )

    init_session(user_id, category)
    send_question(chat_id, user_id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("ans_"))
def handle_answer(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    session = get_session(user_id)

    if not session:
        bot.answer_callback_query(call.id, "Игра не найдена. Начни новую!")
        return

    _, q_idx_str, chosen_str = call.data.split("_")
    q_idx  = int(q_idx_str)
    chosen = int(chosen_str)

    if q_idx != session["current"]:
        bot.answer_callback_query(call.id, "Ты уже ответил на этот вопрос!")
        return

    q       = session["questions"][q_idx]
    correct = q["answer"]
    elapsed = time.time() - session["question_start"]
    letters = ["A", "B", "C", "D"]

    if chosen == correct:
        bonus = int(TIME_BONUS_THRESHOLD - elapsed) + 1 if elapsed < TIME_BONUS_THRESHOLD else 0
        points     = POINTS_PER_CORRECT + bonus
        speed_line = f"\n⚡ Бонус за скорость: +{bonus} очков!" if bonus else ""

        session["score"]   += points
        session["correct"] += 1

        result_icon = "✅"
        result_text = f"<b>Правильно!</b> +{points} очков{speed_line}"
    else:
        session["wrong"] += 1
        result_icon = "❌"
        result_text = (
            f"<b>Неверно!</b>\n"
            f"Правильный ответ: <b>{letters[correct]}. {q['options'][correct]}</b>"
        )

    try:
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    except Exception:
        pass

    bot.answer_callback_query(call.id, "✅ Правильно!" if chosen == correct else "❌ Неверно!")
    bot.send_message(
        chat_id,
        f"{result_icon} {result_text}\n\n💡 <i>{q['explanation']}</i>",
        parse_mode="HTML"
    )

    session["current"] += 1
    if session["current"] < len(session["questions"]):
        send_question(chat_id, user_id)
    else:
        finish_game(chat_id, user_id)


@bot.callback_query_handler(func=lambda c: c.data == "play_again")
def handle_play_again(call):
    user = call.from_user
    user_names[user.id] = get_user_name(user)
    bot.answer_callback_query(call.id)
    start_quiz_flow(call.message.chat.id, user.id)


@bot.callback_query_handler(func=lambda c: c.data == "show_leaders")
def handle_show_leaders(call):
    bot.answer_callback_query(call.id)
    show_leaderboard(call.message.chat.id)


if __name__ == "__main__":
    print("🤖 QuizMaster Bot запущен!")
    # Direct connection – no proxy
    bot.infinity_polling(timeout=10, long_polling_timeout=5)