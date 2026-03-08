import asyncio
import logging
import re

import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bs4 import BeautifulSoup

TOKEN = "8609986044:AAHyMYrVaTj2xWh7aWdu6Uq7i8mrHT-BjH0"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

user_brawlers = {}

@dp.message(Command("start"))
async def cmd_start(message: Message):
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
        # Сохраняем данные для кэша перед вызовом
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
    await message.answer(
        f"🔍 Поиск игрока <code>#{player_tag}</code>...",
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

                # Ищем ник - любой h1 с font-bold
                name_elem = soup.find("h1")
                name = name_elem.get_text(strip=True) if name_elem else "Неизвестно"

                # Ищем кубки - любой span с text-brawl-gold
                trophies_elem = soup.find("span", class_="text-brawl-gold")
                trophies = trophies_elem.get_text(strip=True) if trophies_elem else "Неизвестно"

                # Ищем информацию о клубе
                club_name = "Не состоит"
                club_tag = ""
                
                # Ищем секцию с клубом - Club
                club_section = soup.find("span", string=lambda x: x and "Club" in x)
                if club_section:
                    # Находим родительский блок
                    club_div = club_section.find_parent("div", class_=lambda x: x and "flex flex-col" in x)
                    if club_div:
                        # Ищем ссылку на клуб
                        club_link = club_div.find("a", href=lambda x: x and "/club/" in x)
                        if club_link:
                            # Ищем название клуба
                            club_name_elem = club_link.find("p", class_="font-bold")
                            if club_name_elem:
                                club_name = club_name_elem.get_text(strip=True)
                            
                            # Извлекаем тег из href
                            href = club_link.get("href", "")
                            if "/club/" in href:
                                club_tag = href.split("/club/")[-1].rstrip("/")

                # Ищем топ 3 бойцов на подиуме
                top_brawlers = []

                # Ищем все карточки с цифрами 1, 2, 3
                first_place = None
                second_place = None
                third_place = None
                
                # Ищем все div с rounded-full (кружочки с номерами)
                rank_circles = soup.find_all("div", class_="rounded-full")
                
                for circle in rank_circles:
                    rank_text = circle.get_text(strip=True)
                    if rank_text not in ["1", "2", "3"]:
                        continue
                    
                    # Ищем родительскую карточку
                    card = circle.find_parent("div", class_=lambda x: x and "flex-col" in x and "items-center" in x)
                    if not card:
                        continue
                    
                    # Ищем имя и кубки в карточке
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

                # Собираем топ 3 в правильном порядке
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
                    f"🆔 <b>ID:</b> <code>#{player_tag}</code>"
                )

                # Добавляем информацию о клубе
                if club_name != "Не состоит":
                    result += f"\n\n🏰 <b>Клан:</b> <code>{club_name}</code>"
                    if club_tag:
                        result += f" <code>#{club_tag}</code>"

                if top_brawlers:
                    result += "\n\n<b>🎯 Топ 3 бойца:</b>\n"
                    for i, (b_name, b_trophies) in enumerate(top_brawlers, 1):
                        result += f"{i}. <code>{b_name}</code> - <b>{b_trophies}</b>\n"

                # Добавляем кнопку "Бойцы"
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
    await message.answer(
        f"🔍 Поиск клана <code>#{clan_tag}</code>...",
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
                    f"🆔 <b>ID:</b> <code>#{clan_tag}</code>"
                )

                await message.answer(result, parse_mode="HTML")

        except Exception as e:
            logging.error(f"Ошибка при запросе клана: {e}")
            await message.answer(
                "❌ <b>Произошла ошибка</b> при получении данных",
                parse_mode="HTML"
            )


