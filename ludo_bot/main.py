# bot_main.py (yoki sizning bot faylingiz nomi)
import asyncio
import httpx # HTTP so'rovlari uchun (yoki requests)
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import WebAppInfo

BOT_TOKEN = "8033028557:AAHWfw4fv9_8DJ5I0tJRqoV0FHjTWeywX5o"
API_SERVER_URL = "http://localhost:8000" # Sizning FastAPI serveringiz manzili
MINI_APP_BASE_URL = "https://t.me/ludo_demo_bot/ludo" # Sizning Mini App manzilingiz

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def on_startup(dispatcher):
    # Webhookni o'rnatish (agar polling o'rniga ishlatsangiz)
    # await bot.set_webhook(url=f"{YOUR_NGROK_OR_SERVER_URL}/webhook/{BOT_TOKEN}")
    print("Bot ishga tushdi")

async def on_shutdown(dispatcher):
    # await bot.delete_webhook()
    print("Bot to'xtadi")


@dp.message(Command("new_game"))
async def new_game_command_handler(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("Bu buyruq faqat guruhlarda ishlaydi.")
        return

    chat_id = message.chat.id
    host_user_id = message.from_user.id
    host_first_name = message.from_user.first_name

    payload = {
        "chat_id": chat_id,
        "host_user_id": host_user_id,
        "host_first_name": host_first_name
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{API_SERVER_URL}/bot/new_game", json=payload)
            response.raise_for_status() # Agar HTTP xatolik bo'lsa (4xx, 5xx) exception chiqaradi
            
            game_data = response.json() # Bu BotNewGameResponse bo'lishi kerak
            game_id = game_data.get("game_id")

            if not game_id:
                await message.reply("O'yin yaratishda xatolik yuz berdi (serverdan game_id kelmadi).")
                return

            mini_app_url = f"{MINI_APP_BASE_URL}?startapp={game_id}"
            
            builder = InlineKeyboardBuilder()
            builder.button(text="KIRIW", url=mini_app_url)
            # Mini App tugmasi uchun: web_app=WebAppInfo(url=mini_app_url)
            # builder.button(text="🏆 O'yinga qo'shilish", web_app=types.WebAppInfo(url=mini_app_url))


            sent_message = await message.answer(
                f"<b>🎲 JAŃA OYÍN №{message.message_id}</b>",
                reply_markup=builder.as_markup(),
                parse_mode='HTML'
            )
            # Xabar ID sini serverga yuborish
            message_id_payload = {
                "game_id": game_id,
                "message_id": sent_message.message_id
            }
            await client.post(f"{API_SERVER_URL}/bot/set_message_id", json=message_id_payload)
            await message.delete()
            # Bu so'rovning javobini tekshirish ham mumkin

    except httpx.HTTPStatusError as e:
        print(f"Server bilan bog'lanishda HTTP xatoligi: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        print(f"Serverga so'rov yuborishda xatolik: {e}")
    except Exception as e:
        print(f"/new_game handlerida kutilmagan xatolik: {e}")

# ... (qolgan bot kodlaringiz) ...

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())