import asyncio
import os
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = "8273704049:AAEeeE50GCsf4ZJ4OMY_NjipwahO7kQSqRY"
GIGACHAT_CREDENTIALS = "MDFhMGJjMTQtYmE5MC03ZGY2LTgwZTMtMGEwNWVkMWQ2YThjOmZmOTJlOWZkLTYyMGItNDkxOC04N2IwLTAzNjM5NzE0OWY3Nw=="

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- Автопоиск модели GigaChat ---
GIGA_MODEL = None

def init_gigachat():
    global GIGACHAT_CREDENTIALS, GIGA_MODEL
    if "ВСТАВЬ_СЮДА" in GIGACHAT_CREDENTIALS:
        logger.error("GIGACHAT_CREDENTIALS не заполнены! Вставь свои credentials в bot.py")
        return None
    try:
        g = GigaChat(credentials=GIGACHAT_CREDENTIALS, verify_ssl_certs=False, scope="GIGACHAT_API_PERS")
        models = g.get_models()
        model_ids = [m.id_ for m in models.data]
        logger.info(f"Доступные модели: {model_ids}")
        if model_ids:
            GIGA_MODEL = model_ids[0]
            logger.info(f"Выбрана модель: {GIGA_MODEL}")
        return g
    except Exception as e:
        logger.error(f"Ошибка инициализации GigaChat: {e}")
        return None

giga = None  # инициализируем в main()

user_roles = {}
user_history = {}
user_materials = {}
user_context = {}
MAX_HISTORY = 10

class GenStates(StatesGroup):
    waiting_subject = State()
    waiting_class = State()
    waiting_topic = State()
    waiting_level = State()
    waiting_student_question = State()
    waiting_parent_topic = State()
    waiting_check_answer = State()

def role_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Я учитель", callback_data="role_teacher")],
        [InlineKeyboardButton(text="Я ученик", callback_data="role_student")],
        [InlineKeyboardButton(text="Я родитель", callback_data="role_parent")],
    ])

def teacher_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Создать тест"), KeyboardButton(text="План урока")],
        [KeyboardButton(text="Раздаточные карточки"), KeyboardButton(text="Проверить работу")],
        [KeyboardButton(text="Мои материалы"), KeyboardButton(text="Сменить роль")],
    ], resize_keyboard=True)

def student_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Объяснить тему")],
        [KeyboardButton(text="Мини-тест"), KeyboardButton(text="Разбор ошибок")],
        [KeyboardButton(text="Мои материалы"), KeyboardButton(text="Сменить роль")],
    ], resize_keyboard=True)

def parent_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Помощник ДЗ")],
        [KeyboardButton(text="Объяснить тему ребенку")],
        [KeyboardButton(text="Тренировочные задания")],
        [KeyboardButton(text="Сменить роль")],
    ], resize_keyboard=True)

def level_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Базовый"), KeyboardButton(text="Средний")],
        [KeyboardButton(text="Продвинутый")],
    ], resize_keyboard=True)

SYSTEM_PROMPTS = {
    "teacher": "Ты - методический помощник ПроСвет для учителя. Создавай готовые педагогические материалы по стандартам ФГОС. Тесты - с ключами и критериями оценивания. Планы уроков - с этапами, целями и раздаточными материалами. Карточки - компактные, с заданием и образцом ответа. Всегда указывай тему, класс и уровень сложности.",
    "student": "Ты - дружелюбный помощник ПроСвет для ученика. Объясняй темы простыми словами, как старший товарищ. Если даешь мини-тест - 5-7 коротких задач с ответами. Разбирай ошибки понятно, без сложных терминов. Поддерживай и хвали за старание.",
    "parent": "Ты - помощник ПроСвет для родителя. Объясняй школьные темы простыми словами, чтобы родитель мог помочь ребенку. Давай 3-4 тренировочных задания с ответами. Не решай за ребенка - подсказывай, как помочь. Будь теплым и поддерживающим.",
}

def build_messages(user_id, user_text, extra_system=""):
    role = user_roles.get(user_id, "student")
    history = user_history.get(user_id, [])
    system_text = SYSTEM_PROMPTS.get(role, SYSTEM_PROMPTS["student"])
    if extra_system:
        system_text += "\n\n" + extra_system
    messages = [Messages(role=MessagesRole.SYSTEM, content=system_text)]
    messages.extend(history)
    messages.append(Messages(role=MessagesRole.USER, content=user_text))
    return messages

def save_history(user_id, user_text, bot_answer):
    if user_id not in user_history:
        user_history[user_id] = []
    user_history[user_id].append(Messages(role=MessagesRole.USER, content=user_text))
    user_history[user_id].append(Messages(role=MessagesRole.ASSISTANT, content=bot_answer))
    if len(user_history[user_id]) > MAX_HISTORY * 2:
        user_history[user_id] = user_history[user_id][-MAX_HISTORY * 2:]

