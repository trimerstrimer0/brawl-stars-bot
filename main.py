import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import os

TOKEN = os.environ.get("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

API_KEY = os.environ.get("BS_API_KEY")

BASE_URL = "https://api.brawlstars.com/v1"

TCP_PROXY = os.environ.get("TCP_PROXY")

user_brawlers = {}
processed_updates = set()

# Заголовки для API
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json"
}


async def check_proxy():
    """Проверить работу прокси и показать IP"""
    try:
        print(f"🔍 Проверяем прокси: {TCP_PROXY}")
        
        # Настройки для прокси
        connector = aiohttp.TCPConnector(ssl=False)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            # IP через прокси
            try:
                async with session.get('https://api.ipify.org', proxy=TCP_PROXY, timeout=15) as resp:
                    if resp.status == 200:
                        proxy_ip = await resp.text()
                        print(f"✅ IP через прокси: {proxy_ip.strip()}")
                    else:
                        print(f"❌ Прокси вернул статус: {resp.status}")
                        return None
            except aiohttp.ClientProxyConnectionError as e:
                print(f"❌ Ошибка подключения к прокси: {e}")
                return None
            except Exception as e:
                print(f"❌ Ошибка при запросе через прокси: {e}")
                return None
            
            # Прямой IP
            async with session.get('https://api.ipify.org', timeout=5) as resp:
                direct_ip = await resp.text()
                print(f"🖥️ Прямой IP сервера: {direct_ip.strip()}")
            
            print(f"\n📝 Добавьте этот IP в белый список Brawl Stars API: {proxy_ip.strip()}")
            print("-" * 50)
            
            return proxy_ip.strip()
            
    except Exception as e:
        print(f"❌ Общая ошибка проверки прокси: {e}")
        return None


