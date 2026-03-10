import urllib.request
import json

# Получаем все IP-диапазоны Google Cloud
url = 'https://www.gstatic.com/ipranges/cloud.json'
response = urllib.request.urlopen(url)
data = json.loads(response.read())

# Выводим все IPv4 диапазоны
for prefix in data['prefixes']:
    if 'ipv4Prefix' in prefix:
        print(prefix['ipv4Prefix'])