def save_material(user_id, material_type, subject, class_num, topic, content):
    if user_id not in user_materials:
        user_materials[user_id] = []
    user_materials[user_id].append({"type": material_type, "subject": subject, "class": class_num, "topic": topic, "content": content, "date": datetime.now().strftime("%d.%m.%Y %H:%M")})

def ask_gigachat(user_id, user_text, extra_system=""):
    global giga, GIGA_MODEL
    if giga is None:
        raise RuntimeError("GigaChat не инициализирован. Проверь credentials.")
    messages = build_messages(user_id, user_text, extra_system)
    if GIGA_MODEL:
        payload = Chat(messages=messages, model=GIGA_MODEL)
    else:
        payload = Chat(messages=messages)
    response = giga.chat(payload)
    answer = response.choices[0].message.content
    save_history(user_id, user_text, answer)
    return answer

@dp.message(Command("start"))
async def cmd_start(message, state):
    await state.clear()
    user_id = message.from_user.id
    user_history.pop(user_id, None)
    user_context.pop(user_id, None)
    await message.answer("Привет! Я <b>ПроСвет</b> - ИИ-помощник для школы.\n\nЯ помогаю:\n- Учителям: тесты, планы, карточки, автопроверка\n- Ученикам: объяснения, мини-тесты, разбор ошибок\n- Родителям: помощь с ДЗ и объяснения\n\nВыбери, кто ты:", reply_markup=role_keyboard())

@dp.callback_query(F.data == "change_role")
async def cq_change_role(callback, state):
    await state.clear()
    user_id = callback.from_user.id
    user_roles.pop(user_id, None)
    user_context.pop(user_id, None)
    await callback.message.edit_text("Выбери свою роль:", reply_markup=role_keyboard())
    await callback.answer()

@dp.callback_query(F.data.startswith("role_"))
async def cq_set_role(callback, state):
    role = callback.data.replace("role_", "")
    user_id = callback.from_user.id
    user_roles[user_id] = role
    await state.clear()
    if role == "teacher":
        text = "Ты в режиме <b>учителя</b>. Доступные модули:\n- Создать тест (3 уровня)\n- План урока\n- Раздаточные карточки\n- Проверить работу\n- Мои материалы"
        kb = teacher_keyboard()
    elif role == "student":
        text = "Ты в режиме <b>ученика</b>. Доступные модули:\n- Объяснить тему\n- Мини-тест (5-7 задач)\n- Разбор ошибок\n- Мои материалы"
        kb = student_keyboard()
    else:
        text = "Вы в режиме <b>родителя</b>. Доступные модули:\n- Помощник ДЗ\n- Объяснить тему ребенку\n- Тренировочные задания"
        kb = parent_keyboard()
    await callback.message.answer(text, reply_markup=kb)
    await callback.message.delete()
    await callback.answer()

@dp.message(F.text == "Сменить роль")
async def btn_change_role(message, state):
    await state.clear()
    user_id = message.from_user.id
    user_roles.pop(user_id, None)
    user_context.pop(user_id, None)
    await message.answer("Выбери свою роль:", reply_markup=role_keyboard())

@dp.message(F.text == "Создать тест")
async def teacher_test_start(message, state):
    if user_roles.get(message.from_user.id) != "teacher":
        await message.answer("Это функция для учителей. Смени роль.")
        return
    user_context[message.from_user.id] = {"material_type": "test"}
    await state.set_state(GenStates.waiting_subject)
    await message.answer("Введи предмет:")

@dp.message(F.text == "План урока")
async def teacher_lesson_start(message, state):
    if user_roles.get(message.from_user.id) != "teacher":
        await message.answer("Это функция для учителей. Смени роль.")
        return
    user_context[message.from_user.id] = {"material_type": "lesson_plan"}
    await state.set_state(GenStates.waiting_subject)
    await message.answer("Введи предмет:")

@dp.message(F.text == "Раздаточные карточки")
async def teacher_cards_start(message, state):
    if user_roles.get(message.from_user.id) != "teacher":
        await message.answer("Это функция для учителей. Смени роль.")
        return
    user_context[message.from_user.id] = {"material_type": "cards"}
    await state.set_state(GenStates.waiting_subject)
    await message.answer("Введи предмет:")

@dp.message(F.text == "Проверить работу")
async def teacher_check_start(message, state):
    if user_roles.get(message.from_user.id) != "teacher":
        await message.answer("Это функция для учителей. Смени роль.")
        return
    user_context[message.from_user.id] = {"material_type": "check"}
    await state.set_state(GenStates.waiting_subject)
    await message.answer("Введи предмет:")