async def make_brawl_request(url):
    """Запрос к Brawl Stars API через прокси Railway"""
    try:
        logging.info(f"Запрос через прокси: {TCP_PROXY}")
        
        connector = aiohttp.TCPConnector(ssl=False)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(
                url,
                headers=HEADERS,
                proxy=TCP_PROXY,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logging.error(f"Ошибка API: {response.status} - {error_text}")
                    
                    if response.status == 403:
                        async with session.get('https://api.ipify.org', proxy=TCP_PROXY) as ip_resp:
                            proxy_ip = await ip_resp.text()
                            logging.error(f"❌ IP прокси ({proxy_ip.strip()}) не в белом списке!")
                    
                    return None
                    
    except aiohttp.ClientProxyConnectionError as e:
        logging.error(f"Ошибка подключения к прокси: {e}")
        return None
    except Exception as e:
        logging.error(f"Ошибка при запросе: {e}")
        return None


async def get_server_ip():
    """Просто вывести IP в консоль"""
    try:
        async with aiohttp.ClientSession() as session:
            # Сервис 1
            async with session.get('https://api.ipify.org', timeout=5) as resp:
                ip1 = await resp.text()
                print(f"IP сервера (api.ipify.org): {ip1.strip()}")
            
            # Сервис 2
            async with session.get('https://ifconfig.me/ip', timeout=5) as resp:
                ip2 = await resp.text()
                print(f"IP сервера (ifconfig.me): {ip2.strip()}")
            
            # Сервис 3
            async with session.get('https://icanhazip.com', timeout=5) as resp:
                ip3 = await resp.text()
                print(f"IP сервера (icanhazip.com): {ip3.strip()}")
            
            return ip1.strip()
    except Exception as e:
        print(f"Ошибка получения IP: {e}")
        return None


@dp.message(Command("start"))
async def cmd_start(message: Message):
    update_id = f"msg_{message.chat.id}_{message.message_id}"
    if update_id in processed_updates:
        return
    processed_updates.add(update_id)
    if len(processed_updates) > 1000:
        processed_updates.clear()

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
    update_id = f"msg_{message.chat.id}_{message.message_id}"
    if update_id in processed_updates:
        return
    processed_updates.add(update_id)
    if len(processed_updates) > 1000:
        processed_updates.clear()

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
    logging.info(f"Запрос игрока: {tag_clean}")
    display_tag = player_tag if player_tag.startswith('#') else f"#{player_tag}"
    await message.answer(
        f"🔍 Поиск игрока <code>{display_tag}</code>...",
        parse_mode="HTML"
    )

    url = f"{BASE_URL}/players/%23{tag_clean}"

    data = await make_brawl_request(url)
    if data:
        name = data.get("name", "Неизвестно")
        trophies = data.get("trophies", "Неизвестно")
        tag = data.get("tag", f"#{tag_clean}")

        club_name = data.get("club", {}).get("name", "Не состоит")
        club_tag = data.get("club", {}).get("tag", "")

        result = (
            f"🎮 <b>Игрок найден!</b>\n\n"
            f"👤 <b>Ник:</b> <code>{name}</code>\n"
            f"🏆 <b>Кубки:</b> <code>{trophies}</code>\n"
            f"🆔 <b>ID:</b> <code>{tag}</code>"
        )

        if club_name and club_name != "None":
            result += f"\n\n🏰 <b>Клан:</b> <code>{club_name}</code>"
            if club_tag:
                result += f" <code>{club_tag}</code>"

        # Топ 3 бойца
        brawlers = data.get("brawlers", [])
        if brawlers:
            top_brawlers = sorted(brawlers, key=lambda x: x.get("trophies", 0), reverse=True)[:3]
            result += "\n\n<b>🎯 Топ 3 бойца:</b>\n"
            for i, brawler in enumerate(top_brawlers, 1):
                result += f"{i}. <code>{brawler.get('name', 'Unknown')}</code> - <b>{brawler.get('trophies', 0)}</b>\n"

        safe_tag = tag_clean
        keyboard = [
            [
                InlineKeyboardButton(text="🎮 Бойцы", callback_data=f"brawlers_list_{safe_tag}"),
                InlineKeyboardButton(text="⚔️ Матчи", callback_data=f"matches_list_{safe_tag}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        await message.answer(result, parse_mode="HTML", reply_markup=reply_markup)
    else:
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

    url = f"{BASE_URL}/clubs/%23{tag_clean}"

    data = await make_brawl_request(url)
    if data:
        clan_name = data.get("name", "Неизвестно")
        clan_trophies = data.get("trophies", "Неизвестно")
        members = data.get("members", {}).get("total", "Неизвестно") if isinstance(data.get("members"), dict) else len(data.get("members", []))
        description = data.get("description", "Нет описания") or "Нет описания"

        result = (
            f"🏰 <b>Клан найден!</b>\n\n"
            f"📛 <b>Название:</b> <code>{clan_name}</code>\n"
            f"🏆 <b>Кубки:</b> <code>{clan_trophies}</code>\n"
            f"👥 <b>Участников:</b> <code>{members}</code>\n"
            f"📝 <b>Описание:</b> <i>{description}</i>\n"
            f"🆔 <b>ID:</b> <code>#{data.get('tag', tag_clean)}</code>"
        )

        await message.answer(result, parse_mode="HTML")
    else:
        await message.answer(
            "❌ <b>Произошла ошибка</b> при получении данных",
            parse_mode="HTML"
        )


async def get_brawlers_info(message: Message, tag_clean: str, player_tag: str, page: int, callback: CallbackQuery = None, is_list: bool = False):
    if callback:
        user_id = callback.from_user.id
    else:
        user_id = message.from_user.id
    display_tag = player_tag if player_tag.startswith('#') else f"#{player_tag}"

    if user_id not in user_brawlers or user_brawlers[user_id]["tag_clean"] != tag_clean or not user_brawlers[user_id].get("brawlers"):
        if not callback:
            await message.answer(
                f"🔍 Загрузка бойцов игрока <code>{display_tag}</code>...",
                parse_mode="HTML"
            )

        url = f"{BASE_URL}/players/%23{tag_clean}"
        data = await make_brawl_request(url)

        if not data:
            error_msg = "❌ <b>Произошла ошибка</b> при получении данных"
            if callback:
                await callback.message.edit_text(error_msg, parse_mode="HTML")
            else:
                await message.answer(error_msg, parse_mode="HTML")
            return

        brawlers_data = data.get("brawlers", [])

        brawlers_list = []
        for brawler in brawlers_data:
            brawlers_list.append({
                "name": brawler.get("name", "Unknown"),
                "power": brawler.get("power", "?"),
                "trophies": str(brawler.get("trophies", 0)),
                "trophies_num": brawler.get("trophies", 0),
            })

        logging.info(f"Найдено бойцов: {len(brawlers_list)}")
        brawlers_list.sort(key=lambda x: x["trophies_num"], reverse=True)

        user_brawlers[user_id] = {
            "brawlers": brawlers_list,
            "page": 0,
            "tag_clean": tag_clean,
            "player_tag": player_tag
        }

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

    safe_tag = tag_clean

    if page > 0:
        row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"brawlers_page_{safe_tag}_{page - 1}"))

    if page < total_pages - 1:
        row.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"brawlers_page_{safe_tag}_{page + 1}"))

    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"brawlers_list_{safe_tag}")])

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    if callback:
        if is_list:
            await callback.message.answer(result, parse_mode="HTML", reply_markup=reply_markup)
        else:
            await callback.message.edit_text(result, parse_mode="HTML", reply_markup=reply_markup)
        await callback.answer()
    else:
        await message.answer(result, parse_mode="HTML", reply_markup=reply_markup)


