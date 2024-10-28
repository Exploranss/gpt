import telebot
import requests
import json
import logging
import time
import sqlite3
from googletrans import Translator
from telebot import types
from concurrent.futures import ThreadPoolExecutor
import pytesseract
from PIL import Image
import os 
import cv2
import docx
import PyPDF2
from google.cloud import speech_v1p1beta1 as speech
import io

# Настройки логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен вашего Telegram-бота
bot = telebot.TeleBot("7766574233:AAGmft91MSwXpubvTfAFhaVZFWGRPbYRMdU")

# API ключ для OpenAI
openai_api_key = "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"

# API ключ для Prodia
prodia_api_key = "97df967b-62e0-42ed-a232-72bd5ae7e3c9"

# URL для запроса к OpenAI
openai_url = "https://openrouter.ai/api/v1/chat/completions"

# Заголовки запроса к OpenAI
openai_headers = {
    "Authorization": f"Bearer {openai_api_key}",
    "HTTP-Referer": "https://your-site-url.com",  # Замените на ваш сайт URL
    "X-Title": "Your App Name",  # Замените на название вашего приложения
    "Content-Type": "application/json"
}

# Хранение контекста для каждого пользователя
user_context = {}

# Хранение состояния для каждого пользователя (0 - режим ИИ, 1 - режим создания изображений, 2 - работа с документами)
user_state = {}

# Хранение выбранных параметров для каждого пользователя
user_params = {}

# Смайлик песочных часов
waiting_message = "⏳"

# Список моделей и стилей
models = [
    "absolutereality_v181.safetensors [3d9d4d2b]",
    "anything-v4.5-pruned.ckpt [65745d25]",
    "AOM3A3_orangemixs.safetensors [9600da17]",
    "deliberate_v2.safetensors [10ec4b29]",
    "dreamlike-photoreal-2.0.safetensors [fdcf65e7]",
    "dreamshaper_8.safetensors [9d40847d]",
    "edgeOfRealism_eorV20.safetensors [3ed5de15]",
    "elldreths-vivid-mix.safetensors [342d9d26]",
    "epicrealism_naturalSinRC1VAE.safetensors [90a4c676]",
    "juggernaut_aftermath.safetensors [5e20c455]",
    "lyriel_v16.safetensors [68fceea2]",
    "meinamix_meinaV11.safetensors [b56ce717]",
    "openjourney_V4.ckpt [ca2f377f]",
    "protogenx34.safetensors [5896f8d5]",
    "Realistic_Vision_V5.0.safetensors [614d1063]",
    "redshift_diffusion-V10.safetensors [1400e684]",
    "rundiffusionFX25D_v10.safetensors [cd12b0ee]",
    "rundiffusionFX_v10.safetensors [cd4e694d]",
    "v1-5-pruned-emaonly.safetensors [d7049739]",
    "shoninsBeautiful_v10.safetensors [25d8c546]",
    "theallys-mix-ii-churned.safetensors [5d9225a4]",
    "timeless-1.0.ckpt [7c4971d4]",
    "toonyou_beta6.safetensors [980f6b15]"
]

style_presets = [
    "3d-model",
    "analog-film",
    "anime",
    "cinematic",
    "comic-book",
    "digital-art",
    "enhance",
    "fantasy-art",
    "isometric",
    "line-art",
    "low-poly",
    "neon-punk",
    "origami",
    "photographic",
    "pixel-art",
    "texture",
    "craft-clay"
]

