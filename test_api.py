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
        print(f"Error: {e}")
        return None

res = request("stb", "handshake")
if res and "js" in res and "token" in res["js"]:
    headers["Authorization"] = f"Bearer {res['js']['token']}"

# Let's get series categories
series_cats = request("series", "get_categories")
print("Series categories:", [c['title'] for c in series_cats.get('js', [])])

# Let's get series for a category
first_cat = series_cats['js'][1]['id']
series_list = request("series", "get_ordered_list", genre=first_cat, p=1)
if series_list and series_list.get('js') and series_list['js'].get('data'):
    first_series = series_list['js']['data'][0]
    print("First series:", first_series.get('name'), "ID:", first_series.get('id'))
    
    # Get seasons for this series
    seasons = request("series", "get_ordered_list", movie_id=first_series['id'])
    print("Seasons structure:")
    print(json.dumps(seasons['js']['data'], indent=2))
