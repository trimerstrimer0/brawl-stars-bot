import aiohttp
import asyncio
import logging

async def get_railway_ips():
    """Получить все возможные IP Railway"""
    try:
        # Получаем текущий IP
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.ipify.org', timeout=5) as resp:
                current_ip = await resp.text()
                current_ip = current_ip.strip()
                print(f"Текущий IP сервера: {current_ip}")
        
        # Диапазоны IP Railway (нужно добавить в белый список)
        railway_ip_ranges = [
            current_ip,  # Текущий IP
            # Диапазоны Railway (нужно уточнить у поддержки)
            "35.240.0.0/16",    # Примерный диапазон Google Cloud
            "34.120.0.0/16",    # Другой диапазон
        ]
        
        print("\nДобавьте эти IP в белый список Brawl Stars API:")
        print("-" * 50)
        for ip in railway_ip_ranges:
            print(ip)
        print("-" * 50)
        
        return railway_ip_ranges
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return []

# Запуск при старте бота
async def on_startup():
    await get_railway_ips()у