# Перевод названий моделей и стилей на русский язык
models_translation = {
    "absolutereality_v181.safetensors [3d9d4d2b]": "Абсолютная реальность v1.81",
    "anything-v4.5-pruned.ckpt [65745d25]": "Что угодно v4.5",
    "AOM3A3_orangemixs.safetensors [9600da17]": "Апельсиновый микс",
    "deliberate_v2.safetensors [10ec4b29]": "Осознанный v2",
    "dreamlike-photoreal-2.0.safetensors [fdcf65e7]": "Фотореализм мечты 2.0",
    "dreamshaper_8.safetensors [9d40847d]": "Мечтатель 8",
    "edgeOfRealism_eorV20.safetensors [3ed5de15]": "Край реализма v2.0",
    "elldreths-vivid-mix.safetensors [342d9d26]": "Яркий микс Эллдрета",
    "epicrealism_naturalSinRC1VAE.safetensors [90a4c676]": "Эпический реализм",
    "juggernaut_aftermath.safetensors [5e20c455]": "Джаггернаут: Послевкусие",
    "lyriel_v16.safetensors [68fceea2]": "Лириэль v1.6",
    "meinamix_meinaV11.safetensors [b56ce717]": "Мейна v11",
    "openjourney_V4.ckpt [ca2f377f]": "Открытый путь v4",
    "protogenx34.safetensors [5896f8d5]": "Протоген x34",
    "Realistic_Vision_V5.0.safetensors [614d1063]": "Реалистичное видение v5.0",
    "redshift_diffusion-V10.safetensors [1400e684]": "Красное смещение v10",
    "rundiffusionFX25D_v10.safetensors [cd12b0ee]": "Рандиффузия FX 2.5D v10",
    "rundiffusionFX_v10.safetensors [cd4e694d]": "Рандиффузия FX v10",
    "v1-5-pruned-emaonly.safetensors [d7049739]": "v1.5 обрезанный",
    "shoninsBeautiful_v10.safetensors [25d8c546]": "Шонин: Красота v10",
    "theallys-mix-ii-churned.safetensors [5d9225a4]": "Микс Аллиса II",
    "timeless-1.0.ckpt [7c4971d4]": "Бессмертный v1.0",
    "toonyou_beta6.safetensors [980f6b15]": "Тунун: Бета 6"
}

style_presets_translation = {
    "3d-model": "3D модель",
    "analog-film": "Аналоговая пленка",
    "anime": "Аниме",
    "cinematic": "Кинематографический",
    "comic-book": "Комикс",
    "digital-art": "Цифровое искусство",
    "enhance": "Улучшение",
    "fantasy-art": "Фантастическое искусство",
    "isometric": "Изометрический",
    "line-art": "Линейный рисунок",
    "low-poly": "Низкополигональный",
    "neon-punk": "Неоновый панк",
    "origami": "Оригами",
    "photographic": "Фотографический",
    "pixel-art": "Пиксель-арт",
    "texture": "Текстура",
    "craft-clay": "Керамическая глина"
}

# Переводчик
translator = Translator()

# База данных SQLite
DATABASE_NAME = '1bot_database.db'

