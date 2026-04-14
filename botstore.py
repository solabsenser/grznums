from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = 'YOUR_BOT_TOKEN'
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🇺🇸 США", callback_data="buy_usa"),
        InlineKeyboardButton("🇨🇦 Канада", callback_data="buy_can"),
        InlineKeyboardButton("💰 Пополнить (Uzcard)", callback_data="topup")
    )
    await message.answer("Выбирай страну для регистрации аккаунта:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == 'topup')
async def topup(callback_query: types.CallbackQuery):
    # Ссылка на раздел пополнения в Grizzly (обычно там выбирается метод)
    url = "https://grizzlysms.com/profile/pay" 
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("Перейти к оплате", url=url))
    await bot.send_message(callback_query.from_user.id, "Выбирай способ оплаты (через агрегаторы доступен Uzcard):", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('buy_'))
async def process_buy(callback_query: types.CallbackQuery):
    country = callback_query.data.split('_')[1]
    await bot.answer_callback_query(callback_query.id, "Запускаю регистрацию... Подожди 2-3 минуты.")
    
    # Тут вызываем функцию из Первой части
    reg = GrizzlyReg(country)
    session_file = reg.start_registration()
    
    if session_file:
        file = types.InputFile(f"sessions/{session_file}")
        await bot.send_document(callback_query.from_user.id, file, caption=f"Твой аккаунт {country} готов!")
    else:
        await bot.send_message(callback_query.from_user.id, "Ошибка. Проверь баланс на Grizzly.")

if __name__ == '__main__':
    executor.start_polling(dp)
