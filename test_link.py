import urllib.request
import urllib.parse
import json
import base64

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

# Use a known series and season from previous output
cmd_data = {
    "series_id": 50355,
    "season_num": 1,
    "episode_num": 1,
    "type": "series"
}
cmd_str = base64.b64encode(json.dumps(cmd_data, separators=(',', ':')).encode('utf-8')).decode('utf-8')
print("cmd_str:", cmd_str)

link_res = request("vod", "create_link", cmd=cmd_str, series=1, forced_storage=0, disable_ad=0, JsHttpRequest="1-xml")
print(json.dumps(link_res, indent=2))