async def get_brawlers_info(message: Message, tag_clean: str, player_tag: str, page: int, callback: CallbackQuery = None):
    """Получение списка всех бойцов игрока с пагинацией"""
    user_id = message.from_user.id

    # Если это новая страница (не из кэша или кэш пуст), загружаем данные
    if user_id not in user_brawlers or user_brawlers[user_id]["tag_clean"] != tag_clean or not user_brawlers[user_id].get("brawlers"):
        await message.answer(
            f"🔍 Загрузка бойцов игрока <code>#{player_tag}</code>...",
            parse_mode="HTML"
        )

        url = f"https://brawlify.com/player/{tag_clean}/brawlers"

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

                    # Ищем все карточки бойцов - article с data-id
                    brawler_cards = soup.find_all("article", class_=lambda x: x and "brawler-card" in x)

                    brawlers_list = []
                    for card in brawler_cards:
                        brawler_id = card.get("data-id")
                        brawler_name = card.get("data-name")
                        brawler_power = card.get("data-power")
                        brawler_trophies = card.get("data-trophies")
                        brawler_rank = card.get("data-rank")

                        if brawler_name and brawler_trophies:
                            # Преобразуем кубки в число для сортировки
                            trophies_num = int(brawler_trophies.replace(",", "")) if brawler_trophies.replace(",", "").isdigit() else 0

                            brawlers_list.append({
                                "name": brawler_name,
                                "power": brawler_power or "?",
                                "trophies": brawler_trophies,
                                "trophies_num": trophies_num,
                                "rank": brawler_rank or "?"
                            })

                    logging.info(f"Найдено бойцов: {len(brawlers_list)}")
                    
                    # Сортируем по кубкам (по убыванию)
                    brawlers_list.sort(key=lambda x: x["trophies_num"], reverse=True)
                    
                    # Сохраняем в кэш
                    user_brawlers[user_id] = {
                        "brawlers": brawlers_list,
                        "page": 0,
                        "tag_clean": tag_clean,
                        "player_tag": player_tag
                    }
                    
            except Exception as e:
                logging.error(f"Ошибка при запросе бойцов: {e}")
                await message.answer(
                    "❌ <b>Произошла ошибка</b> при получении данных",
                    parse_mode="HTML"
                )
                return
    
    # Получаем данные из кэша
    brawlers_list = user_brawlers[user_id]["brawlers"]
    total_pages = (len(brawlers_list) + 14) // 15  # Округляем вверх
    
    if page >= total_pages:
        page = total_pages - 1
    if page < 0:
        page = 0
    
    user_brawlers[user_id]["page"] = page
    
    # Получаем 15 бойцов для текущей страницы
    start_idx = page * 15
    end_idx = min(start_idx + 15, len(brawlers_list))
    page_brawlers = brawlers_list[start_idx:end_idx]
    
    # Формируем сообщение
    result = f"🎮 <b>Бойцы игрока</b> <code>#{player_tag}</code>\n\n"
    
    for i, brawler in enumerate(page_brawlers, start_idx + 1):
        result += f"{i}. <b>{brawler['name']}</b> — Сила <code>{brawler['power']}</code> — 🏆 <code>{brawler['trophies']}</code>\n"
    
    result += f"\n📄 Страница <b>{page + 1}/{total_pages}</b>"
    
    # Добавляем кнопки навигации
    keyboard = []
    row = []
    
    safe_tag = tag_clean.replace("#", "")
    
    if page > 0:
        row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"brawlers_page_{safe_tag}_{page - 1}"))
    
    if page < total_pages - 1:
        row.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"brawlers_page_{safe_tag}_{page + 1}"))
    
    if row:
        keyboard.append(row)
    
    # Добавляем кнопку "Обновить"
    keyboard.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"brawlers_list_{safe_tag}_{player_tag}")])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None

    if callback:
        await callback.message.edit_text(result, parse_mode="HTML", reply_markup=reply_markup)
    else:
        await message.answer(result, parse_mode="HTML", reply_markup=reply_markup)


@dp.callback_query(F.data.startswith("brawlers_"))
async def callback_brawlers_page(callback: CallbackQuery):
    """Обработчик нажатия кнопок пагинации бойцов"""
    data = callback.data.split("_")

    # Обработка кнопки "Бойцы" из профиля игрока
    if data[1] == "list" and len(data) >= 4:
        tag_clean = data[2]
        player_tag = "_".join(data[3:])  # На случай если в теге есть подчёркивания
        
        # Сохраняем в кэш
        user_brawlers[callback.from_user.id] = {
            "brawlers": [],
            "page": 0,
            "tag_clean": tag_clean,
            "player_tag": player_tag
        }
        await get_brawlers_info(callback.message, tag_clean, player_tag, 0)
        await callback.answer()
        return
    
    # Обработка пагинации (brawlers_page_TAG_PAGE)
    if data[1] == "page" and len(data) >= 4:
        tag_clean = data[2]
        try:
            page = int(data[3])
        except ValueError:
            await callback.answer()
            return
        
        # Получаем player_tag из кэша или используем tag_clean
        player_tag = tag_clean
        if callback.from_user.id in user_brawlers:
            if user_brawlers[callback.from_user.id]["tag_clean"] == tag_clean:
                player_tag = user_brawlers[callback.from_user.id]["player_tag"]
        
        await get_brawlers_info(callback.message, tag_clean, player_tag, page, callback=callback)
        await callback.answer()
        return
    
    # Старый формат (brawlers_TAG_PAGE) для совместимости
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