@dp.callback_query(F.data.startswith("brawlers_"))
async def callback_brawlers_page(callback: CallbackQuery):
    update_id = f"cb_{callback.id}"
    if update_id in processed_updates:
        await callback.answer()
        return
    processed_updates.add(update_id)
    if len(processed_updates) > 1000:
        processed_updates.clear()

    data = callback.data.split("_")
    logging.info(f"Callback data: {data}")

    if len(data) >= 3 and data[1] == "list":
        tag_clean = data[2]
        player_tag = tag_clean

        user_brawlers[callback.from_user.id] = {
            "brawlers": [],
            "page": 0,
            "tag_clean": tag_clean,
            "player_tag": player_tag
        }
        await get_brawlers_info(callback.message, tag_clean, player_tag, 0, callback=callback, is_list=True)
        await callback.answer()
        return

    if len(data) >= 4 and data[1] == "page":
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


@dp.callback_query(F.data.startswith("matches_"))
async def callback_matches_page(callback: CallbackQuery):
    update_id = f"cb_{callback.id}"
    if update_id in processed_updates:
        await callback.answer()
        return
    processed_updates.add(update_id)
    if len(processed_updates) > 1000:
        processed_updates.clear()

    data = callback.data.split("_")

    if len(data) >= 3 and data[1] == "list":
        tag_clean = data[2]
        player_tag = tag_clean
        await get_matches_info(callback.message, tag_clean, player_tag, callback=None)
        await callback.answer()
        return

    await callback.answer()