@dp.message(GenStates.waiting_subject)
async def gen_subject(message, state):
    user_context[message.from_user.id]["subject"] = message.text
    await state.set_state(GenStates.waiting_class)
    await message.answer("Введи класс (например: 5, 8, 11):")

@dp.message(GenStates.waiting_class)
async def gen_class(message, state):
    user_context[message.from_user.id]["class"] = message.text
    await state.set_state(GenStates.waiting_topic)
    await message.answer("Введи тему:")

@dp.message(GenStates.waiting_topic)
async def gen_topic(message, state):
    ctx = user_context[message.from_user.id]
    ctx["topic"] = message.text
    mat_type = ctx["material_type"]
    if mat_type == "test":
        await state.set_state(GenStates.waiting_level)
        await message.answer("Выбери уровень сложности:", reply_markup=level_keyboard())
    elif mat_type == "check":
        await state.set_state(GenStates.waiting_check_answer)
        await message.answer("Вставь текст работы ученика:")
    else:
        await generate_material(message, state)

@dp.message(GenStates.waiting_level)
async def gen_level(message, state):
    level_map = {"Базовый": "базовый", "Средний": "средний", "Продвинутый": "продвинутый"}
    level = level_map.get(message.text, "средний")
    user_context[message.from_user.id]["level"] = level
    await generate_material(message, state)

@dp.message(GenStates.waiting_check_answer)
async def gen_check_work(message, state):
    ctx = user_context[message.from_user.id]
    prompt = f"Проверь работу ученика по предмету {ctx['subject']}, класс {ctx['class']}, тема {ctx['topic']}.\nТекст работы:\n{message.text}\n\nДай развернутую проверку: оцени работу, укажи ошибки, объясни, что не так, подскажи, как исправить. В конце дай итоговую оценку по 5-балльной системе."
    await message.answer("Проверяю работу...", reply_markup=teacher_keyboard())
    try:
        answer = await asyncio.to_thread(ask_gigachat, message.from_user.id, prompt)
        save_material(message.from_user.id, "Проверка работы", ctx['subject'], ctx['class'], ctx['topic'], answer)
        await message.answer(answer)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer("Не удалось проверить работу. Попробуй позже.")
    finally:
        await state.clear()
        user_context.pop(message.from_user.id, None)

async def generate_material(message, state):
    ctx = user_context[message.from_user.id]
    mat_type = ctx["material_type"]
    subject = ctx["subject"]
    class_num = ctx["class"]
    topic = ctx["topic"]
    level = ctx.get("level", "средний")
    if mat_type == "test":
        prompt = f"Создай тест по предмету {subject} для {class_num} класса. Тема: {topic}. Уровень: {level}. Тест: 8-10 заданий (4-5 с выбором, 3-4 с кратким ответом, 1-2 с развернутым). В конце укажи ключи и критерии оценивания."
        mat_name = f"Тест ({level})"
    elif mat_type == "lesson_plan":
        prompt = f"Составь план урока по предмету {subject} для {class_num} класса. Тема: {topic}. Включи: цели, этапы (орг. момент, актуализация, изучение нового, закрепление, рефлексия, ДЗ), методы и формы работы, раздаточные материалы."
        mat_name = "План урока"
    elif mat_type == "cards":
        prompt = f"Создай 5-6 раздаточных карточек по предмету {subject} для {class_num} класса. Тема: {topic}. Каждая карточка: номер, краткое задание, образец ответа. Компактные, для печати."
        mat_name = "Раздаточные карточки"
    else:
        await state.clear()
        user_context.pop(message.from_user.id, None)
        return
    await message.answer("Генерирую материал...", reply_markup=teacher_keyboard())
    try:
        answer = await asyncio.to_thread(ask_gigachat, message.from_user.id, prompt)
        save_material(message.from_user.id, mat_name, subject, class_num, topic, answer)
        await message.answer(answer)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer("Не удалось создать материал. Попробуй позже.")
    finally:
        await state.clear()
        user_context.pop(message.from_user.id, None)

@dp.message(F.text == "Объяснить тему")
async def student_explain(message, state):
    if user_roles.get(message.from_user.id) != "student":
        await message.answer("Это функция для учеников. Смени роль.")
        return
    await state.set_state(GenStates.waiting_student_question)
    await message.answer("Напиши тему или вопрос - объясню простыми словами!")

@dp.message(GenStates.waiting_student_question)
async def student_explain_handler(message, state):
    prompt = f"Объясни тему простыми словами, как старший товарищ. Используй примеры из жизни. В конце задай 1-2 проверочных вопроса.\n\nТема: {message.text}"
    await message.answer("Объясняю...", reply_markup=student_keyboard())
    try:
        answer = await asyncio.to_thread(ask_gigachat, message.from_user.id, prompt)
        save_material(message.from_user.id, "Объяснение темы", "-", "-", message.text, answer)
        await message.answer(answer)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer("Не удалось получить объяснение. Попробуй позже.")
    finally:
        await state.clear()

