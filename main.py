import asyncio
import logging
import os
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bs4 import BeautifulSoup

TOKEN = os.environ.get("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

user_brawlers = {}
processed_messages = set()
processed_callbacks = set()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    message_id = f"{message.chat.id}_{message.message_id}"
    if message_id in processed_messages:
        return
    processed_messages.add(message_id)
    
    if len(processed_messages) > 1000:
        processed_messages.clear()
    
    await message.answer(
        f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n"
        f"🤖 <b>Я бот для проверки статистики Brawl Stars</b>\n\n"
        f"📋 <b>Команды:</b>\n"
        f"• <code>/bs player &lt;тег&gt;</code> — статистика игрока\n"
        f"• <code>/bs clan &lt;тег&gt;</code> — информация о клане\n"
        f"• <code>/bs brawlers &lt;тег&gt;</code> — все бойцы игрока\n\n"
        f"💡 <b>Примеры:</b>\n"
        f"• <code>/bs player #Y8GVPQJ0</code>\n"
        f"• <code>/bs clan #80R2V882V</code>\n"
        f"• <code>/bs brawlers #Y8GVPQJ0</code>",
        parse_mode="HTML"
    )

@dp.message(Command("bs"))
async def cmd_bs(message: Message):
    message_id = f"{message.chat.id}_{message.message_id}"
    if message_id in processed_messages:
        return
    processed_messages.add(message_id)
    
    if len(processed_messages) > 1000:
        processed_messages.clear()
    
    args = message.text.split(maxsplit=2)

    if len(args) < 3:
        await message.answer(
            "❌ <b>Неверный формат!</b>\n\n"
            "Используй:\n"
            "• <code>/bs player &lt;тег&gt;</code>\n"
            "• <code>/bs clan &lt;тег&gt;</code>\n"
            "• <code>/bs brawlers &lt;тег&gt;</code>",
            parse_mode="HTML"
        )
        return

    cmd_type = args[1].lower()
    player_tag = args[2].strip()
    tag_clean = player_tag.lstrip("#")

    if cmd_type == "player":
        await get_player_info(message, tag_clean, player_tag)
    elif cmd_type == "clan":
        await get_clan_info(message, tag_clean, player_tag)
    elif cmd_type == "brawlers":
        user_brawlers[message.from_user.id] = {
            "brawlers": [],
            "page": 0,
            "tag_clean": tag_clean,
            "player_tag": player_tag
        }
        await get_brawlers_info(message, tag_clean, player_tag, 0)
    else:
        await message.answer(
            "❌ <b>Неизвестная команда!</b>\n\n"
            "Доступно:\n"
            "• <code>/bs player &lt;тег&gt;</code>\n"
            "• <code>/bs clan &lt;тег&gt;</code>\n"
            "• <code>/bs brawlers &lt;тег&gt;</code>",
            parse_mode="HTML"
        )

async def get_player_info(message: Message, tag_clean: str, player_tag: str):
    display_tag = player_tag if player_tag.startswith('#') else f"#{player_tag}"
    await message.answer(
        f"🔍 Поиск игрока <code>{display_tag}</code>...",
        parse_mode="HTML"
    )

    url = f"https://brawlify.com/player/{tag_clean}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    await message.answer(
                        f"❌ <b>Ошибка:</b> статус <code>{response.status}</code>",
                        parse_mode="HTML"
                    )
                    return

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                name_elem = soup.find("h1")
                name = name_elem.get_text(strip=True) if name_elem else "Неизвестно"
                trophies_elem = soup.find("span", class_="text-brawl-gold")
                trophies = trophies_elem.get_text(strip=True) if trophies_elem else "Неизвестно"

                club_name = "Не состоит"
                club_tag = ""
                
                club_section = soup.find("span", string=lambda x: x and "Club" in x)
                if club_section:
                    club_div = club_section.find_parent("div", class_=lambda x: x and "flex flex-col" in x)
                    if club_div:
                        club_link = club_div.find("a", href=lambda x: x and "/club/" in x)
                        if club_link:
                            club_name_elem = club_link.find("p", class_="font-bold")
                            if club_name_elem:
                                club_name = club_name_elem.get_text(strip=True)
                            href = club_link.get("href", "")
                            if "/club/" in href:
                                club_tag = href.split("/club/")[-1].rstrip("/")

                top_brawlers = []
                first_place = None
                second_place = None
                third_place = None
                
                rank_circles = soup.find_all("div", class_="rounded-full")
                
                for circle in rank_circles:
                    rank_text = circle.get_text(strip=True)
                    if rank_text not in ["1", "2", "3"]:
                        continue
                    
                    card = circle.find_parent("div", class_=lambda x: x and "flex-col" in x and "items-center" in x)
                    if not card:
                        continue
                    
                    name_p = card.find("p", string=lambda x: x and 2 <= len(x.strip()) <= 20)
                    trophies_p = card.find("p", class_="text-brawl-gold")
                    
                    if name_p and trophies_p:
                        brawler_name = name_p.get_text(strip=True)
                        brawler_trophies = trophies_p.get_text(strip=True)
                        
                        if rank_text == "1":
                            first_place = (brawler_name, brawler_trophies)
                        elif rank_text == "2":
                            second_place = (brawler_name, brawler_trophies)
                        elif rank_text == "3":
                            third_place = (brawler_name, brawler_trophies)

                if first_place:
                    top_brawlers.append(first_place)
                if second_place:
                    top_brawlers.append(second_place)
                if third_place:
                    top_brawlers.append(third_place)

                result = (
                    f"🎮 <b>Игрок найден!</b>\n\n"
                    f"👤 <b>Ник:</b> <code>{name}</code>\n"
                    f"🏆 <b>Кубки:</b> <code>{trophies}</code>\n"
                    f"🆔 <b>ID:</b> <code>{display_tag}</code>"
                )

                if club_name != "Не состоит":
                    result += f"\n\n🏰 <b>Клан:</b> <code>{club_name}</code>"
                    if club_tag:
                        result += f" <code>#{club_tag}</code>"

                if top_brawlers:
                    result += "\n\n<b>🎯 Топ 3 бойца:</b>\n"
                    for i, (b_name, b_trophies) in enumerate(top_brawlers, 1):
                        result += f"{i}. <code>{b_name}</code> - <b>{b_trophies}</b>\n"

                safe_tag = tag_clean.replace("#", "")
                keyboard = [[InlineKeyboardButton(text="🎮 Бойцы", callback_data=f"brawlers_list_{safe_tag}_{player_tag}")]]
                reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

                await message.answer(result, parse_mode="HTML", reply_markup=reply_markup)

        except Exception as e:
            logging.error(f"Ошибка при запросе игрока: {e}")
            await message.answer(
                "❌ <b>Произошла ошибка</b> при получении данных",
                parse_mode="HTML"
            )