async def get_matches_info(message: Message, tag_clean: str, player_tag: str, callback: CallbackQuery = None):
    """Получение последних матчей игрока"""
    display_tag = player_tag if player_tag.startswith('#') else f"#{player_tag}"

    await message.answer(
        f"🔍 Загрузка матчей игрока <code>{display_tag}</code>...",
        parse_mode="HTML"
    )

    url = f"{BASE_URL}/players/%23{tag_clean}/battlelog"

    data = await make_brawl_request(url)
    if not data:
        await message.answer(
            "❌ <b>Произошла ошибка</b> при получении данных",
            parse_mode="HTML"
        )
        return

    logging.info(f"Ответ API (матчи): {type(data)}")

    # API возвращает {'items': [...]}
    if isinstance(data, dict):
        matches_list = data.get("items", [])
    else:
        matches_list = data

    if not matches_list:
        await message.answer(
            "❌ Не удалось загрузить матчи",
            parse_mode="HTML"
        )
        return

    # Показываем последние 10 матчей
    display_matches = matches_list[:10]

    result = f"⚔️ <b>Последние матчи</b> <code>{display_tag}</code>\n\n"

    for i, match in enumerate(display_matches, 1):
        event = match.get("event", {})
        # Название режима — красиво на английском
        mode_raw = event.get("mode", "Unknown")
        mode_map = {
            "brawlBall": "⚽ Brawl Ball",
            "knockout": "🏆 Knockout",
            "bounty": "💰 Bounty",
            "heist": "🔐 Heist",
            "hotZone": "🎯 Hot Zone",
            "gemGrab": "💎 Gem Grab",
            "siege": "🤖 Siege",
            "duoShowdown": "👥 Duo Showdown",
            "soloShowdown": "☠️ Solo Showdown",
            "basketBrawl": "🏀 Basket Brawl",
            "holdTheTrophy": "🏆 Hold the Trophy",
            "volleyBrawl": "🏐 Volley Brawl",
            "brawlHockey": "🏒 Brawl Hockey",
            "payload": "📦 Payload",
            "wipedown": "🧼 Wipe Down",
            "trophythieves": "🦹 Trophy Thieves"
        }
        mode = mode_map.get(mode_raw, mode_raw)
        map_name = event.get("map", "Unknown")

        # Результат в battle, а не в корне match
        battle = match.get("battle", {})
        result_match = battle.get("result", "Unknown")

        if result_match == "victory":
            result_text = "🟢 <b>Victory</b>"
        elif result_match == "defeat":
            result_text = "🔴 <b>Defeat</b>"
        elif result_match == "draw":
            result_text = "🟡 <b>Draw</b>"
        else:
            rank = battle.get("rank", 0)
            if rank == 1:
                result_text = "🥇 <b>1st Place</b>"
            elif rank == 2:
                result_text = "🥈 <b>2nd Place</b>"
            elif rank == 3:
                result_text = "🥉 <b>3rd Place</b>"
            else:
                result_text = f"<b>{rank}th Place</b>"

        # Боец из команды
        brawler_name = "?"
        teams = battle.get("teams", [])
        for team in teams:
            for player in team:
                if player.get("tag") == f"#{tag_clean}":
                    brawler_name = player.get("brawler", {}).get("name", "?")
                    break
            if brawler_name != "?":
                break

        result += f"{i}. {result_text} — <b>{brawler_name}</b>\n"
        result += f"   🎮 {mode} • 🗺️ <i>{map_name}</i>\n\n"

    keyboard = [[InlineKeyboardButton(text="🔄 Обновить", callback_data=f"matches_list_{tag_clean}")]]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await message.answer(result, parse_mode="HTML", reply_markup=reply_markup)


@dp.message(Command("proxy_ip"))
async def cmd_proxy_ip(message: Message):
    """Показать IP прокси"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.ipify.org', proxy=TCP_PROXY, timeout=10) as resp:
                proxy_ip = await resp.text()
                await message.answer(
                    f"🌐 **IP прокси:** `{proxy_ip.strip()}`\n\n"
                    f"Добавьте этот IP в белый список Brawl Stars API",
                    parse_mode="Markdown"
                )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


async def main():
    # Проверяем прокси при запуске
    print("\n" + "="*50)
    print("ПРОВЕРКА ПРОКСИ RAILWAY")
    print("="*50)
    
    proxy_ip = await check_proxy()
    
    if proxy_ip:
        logging.info(f"✅ Прокси работает. IP для белого списка: {proxy_ip}")
    else:
        logging.error("❌ Прокси не работает!")
    
    logging.info("Запуск бота...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
