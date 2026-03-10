import requests

# Получаем все IP-диапазоны Google Cloud (Railway использует GCP)
data = requests.get('https://www.gstatic.com/ipranges/cloud.json').json()

# Выводим все IPv4 диапазоны
for prefix in data['prefixes']:
    if 'ipv4Prefix' in prefix:
        print(prefix['ipv4Prefix'])
