import os
from textwrap import shorten

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from registrator import GrizzlyBackend


API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
backend = GrizzlyBackend()


def countries_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("🇻🇳 Vietnam", callback_data="buy_vnm"),
        InlineKeyboardButton("🇺🇸 USA", callback_data="buy_usa"),
        InlineKeyboardButton("🇨🇦 Canada", callback_data="buy_can"),
    )
    kb.add(InlineKeyboardButton("📊 Статусы прогрева", callback_data="list_warmup"))
    return kb


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    text = (
        "Бот контроля закупки номеров Grizzly SMS.\n\n"
        "Команды:\n"
        "/balance — проверить баланс\n"
        "/buy <country> — купить номер (vnm/usa/can)\n"
        "/list — список купленных номеров\n"
        "/status <activation_id> <new|warming|ready|hold> [комментарий]"
    )
    await message.answer(text, reply_markup=countries_keyboard())


@dp.message_handler(commands=["balance"])
async def balance(message: types.Message):
    try:
        data = backend.get_balance()
        await message.answer(f"Баланс Grizzly: {data}")
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"Ошибка баланса: {exc}")


@dp.message_handler(commands=["buy"])
async def buy(message: types.Message):
    parts = message.text.split()
    country = parts[1].lower() if len(parts) > 1 else "vnm"
    try:
        result = backend.buy_number(country=country)
        await message.answer(
            "Номер куплен:\n"
            f"ID: {result['activation_id']}\n"
            f"Телефон: {result['phone_number']}\n"
            f"Страна: {result['country']}\n"
            f"Статус прогрева: {result['status']}"
        )
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"Ошибка покупки: {exc}")


@dp.message_handler(commands=["list"])
async def list_warmup(message: types.Message):
    rows = backend.list_warmup()
    if not rows:
        await message.answer("Пока нет купленных номеров.")
        return

    lines = []
    for row in rows[-20:]:
        lines.append(
            f"• {row['activation_id']} | {row['phone_number']} | {row['country']} | {row['status']} | "
            f"{shorten(row.get('notes', ''), width=40, placeholder='...')}"
        )
    await message.answer("Последние номера:\n" + "\n".join(lines))


@dp.message_handler(commands=["status"])
async def set_status(message: types.Message):
    parts = message.text.split(maxsplit=3)
    if len(parts) < 3:
        await message.answer("Формат: /status <activation_id> <new|warming|ready|hold> [комментарий]")
        return

    activation_id = parts[1]
    status_value = parts[2]
    notes = parts[3] if len(parts) > 3 else ""

    ok = backend.set_warmup_status(activation_id=activation_id, status=status_value, notes=notes)
    if not ok:
        await message.answer("ID не найден.")
        return

    await message.answer(f"Обновил {activation_id}: {status_value}")


@dp.callback_query_handler(lambda c: c.data.startswith("buy_"))
async def buy_callback(callback_query: types.CallbackQuery):
    country = callback_query.data.split("_")[1]
    await bot.answer_callback_query(callback_query.id)
    try:
        result = backend.buy_number(country=country)
        await bot.send_message(
            callback_query.from_user.id,
            f"Куплен номер {result['phone_number']} (ID {result['activation_id']}) для {result['country']}.",
        )
    except Exception as exc:  # noqa: BLE001
        await bot.send_message(callback_query.from_user.id, f"Ошибка: {exc}")


@dp.callback_query_handler(lambda c: c.data == "list_warmup")
async def list_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    rows = backend.list_warmup()
    if not rows:
        await bot.send_message(callback_query.from_user.id, "Список пуст.")
        return
    preview = "\n".join(
        f"{r['activation_id']} | {r['phone_number']} | {r['status']}" for r in rows[-10:]
    )
    await bot.send_message(callback_query.from_user.id, "Последние статусы:\n" + preview)


if __name__ == "__main__":
    if not API_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан")
    executor.start_polling(dp, skip_updates=True)
