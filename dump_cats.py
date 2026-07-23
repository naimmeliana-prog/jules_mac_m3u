import urllib.request
import urllib.parse
import json

mac = "00:1A:79:74:B1:B9"
base_url = "http://mag.greatott.me:80/server/load.php"

headers = {
    "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
    "Cookie": f"mac={mac}",
    "Referer": "http://mag.greatott.me:80/c/"
}

def request(type_, action, **kwargs):
    url = f"{base_url}?type={type_}&action={action}"
    for k, v in kwargs.items():
        url += f"&{k}={urllib.parse.quote(str(v))}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return None

res = request("stb", "handshake")
if res and "js" in res and "token" in res["js"]:
    headers["Authorization"] = f"Bearer {res['js']['token']}"

print("=== ITV Categories ===")
live = request("itv", "get_genres")
if live and live.get('js'):
    for c in live['js']: print(c['title'])

print("\n=== VOD Categories ===")
vod = request("vod", "get_categories")
if vod and vod.get('js'):
    for c in vod['js']: print(c['title'])

print("\n=== Series Categories ===")
series = request("series", "get_categories")
if series and series.get('js'):
    for c in series['js']: print(c['title'])
