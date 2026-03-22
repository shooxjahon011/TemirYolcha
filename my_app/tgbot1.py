import os
import sys
import django
import random
from datetime import timedelta
from django.utils import timezone

# 1. LOYIHA YO'LINI SOZLASH
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))  # my_app papkasi
BASE_DIR = os.path.dirname(CURRENT_DIR)  # Asosiy loyiha papkasi
sys.path.append(BASE_DIR)

# 2. DJANGO SOZLAMALARI
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_project.settings')
try:
    django.setup()
except Exception as e:
    print(f"Django setup xatosi: {e}")

# 3. MODELLARNI IMPORT QILISH (django.setup() dan keyin)
try:
    from my_app.models import UserProfile, IshchiGuruh
except ImportError:
    print("Modellarni import qilishda xatolik!")

import telebot
from telebot import types

# Bot ma'lumotlari
TOKEN = "7833987841:AAF5Zm6THDhoEv8BeHl7rBxWdKk-TKGcxtw"
ADMIN_ID = "8513245980"
bot = telebot.TeleBot(TOKEN)

print("✅ Bot muvaffaqiyatli ishga tushdi...")


# --- HANDLERLAR ---

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    btn = types.KeyboardButton("📞 Telefon raqamni yuborish", request_contact=True)
    markup.add(btn)
    bot.send_message(message.chat.id, "Assalomu alaykum! Ro'yxatdan o'tgan raqamingizni yuboring:", reply_markup=markup)


@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    try:
        raw_phone = str(message.contact.phone_number).replace("+", "")
        short_phone = raw_phone[-9:]

        user = UserProfile.objects.filter(phone__contains=short_phone).first()

        if user:
            # AttributeError oldini olish uchun xavfsiz tekshiruv
            guruh_nomi = "Guruhsiz"
            if hasattr(user, 'guruh') and user.guruh:
                guruh_nomi = user.guruh.nomi

            bot.send_message(
                message.chat.id,
                f"✅ Sizni topdim!\n👤 {user.full_name}\n🏗 Guruh: {guruh_nomi}\n\nEndi o'zingizni rasmimgizni yuboring yuboring.",
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            bot.send_message(message.chat.id, "❌ Siz hali saytda ro'yxatdan o'tmabsiz.")
    except Exception as e:
        print(f"Contact xatosi: {e}")
        bot.send_message(message.chat.id, "⚠️ Ma'lumotlarni tekshirishda xatolik yuz berdi.")


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    markup = types.InlineKeyboardMarkup()
    btn_accept = types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"ok_{message.chat.id}")
    btn_reject = types.InlineKeyboardButton("❌ Rad etish", callback_data=f"no_{message.chat.id}")
    markup.add(btn_accept, btn_reject)

    bot.send_photo(
        ADMIN_ID,
        message.photo[-1].file_id,
        caption=f"🔔 Yangi to'lov cheki!\n👤 Ism: {message.from_user.first_name}\n🆔 TG-ID: {message.chat.id}",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data.split("_")
    cmd = data[0]
    target_tg_id = data[1]

    if cmd == "ok":
        # Oxirgi nofaol foydalanuvchini topish
        user = UserProfile.objects.filter(is_active=False).last()

        if user:
            code = str(random.randint(1000, 9999))
            user.activation_code = code
            user.is_active = True
            user.save()

            # Guruh nomini xavfsiz olish
            g_nomi = "Yo'q"
            if hasattr(user, 'guruh') and user.guruh:
                g_nomi = user.guruh.nomi

            # Adminga natija
            m = types.InlineKeyboardMarkup()
            m.add(types.InlineKeyboardButton("🔴 Faolsizlantirish", callback_data=f"del_{user.id}_{target_tg_id}"))

            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=f"✅ TASDIQLANDI\n👤 User: {user.full_name}\n🏗 Guruh: {g_nomi}\n🔑 Kod: {code}",
                reply_markup=m
            )
            # Foydalanuvchiga xabar
            bot.send_message(target_tg_id, f"✅ Profilingiz tasdiqlandi!\n🏗 Guruh: {g_nomi}\n🔑 Yangi kodingiz: {code}")
        else:
            bot.answer_callback_query(call.id, "❌ Nofaol user topilmadi.")

    elif cmd == "no":
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption="❌ Rad etildi."
        )
        bot.send_message(target_tg_id, "❌ To'lov cheki qabul qilinmadi.")

    elif cmd == "del":
        user_db_id = data[1]
        user_tg_id = data[2] if len(data) > 2 else ""

        user = UserProfile.objects.filter(id=user_db_id).first()
        if user:
            user.is_active = False
            user.save()

            m = types.InlineKeyboardMarkup()
            m.add(types.InlineKeyboardButton("🟢 Qayta faollashtirish", callback_data=f"act_{user.id}_{user_tg_id}"))

            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=f"🔴 {user.full_name} FAOLSIZLANTIRILDI.",
                reply_markup=m
            )
            if user_tg_id:
                bot.send_message(user_tg_id, "⚠️ Profilingiz admin tomonidan to'xtatildi.")

    elif cmd == "act":
        user_db_id = data[1]
        user_tg_id = data[2] if len(data) > 2 else ""

        user = UserProfile.objects.filter(id=user_db_id).first()
        if user:
            user.is_active = True
            user.save()

            m = types.InlineKeyboardMarkup()
            m.add(types.InlineKeyboardButton("🔴 Faolsizlantirish", callback_data=f"del_{user.id}_{user_tg_id}"))

            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=f"🟢 {user.full_name} QAYTA FAOLLASHTIRILDI.",
                reply_markup=m
            )
            if user_tg_id:
                bot.send_message(user_tg_id, "✅ Profilingiz qayta faollashtirildi!")


# BOTNI ISHGA TUSHIRISH
try:
    bot.polling(none_stop=True)
except Exception as e:
    print(f"Polling xatosi: {e}")