def create_tables():
    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        
        # Таблица пользователей
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (user_id INTEGER PRIMARY KEY, username TEXT, chat_id INTEGER, UNIQUE(username, chat_id))''')
        
        # Таблица запросов
        c.execute('''CREATE TABLE IF NOT EXISTS requests
                     (request_id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, chat_id INTEGER, request_text TEXT)''')
        
        # Таблица изображений
        c.execute('''CREATE TABLE IF NOT EXISTS images
                     (image_id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, chat_id INTEGER, request_text TEXT, image_url TEXT)''')
        
        conn.commit()

create_tables()

# Пул потоков для выполнения запросов к базе данных
executor = ThreadPoolExecutor(max_workers=5)

# Добавление пользователя в базу данных
def add_user_to_db(user_id, username, chat_id):
    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (user_id, username, chat_id) VALUES (?, ?, ?)", (user_id, username, chat_id))
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # Пользователь уже существует

def add_image_to_db(username, chat_id, request_text, image_url):
    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO images (username, chat_id, request_text, image_url) VALUES (?, ?, ?, ?)", (username, chat_id, request_text, image_url))
        conn.commit()

# Добавление запроса в базу данных
def add_request_to_db(username, chat_id, request_text):
    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO requests (username, chat_id, request_text) VALUES (?, ?, ?)", (username, chat_id, request_text))
        conn.commit()

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    chat_id = message.chat.id
    
    add_user_to_db(user_id, username, chat_id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Режим ИИ", "Режим изображений", "Работа с документами", "Очистить контекст")
    bot.reply_to(message, 'Привет! Я готов к работе. Выберите режим работы.', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Работа с документами")
def set_document_mode(message):
    user_id = message.from_user.id
    user_state[user_id] = 2
    bot.reply_to(message, 'Режим работы с документами активирован. Пожалуйста, отправьте документ (Word или PDF).')

@bot.message_handler(func=lambda message: message.text == "Очистить контекст")
def clear_context(message):
    user_id = message.from_user.id
    if user_id in user_context:
        del user_context[user_id]
    if user_id in user_params:
        del user_params[user_id]
    bot.reply_to(message, 'Контекст очищен.')

@bot.message_handler(func=lambda message: message.text == "Режим ИИ")
def set_ai_mode(message):
    user_id = message.from_user.id
    user_state[user_id] = 0
    bot.reply_to(message, 'Режим ИИ активирован.')

# Путь к исполняемому файлу Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Функция для анализа изображения
def analyze_image(image_path):
    # Загружаем изображение с помощью OpenCV
    image = cv2.imread(image_path)

    # Преобразуем изображение в оттенки серого
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Применяем пороговую обработку для улучшения контраста
    _, thresholded = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

    # Распознаем текст на изображении
    extracted_text = pytesseract.image_to_string(thresholded, lang='rus+eng')

    # Возвращаем распознанный текст
    return extracted_text

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    username = message.from_user.username
    chat_id = message.chat.id
    add_user_to_db(user_id, username, chat_id)  # Исправлен вызов функции

    # Проверяем, находимся ли мы в режиме ИИ
    if user_state.get(user_id, 0) == 0:
        # Получаем файл изображения
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Сохраняем изображение во временный файл
        temp_image_path = "temp_image.jpg"
        with open(temp_image_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        # Анализируем изображение
        extracted_text = analyze_image(temp_image_path)

        # Удаляем временный файл
        os.remove(temp_image_path)

        # Отправляем извлеченный текст обратно в диалог
        bot.reply_to(message, f"Извлеченный текст:\n{extracted_text}")

        # Отправляем извлеченный текст в обработчик текстовых сообщений
        handle_text_message(user_id, username, chat_id, extracted_text, message)

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

def extract_text_from_pdf(file_path):
    pdf_file = open(file_path, 'rb')
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    full_text = []
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        full_text.append(page.extract_text())
    pdf_file.close()
    return '\n'.join(full_text)

@bot.message_handler(content_types=['document'])
def handle_document(message):
    user_id = message.from_user.id
    if user_state.get(user_id) == 2:
        waiting_msg = bot.send_message(message.chat.id, "⏳ Обрабатываю документ...")
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_path = f"temp_{message.document.file_name}"
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        if file_path.endswith('.docx'):
            extracted_text = extract_text_from_docx(file_path)
        elif file_path.endswith('.pdf'):
            extracted_text = extract_text_from_pdf(file_path)
        else:
            bot.reply_to(message, 'Поддерживаются только документы формата Word (docx) и PDF.')
            return
        
        os.remove(file_path)
        
        # Сохраняем содержимое документа в контексте пользователя
        if user_id not in user_context:
            user_context[user_id] = []
        user_context[user_id].append({"role": "system", "content": extracted_text})
        
        bot.delete_message(message.chat.id, waiting_msg.message_id)
        bot.reply_to(message, 'Документ успешно загружен. Теперь вы можете задавать вопросы по содержимому документа.')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    username = message.from_user.username
    chat_id = message.chat.id
    add_user_to_db(user_id, username, chat_id)

    if user_id not in user_state:
        user_state[user_id] = 0  # По умолчанию режим ИИ

    if user_state[user_id] == 0:  # Режим ИИ
        if message.content_type == 'text':
            user_message = message.text
            add_request_to_db(username, chat_id, user_message)
            handle_text_message(user_id, username, chat_id, user_message, message)
        else:
            bot.reply_to(message, "Я не могу обработать этот тип сообщения.")

    elif user_state[user_id] == 1:  # Режим создания изображений
        if message.content_type == 'text':
            user_message = message.text
            if "width" not in user_params[user_id] or "height" not in user_params[user_id]:
                try:
                    width, height = map(int, user_message.split(','))
                    user_params[user_id]["width"] = width
                    user_params[user_id]["height"] = height
                    bot.send_message(message.chat.id, "Теперь отправьте текстовый запрос для генерации изображения.")
                except ValueError:
                    bot.send_message(message.chat.id, "Пожалуйста, введите ширину и высоту через запятую (например, 512,512).")
            else:
                generate_image(user_message, message.chat.id, user_params[user_id])
        else:
            bot.reply_to(message, "В режиме создания изображений я могу обрабатывать только текстовые запросы.")

    elif user_state[user_id] == 2:  # Режим работы с документами
        if message.content_type == 'text':
            user_message = message.text
            if user_id in user_context:
                # Если есть сохраненный документ, добавляем его содержимое в контекст
                handle_text_message(user_id, username, chat_id, user_message, message)
            else:
                bot.reply_to(message, "Пожалуйста, сначала загрузите документ.")
        else:
            bot.reply_to(message, "Я не могу обработать этот тип сообщения.")

# Установка переменной окружения
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "path_to_your_google_cloud_credentials.json"

def recognize_speech(file_path, language_code):
    client = speech.SpeechClient()
    with io.open(file_path, "rb") as audio_file:
        content = audio_file.read()

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
        sample_rate_hertz=48000,
        language_code=language_code,
    )

    response = client.recognize(config=config, audio=audio)
    for result in response.results:
        return result.alternatives[0].transcript

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    user_id = message.from_user.id
    if user_state.get(user_id) == 0:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_path = f"temp_voice_{user_id}.ogg"
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        recognized_text = recognize_speech(file_path, "ru-RU")  # Можно добавить поддержку других языков
        os.remove(file_path)
        bot.reply_to(message, f"Распознанный текст:\n{recognized_text}")
        handle_text_message(user_id, message.from_user.username, message.chat.id, recognized_text, message)

@bot.message_handler(func=lambda message: message.text == "Режим изображений")
def set_image_mode(message):
    user_id = message.from_user.id
    user_state[user_id] = 1
    bot.reply_to(message, 'Режим изображений активирован.')
    select_model(message)

def select_model(message):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Определить автоматически", callback_data="model_absolutereality_v181.safetensors [3d9d4d2b]"))
    for model in models:
        markup.add(types.InlineKeyboardButton(models_translation[model], callback_data=f"model_{model}"))
    bot.send_message(message.chat.id, "Выберите модель:", reply_markup=markup)

def select_style(message):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    for style in style_presets:
        markup.add(types.InlineKeyboardButton(style_presets_translation[style], callback_data=f"style_{style}"))
    bot.send_message(message.chat.id, "Выберите стиль:", reply_markup=markup)

def select_dimensions(message):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    dimensions = [
        (512, 512),
        (768, 768),
        (1024, 1024),
        (1280, 720),
        (1920, 1080)
    ]
    for width, height in dimensions:
        markup.add(types.InlineKeyboardButton(f"{width}x{height}", callback_data=f"dimension_{width}_{height}"))
    bot.send_message(message.chat.id, "Выберите размер изображения:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("dimension_"))
def dimension_callback_handler(call):
    user_id = call.from_user.id
    data = call.data.split("_")
    width = int(data[1])
    height = int(data[2])
    user_params[user_id]["width"] = width
    user_params[user_id]["height"] = height
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "Теперь отправьте текстовый запрос для генерации изображения.")

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.username == 'oxpanik_1':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Окончить рассылку")
        bot.reply_to(message, 'Вы начали рассылку. Отправьте текст или фото для рассылки.', reply_markup=markup)
        bot.register_next_step_handler(message, send_broadcast)
    else:
        bot.reply_to(message, 'У вас нет прав для выполнения этой команды.')

def send_broadcast(message):
    if message.text == "Окончить рассылку":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Режим ИИ", "Режим изображений", "Очистить контекст")
        bot.reply_to(message, 'Рассылка окончена.', reply_markup=markup)
        return

    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT chat_id FROM users")
        chat_ids = c.fetchall()
        
        for chat_id in chat_ids:
            if message.content_type == 'text':
                bot.send_message(chat_id[0], message.text)
            elif message.content_type == 'photo':
                bot.send_photo(chat_id[0], message.photo[-1].file_id, caption=message.caption)

    bot.reply_to(message, 'Рассылка завершена.')

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    username = call.from_user.username
    chat_id = call.message.chat.id
    add_user_to_db(user_id, username, chat_id, username, 'Some info about user')

    data = call.data.split("_")
    param_type = data[0]
    param_value = "_".join(data[1:])

    if param_type == "model":
        user_params[user_id] = {"model": param_value}
        bot.delete_message(call.message.chat.id, call.message.message_id)
        select_style(call.message)
    elif param_type == "style":
        user_params[user_id]["style_preset"] = param_value
        bot.delete_message(call.message.chat.id, call.message.message_id)
        select_dimensions(call.message)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    username = message.from_user.username
    chat_id = message.chat.id
    add_user_to_db(user_id, username, chat_id)

    if user_id not in user_state:
        user_state[user_id] = 0  # По умолчанию режим ИИ

    if user_state[user_id] == 0:  # Режим ИИ
        if message.content_type == 'text':
            user_message = message.text
            add_request_to_db(username, chat_id, user_message)
            handle_text_message(user_id, username, chat_id, user_message, message)
        else:
            bot.reply_to(message, "Я не могу обработать этот тип сообщения.")

    elif user_state[user_id] == 1:  # Режим создания изображений
        if message.content_type == 'text':
            user_message = message.text
            if "width" not in user_params[user_id] or "height" not in user_params[user_id]:
                try:
                    width, height = map(int, user_message.split(','))
                    user_params[user_id]["width"] = width
                    user_params[user_id]["height"] = height
                    bot.send_message(message.chat.id, "Теперь отправьте текстовый запрос для генерации изображения.")
                except ValueError:
                    bot.send_message(message.chat.id, "Пожалуйста, введите ширину и высоту через запятую (например, 512,512).")
            else:
                generate_image(user_message, message.chat.id, user_params[user_id])
        else:
            bot.reply_to(message, "В режиме создания изображений я могу обрабатывать только текстовые запросы.")

    elif user_state[user_id] == 2:  # Режим работы с документами
        if message.content_type == 'text':
            user_message = message.text
            if user_id in user_context:
                # Если есть сохраненный документ, добавляем его содержимое в контекст
                handle_text_message(user_id, username, chat_id, user_message, message)
            else:
                bot.reply_to(message, "Пожалуйста, сначала загрузите документ.")
        else:
            bot.reply_to(message, "Я не могу обработать этот тип сообщения.")

def handle_text_message(user_id, username, chat_id, user_message, original_message):
    # Если контекст для пользователя не существует, создаем его
    if user_id not in user_context:
        user_context[user_id] = []

    # Добавляем сообщение пользователя в контекст
    user_context[user_id].append({"role": "user", "content": user_message})

    # Данные для запроса
    data = {
        "model": "openai/gpt-4o-mini-2024-07-18",  # Optional
        "messages": user_context[user_id]
    }

    waiting_msg = bot.send_message(original_message.chat.id, waiting_message)
    response = send_to_api(data)

    # Проверка статуса ответа
    if response and response.status_code == 200:
        response_data = response.json()
        if 'choices' in response_data:
            assistant_response = response_data['choices'][0]['message']['content']

            # Добавляем ответ нейросети в контекст
            user_context[user_id].append({"role": "assistant", "content": assistant_response})

            # Разбиваем ответ на части, если он превышает 4096 символов
            for part in split_message(assistant_response):
                bot.reply_to(original_message, part)
        else:
            bot.reply_to(original_message, "Ошибка: Ответ от API не содержит ключа 'choices'.")
            logger.error(f"Ошибка: Ответ от API не содержит ключа 'choices'. Ответ: {response_data}")
    else:
        bot.reply_to(original_message, f"Ошибка при выполнении запроса. Статус код: {response.status_code if response else 'Не удалось загрузить изображение'}")
        logger.error(f"Ошибка при выполнении запроса. Статус код: {response.status_code if response else 'Не удалось загрузить изображение'}")

    bot.delete_message(original_message.chat.id, waiting_msg.message_id)

def split_message(text, max_length=4096):
    """Разбивает текст на части не больше max_length символов."""
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

def send_to_api(data):
    response = requests.post(
        url=openai_url,
        headers=openai_headers,
        data=json.dumps(data)
    )
    return response

def generate_image(prompt, chat_id, params):
    url = "https://api.prodia.com/v1/sd/generate"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-Prodia-Key": prodia_api_key
    }
    translated_prompt = translator.translate(prompt, src='ru', dest='en').text
    payload = {
        "model": params["model"],
        "prompt": translated_prompt,
        "negative_prompt": "badly drawn",
        "style_preset": params["style_preset"],
        "steps": 20,
        "cfg_scale": 7,
        "seed": -1,
        "upscale": True,
        "sampler": "DPM++ 2M Karras",
        "width": params["width"],
        "height": params["height"]
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Проверка на ошибки HTTP
        response_data = response.json()
        logger.info(f"Ответ от Prodia: {response_data}")  # Логирование ответа от Prodia

        job_id = response_data.get("job")
        if job_id:
            check_job_status(job_id, chat_id, prompt)
        else:
            bot.send_message(chat_id, "Ошибка: Job ID не найден в ответе от Prodia.")
            logger.error("Job ID не найден в ответе от Prodia.")
    except requests.exceptions.RequestException as e:
        bot.send_message(chat_id, f"Ошибка при генерации изображения: {e}")
        logger.error(f"Ошибка при генерации изображения: {e}")
    except json.JSONDecodeError as e:
        bot.send_message(chat_id, "Ошибка: Не удалось декодировать JSON ответ от Prodia.")
        logger.error(f"Ошибка при декодировании JSON ответа от Prodia: {e}")

def check_job_status(job_id, chat_id, prompt):
    url = f"https://api.prodia.com/v1/job/{job_id}"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-Prodia-Key": prodia_api_key
    }
    waiting_msg = bot.send_message(chat_id, waiting_message)
    start_time = time.time()
    while time.time() - start_time < 120:  # 2 минуты
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Проверка на ошибки HTTP
            response_data = response.json()
            logger.info(f"Статус задачи от Prodia: {response_data}")  # Логирование статуса задачи

            status = response_data.get("status")
            if status == "succeeded":
                image_url = response_data.get("imageUrl")
                if image_url:
                    bot.delete_message(chat_id, waiting_msg.message_id)
                    send_image_by_url(chat_id, image_url)
                    add_image_to_db(message.from_user.username, chat_id, prompt, image_url)
                    return
                else:
                    bot.send_message(chat_id, "Ошибка: URL изображения не найден в ответе от Prodia.")
                    logger.error("URL изображения не найден в ответе от Prodia.")
                    return
            elif status == "failed":
                bot.send_message(chat_id, "Ошибка: Задача завершилась с ошибкой.")
                logger.error("Задача завершилась с ошибкой.")
                return
            else:
                time.sleep(5)  # Подождать 5 секунд перед следующей проверкой
        except requests.exceptions.RequestException as e:
            bot.send_message(chat_id, f"Ошибка при проверке статуса задачи: {e}")
            logger.error(f"Ошибка при проверке статуса задачи: {e}")
            return
        except json.JSONDecodeError as e:
            bot.send_message(chat_id, "Ошибка: Не удалось декодировать JSON ответ от Prodia.")
            logger.error(f"Ошибка при декодировании JSON ответа от Prodia: {e}")
            return

    bot.send_message(chat_id, "Ошибка: Превышено время ожидания. Попробуйте снова.")
    logger.error("Превышено время ожидания.")

def send_image_by_url(chat_id, image_url):
    try:
        # Загрузка изображения по URL
        image_response = requests.get(image_url)
        image_response.raise_for_status()  # Проверка на ошибки HTTP

        # Отправка изображения через Telegram API
        bot.send_photo(chat_id, image_response.content)
    except requests.exceptions.RequestException as e:
        bot.send_message(chat_id, f"Ошибка при загрузке изображения: {e}")
        logger.error(f"Ошибка при загрузке изображения: {e}")

# Команда для отправки рассылок
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.username == 'oxpanik_1':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Окончить рассылку")
        bot.reply_to(message, 'Вы начали рассылку. Отправьте текст или фото для рассылки.', reply_markup=markup)
        bot.register_next_step_handler(message, send_broadcast)
    else:
        bot.reply_to(message, 'У вас нет прав для выполнения этой команды.')

def send_broadcast(message):
    if message.text == "Окончить рассылку":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Режим ИИ", "Режим изображений", "Очистить контекст")
        bot.reply_to(message, 'Рассылка окончена.', reply_markup=markup)
        return

    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT chat_id FROM users")
        chat_ids = c.fetchall()
        
        for chat_id in chat_ids:
            if message.content_type == 'text':
                bot.send_message(chat_id[0], message.text)
            elif message.content_type == 'photo':
                bot.send_photo(chat_id[0], message.photo[-1].file_id, caption=message.caption)

    bot.reply_to(message, 'Рассылка завершена.')

@bot.message_handler(func=lambda message: message.text in ["Режим ИИ", "Режим изображений", "Работа с документами"])
def clear_document_data(message):
    user_id = message.from_user.id
    if user_id in user_context:
        del user_context[user_id]
    if user_id in user_params:
        del user_params[user_id]
    bot.reply_to(message, 'Данные о документах и голосовых сообщениях очищены.')

# Запуск бота
bot.polling()