async def get_clan_info(message: Message, tag_clean: str, clan_tag: str):
    display_tag = clan_tag if clan_tag.startswith('#') else f"#{clan_tag}"
    await message.answer(
        f"🔍 Поиск клана <code>{display_tag}</code>...",
        parse_mode="HTML"
    )

    url = f"https://brawlify.com/club/{tag_clean}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    await message.answer(
                        f"❌ <b>Ошибка:</b> статус <code>{response.status}</code>",
                        parse_mode="HTML"
                    )
                    return

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                name_elem = soup.find("h1", class_="text-base sm:text-lg font-bold text-white truncate leading-tight")
                clan_name = name_elem.get_text(strip=True) if name_elem else "Неизвестно"
                trophies_elem = soup.find("span", class_="text-brawl-gold font-bold text-sm")
                clan_trophies = trophies_elem.get_text(strip=True) if trophies_elem else "Неизвестно"
                members_elem = soup.find("span", class_="text-white font-medium")
                members = members_elem.get_text(strip=True) if members_elem else "Неизвестно"

                description = "Нет описания"
                club_info_section = soup.find("section", class_=lambda x: x and "bg-brawl-surface" in x and "mb-6" in x)
                if club_info_section:
                    desc_paragraph = club_info_section.find("p", class_="text-text-secondary text-sm mt-3 leading-relaxed")
                    if desc_paragraph and desc_paragraph.get_text(strip=True):
                        description = desc_paragraph.get_text(strip=True)

                result = (
                    f"🏰 <b>Клан найден!</b>\n\n"
                    f"📛 <b>Название:</b> <code>{clan_name}</code>\n"
                    f"🏆 <b>Кубки:</b> <code>{clan_trophies}</code>\n"
                    f"👥 <b>Участники:</b> <code>{members}</code>\n"
                    f"📝 <b>Описание:</b> <i>{description}</i>\n"
                    f"🆔 <b>ID:</b> <code>{display_tag}</code>"
                )

                await message.answer(result, parse_mode="HTML")

        except Exception as e:
            logging.error(f"Ошибка при запросе клана: {e}")
            await message.answer(
                "❌ <b>Произошла ошибка</b> при получении данных",
                parse_mode="HTML"
            )