@dp.message(F.text == "Мини-тест")
async def student_test(message):
    if user_roles.get(message.from_user.id) != "student":
        await message.answer("Это функция для учеников. Смени роль.")
        return
    prompt = "Создай мини-тест из 5-7 коротких задач по теме, которую мы обсуждали. Если темы не было - спроси, по какой теме сделать тест. В конце укажи правильные ответы."
    await message.answer("Готовлю мини-тест...")
    try:
        answer = await asyncio.to_thread(ask_gigachat, message.from_user.id, prompt)
        save_material(message.from_user.id, "Мини-тест", "-", "-", "По последней теме", answer)
        await message.answer(answer)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer("Не удалось создать тест. Попробуй позже.")

@dp.message(F.text == "Разбор ошибок")
async def student_errors(message, state):
    if user_roles.get(message.from_user.id) != "student":
        await message.answer("Это функция для учеников. Смени роль.")
        return
    await state.set_state(GenStates.waiting_student_question)
    await message.answer("Опиши, в чем ошибся - разберем подробно и дам похожие задачи для закрепления.")

@dp.message(F.text == "Помощник ДЗ")
async def parent_hw(message, state):
    if user_roles.get(message.from_user.id) != "parent":
        await message.answer("Это функция для родителей. Смени роль.")
        return
    await state.set_state(GenStates.waiting_parent_topic)
    await message.answer("Опишите домашнее задание или тему - дам простое объяснение и 3-4 тренировочных задания с ответами.")

@dp.message(F.text == "Объяснить тему ребенку")
async def parent_explain(message, state):
    if user_roles.get(message.from_user.id) != "parent":
        await message.answer("Это функция для родителей. Смени роль.")
        return
    await state.set_state(GenStates.waiting_parent_topic)
    await message.answer("Напишите тему - объясню так, чтобы вы могли понятно рассказать ребенку.")

@dp.message(F.text == "Тренировочные задания")
async def parent_tasks(message, state):
    if user_roles.get(message.from_user.id) != "parent":
        await message.answer("Это функция для родителей. Смени роль.")
        return
    await state.set_state(GenStates.waiting_parent_topic)
    await message.answer("Напишите тему - подготовлю 3-4 коротких задания с ответами для тренировки.")

@dp.message(GenStates.waiting_parent_topic)
async def parent_topic_handler(message, state):
    prompt = f"Помоги родителю объяснить ребенку. Дай простое объяснение темы и 3-4 тренировочных задания с ответами. Не решай за ребенка - подсказывай, как помочь.\n\nТема: {message.text}"
    await message.answer("Готовлю материал...", reply_markup=parent_keyboard())
    try:
        answer = await asyncio.to_thread(ask_gigachat, message.from_user.id, prompt)
        save_material(message.from_user.id, "Помощник ДЗ", "-", "-", message.text, answer)
        await message.answer(answer)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer("Не удалось подготовить материал. Попробуйте позже.")
    finally:
        await state.clear()

@dp.message(F.text == "Мои материалы")
async def show_materials(message):
    user_id = message.from_user.id
    materials = user_materials.get(user_id, [])
    if not materials:
        await message.answer("Папка материалов пока пуста. Создай что-нибудь!")
        return
    text = "<b>Материалы от ПроСвет</b>:\n\n"
    for i, mat in enumerate(materials[-10:], 1):
        text += f"{i}. <b>{mat['type']}</b> - {mat['subject']}, {mat['class']} кл.\n   Тема: {mat['topic']}\n   {mat['date']}\n\n"
    text += f"Всего сохранено: {len(materials)}"
    await message.answer(text)

@dp.message()
async def handle_text(message, state):
    user_id = message.from_user.id
    role = user_roles.get(user_id)
    if not role:
        await message.answer("Сначала выбери роль:", reply_markup=role_keyboard())
        return
    current_state = await state.get_state()
    if current_state is not None:
        return
    text = message.text
    if not text:
        await message.answer("Я понимаю только текстовые сообщения.")
        return
    await message.answer("Думаю...")
    try:
        answer = await asyncio.to_thread(ask_gigachat, user_id, text)
        await message.answer(answer)
    except Exception as e:
        logger.error(f"Ошибка GigaChat для {user_id}: {e}")
        await message.answer("Не удалось получить ответ. Попробуй позже.")

async def main():
    global giga
    logger.info("Бот ПроСвет запущен! Инициализация GigaChat...")
    giga = init_gigachat()
    if giga is None:
        logger.error("GigaChat не инициализирован! Бот запустится, но ответы не будут работать.")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
