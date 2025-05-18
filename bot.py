import os
import openai
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, CommandHandler
import speech_recognition as sr
from pydub import AudioSegment
from gtts import gTTS

# Лог запуска
with open("launch_log.txt", "a", encoding="utf-8") as log_file:
    log_file.write(f"Бот запущен: {datetime.now()}\n")

# API-ключи
openai.api_key = "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"
TELEGRAM_TOKEN = "7418110001:AAH7mFFDpoLBrb0aX6ZqRekUMZF-M4xNeWk"

TEMP_FOLDER = "temp_audio"
os.makedirs(TEMP_FOLDER, exist_ok=True)

user_settings = {}

LANGUAGES = {
    "Русский": "ru",
    "Английский": "en",
    "Польский": "pl",
    "Немецкий": "de",
    "Чешский": "cs",
    "Украинский": "uk"
}

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Привет! Я голосовой переводчик на GPT.\nОтправь голосовое сообщение.\nЯзыки настраиваются через /language")

def language(update: Update, context: CallbackContext):
    keyboard = [[k] for k in LANGUAGES.keys()]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text("Выбери язык, на котором ты ГОВОРИШЬ:", reply_markup=reply_markup)
    context.user_data["lang_step"] = "from"

def handle_text(update: Update, context: CallbackContext):
    text = update.message.text
    if "lang_step" in context.user_data:
        step = context.user_data["lang_step"]
        if text in LANGUAGES:
            if step == "from":
                context.user_data["from_lang"] = LANGUAGES[text]
                context.user_data["lang_step"] = "to"
                keyboard = [[k] for k in LANGUAGES.keys()]
                reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
                update.message.reply_text("Теперь выбери язык, на который ПЕРЕВОДИТЬ:", reply_markup=reply_markup)
            elif step == "to":
                context.user_data["to_lang"] = LANGUAGES[text]
                context.user_data.pop("lang_step")
                user_settings[update.message.from_user.id] = {
                    "from": context.user_data["from_lang"],
                    "to": context.user_data["to_lang"]
                }
                update.message.reply_text("Языки сохранены! Можешь отправлять голосовые.")
        else:
            update.message.reply_text("Пожалуйста, выбери язык из списка.")
    else:
        update.message.reply_text("Если хочешь сменить язык — используй команду /language")

def lang_code_to_name(code):
    names = {
        "ru": "русского",
        "en": "английского",
        "pl": "польского",
        "de": "немецкого",
        "cs": "чешского",
        "uk": "украинского"
    }
    return names.get(code, code)

def translate_text(text, source_lang="ru", target_lang="en"):
    prompt = f"Переведи с {lang_code_to_name(source_lang)} на {lang_code_to_name(target_lang)}:\n{text}"
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[GPT Ошибка] {e}"

def voice_handler(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    langs = user_settings.get(user_id, {"from": "ru", "to": "en"})

    file = update.message.voice.get_file()
    ogg_path = os.path.join(TEMP_FOLDER, f"{file.file_id}.ogg")
    wav_path = ogg_path.replace(".ogg", ".wav")

    file.download(ogg_path)
    AudioSegment.from_ogg(ogg_path).export(wav_path, format="wav")

    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data, language=langs["from"])
            update.message.reply_text(f"Вы сказали: {text}")

            translated = translate_text(text, source_lang=langs["from"], target_lang=langs["to"])
            update.message.reply_text(f"Перевод: {translated}")

            tts = gTTS(translated, lang=langs["to"])
            mp3_path = os.path.join(TEMP_FOLDER, f"{file.file_id}.mp3")
            tts.save(mp3_path)

            with open(mp3_path, "rb") as audio:
                update.message.reply_audio(audio, filename="translate.mp3", title="Перевод")

        except Exception as e:
            update.message.reply_text(f"Ошибка: {e}")

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("language", language))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dp.add_handler(MessageHandler(Filters.voice, voice_handler))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