async def get_brawlers_info(message: Message, tag_clean: str, player_tag: str, page: int, callback: CallbackQuery = None):
    user_id = message.from_user.id
    display_tag = player_tag if player_tag.startswith('#') else f"#{player_tag}"

    if user_id not in user_brawlers or user_brawlers[user_id]["tag_clean"] != tag_clean or not user_brawlers[user_id].get("brawlers"):
        if not callback:
            await message.answer(
                f"🔍 Загрузка бойцов игрока <code>{display_tag}</code>...",
                parse_mode="HTML"
            )

        url = f"https://brawlify.com/player/{tag_clean}/brawlers"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        error_msg = f"❌ <b>Ошибка:</b> статус <code>{response.status}</code>"
                        if callback:
                            await callback.message.edit_text(error_msg, parse_mode="HTML")
                        else:
                            await message.answer(error_msg, parse_mode="HTML")
                        return

                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    brawler_cards = soup.find_all("article", class_=lambda x: x and "brawler-card" in x)

                    brawlers_list = []
                    for card in brawler_cards:
                        brawler_name = card.get("data-name")
                        brawler_power = card.get("data-power")
                        brawler_trophies = card.get("data-trophies")

                        if brawler_name and brawler_trophies:
                            trophies_num = int(brawler_trophies.replace(",", "")) if brawler_trophies.replace(",", "").isdigit() else 0
                            brawlers_list.append({
                                "name": brawler_name,
                                "power": brawler_power or "?",
                                "trophies": brawler_trophies,
                                "trophies_num": trophies_num,
                            })

                    logging.info(f"Найдено бойцов: {len(brawlers_list)}")
                    brawlers_list.sort(key=lambda x: x["trophies_num"], reverse=True)
                    
                    user_brawlers[user_id] = {
                        "brawlers": brawlers_list,
                        "page": 0,
                        "tag_clean": tag_clean,
                        "player_tag": player_tag
                    }
                    
            except Exception as e:
                logging.error(f"Ошибка при запросе бойцов: {e}")
                error_msg = "❌ <b>Произошла ошибка</b> при получении данных"
                if callback:
                    await callback.message.edit_text(error_msg, parse_mode="HTML")
                else:
                    await message.answer(error_msg, parse_mode="HTML")
                return
    
    brawlers_list = user_brawlers[user_id]["brawlers"]
    total_pages = (len(brawlers_list) + 14) // 15
    
    if page >= total_pages:
        page = total_pages - 1
    if page < 0:
        page = 0
    
    user_brawlers[user_id]["page"] = page
    
    start_idx = page * 15
    end_idx = min(start_idx + 15, len(brawlers_list))
    page_brawlers = brawlers_list[start_idx:end_idx]
    
    result = f"🎮 <b>Бойцы игрока</b> <code>{display_tag}</code>\n\n"
    
    for i, brawler in enumerate(page_brawlers, start_idx + 1):
        result += f"{i}. <b>{brawler['name']}</b> — Сила <code>{brawler['power']}</code> — 🏆 <code>{brawler['trophies']}</code>\n"
    
    result += f"\n📄 Страница <b>{page + 1}/{total_pages}</b>"
    
    keyboard = []
    row = []
    
    safe_tag = tag_clean.replace("#", "")
    
    if page > 0:
        row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"brawlers_page_{safe_tag}_{page - 1}"))
    
    if page < total_pages - 1:
        row.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"brawlers_page_{safe_tag}_{page + 1}"))
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"brawlers_list_{safe_tag}_{player_tag}")])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None

    if callback:
        callback_id = f"{callback.id}"
        if callback_id in processed_callbacks:
            return
        processed_callbacks.add(callback_id)
        
        if len(processed_callbacks) > 1000:
            processed_callbacks.clear()
        
        await callback.message.edit_text(result, parse_mode="HTML", reply_markup=reply_markup)
    else:
        await message.answer(result, parse_mode="HTML", reply_markup=reply_markup)

@dp.callback_query(F.data.startswith("brawlers_"))
async def callback_brawlers_page(callback: CallbackQuery):
    callback_id = f"{callback.id}"
    if callback_id in processed_callbacks:
        await callback.answer()
        return
    processed_callbacks.add(callback_id)
    
    if len(processed_callbacks) > 1000:
        processed_callbacks.clear()
    
    data = callback.data.split("_")

    if data[1] == "list" and len(data) >= 4:
        tag_clean = data[2]
        player_tag = "_".join(data[3:])
        
        user_brawlers[callback.from_user.id] = {
            "brawlers": [],
            "page": 0,
            "tag_clean": tag_clean,
            "player_tag": player_tag
        }
        await get_brawlers_info(callback.message, tag_clean, player_tag, 0, callback=callback)
        await callback.answer()
        return
    
    if data[1] == "page" and len(data) >= 4:
        tag_clean = data[2]
        try:
            page = int(data[3])
        except ValueError:
            await callback.answer()
            return
        
        player_tag = tag_clean
        if callback.from_user.id in user_brawlers:
            if user_brawlers[callback.from_user.id]["tag_clean"] == tag_clean:
                player_tag = user_brawlers[callback.from_user.id]["player_tag"]
        
        await get_brawlers_info(callback.message, tag_clean, player_tag, page, callback=callback)
        await callback.answer()
        return
    
    if len(data) >= 3 and data[1] != "list" and data[1] != "page":
        tag_clean = data[1]
        try:
            page = int(data[2])
        except ValueError:
            await callback.answer()
            return
        
        player_tag = tag_clean
        if callback.from_user.id in user_brawlers:
            if user_brawlers[callback.from_user.id]["tag_clean"] == tag_clean:
                player_tag = user_brawlers[callback.from_user.id]["player_tag"]
        
        await get_brawlers_info(callback.message, tag_clean, player_tag, page, callback=callback)
        await callback.answer()
        return
    
    await callback.answer()

async def main():
    logging.info("Запуск бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
