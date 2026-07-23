import urllib.request
import urllib.parse
import json
import re
import sys
import concurrent.futures
import base64
import argparse

parser = argparse.ArgumentParser(description="M3U Generator")
parser.add_argument("--type", type=str, choices=["tv", "vod", "series"], required=True, help="Type of content to fetch")
parser.add_argument("--lang", type=str, choices=["es", "fr", "en"], required=True, help="Language to fetch")
parser.add_argument("--limit", type=int, default=0, help="Limit number of categories for testing")
args = parser.parse_args()

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
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return None

def clean_cmd(cmd):
    if not cmd:
        return ""
    if cmd.startswith("ffmpeg "):
        cmd = cmd[7:]
    if cmd.startswith("auto "):
        cmd = cmd[5:]
    return cmd

def is_target_lang(cat_name, lang):
    lower_cat = cat_name.lower()
    if lang == "es":
        return re.search(r'(?:es|esp)\|', lower_cat) or re.search(r'\|(?:es|esp)', lower_cat) or "español" in lower_cat or "espagne" in lower_cat
    elif lang == "fr":
        return re.search(r'(?:fr|fra)\|', lower_cat) or re.search(r'\|(?:fr|fra)', lower_cat) or "français" in lower_cat or "france" in lower_cat
    elif lang == "en":
        return re.search(r'(?:en|eng|uk)\|', lower_cat) or re.search(r'\|(?:en|eng|uk)', lower_cat) or "english" in lower_cat or "uk" in lower_cat or "usa" in lower_cat
    return False

res = request("stb", "handshake")
if res and "js" in res and "token" in res["js"]:
    headers["Authorization"] = f"Bearer {res['js']['token']}"

m3u_output = ["#EXTM3U"]
file_name = f"{args.type}_{args.lang}.m3u"

if args.type == "tv":
    print(f"Processing Live TV for {args.lang}...", file=sys.stderr)
    live_genres_res = request("itv", "get_genres")
    if live_genres_res and "js" in live_genres_res:
        live_genres = {g['id']: g['title'] for g in live_genres_res['js'] if g['id'] != '*'}

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            def fetch_live_cat(genre_id, genre_name):
                cat_output = []
                page = 1
                while True:
                    channels_res = request("itv", "get_ordered_list", genre=genre_id, force_ch_link_check="", p=page)
                    if channels_res and "js" in channels_res and "data" in channels_res["js"] and channels_res["js"]["data"]:
                        for ch in channels_res["js"]["data"]:
                            name = ch.get("name", "Unknown Channel")
                            logo = ch.get("logo", "")
                            cmd = ch.get("cmd", "")
                            url = clean_cmd(cmd)
                            if url:
                                cat_output.append(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{genre_name}",{name}\n{url}')
                        page += 1
                    else:
                        break
                return cat_output

            futures = []
            count = 0
            for genre_id, genre_name in live_genres.items():
                if is_target_lang(genre_name, args.lang):
                    print(f"Cat Live: {genre_name}", file=sys.stderr)
                    futures.append(executor.submit(fetch_live_cat, genre_id, genre_name))
                    count += 1
                    if args.limit > 0 and count >= args.limit:
                        break

            for future in concurrent.futures.as_completed(futures):
                res_lines = future.result()
                m3u_output.extend(res_lines)

elif args.type == "vod":
    print(f"Processing VOD for {args.lang}...", file=sys.stderr)
    vod_cats_res = request("vod", "get_categories")

    def get_vod_link(v, cat_name):
        name = v.get("name", "Unknown Movie")
        logo = v.get("screenshot_uri", "")
        cmd = v.get("cmd", "")
        desc = str(v.get("description", "")).replace('\n', ' ').replace('\r', '').replace('"', "'")
        year = v.get("year", "")
        director = str(v.get("director", "")).replace('"', "'")
        actors = str(v.get("actors", "")).replace('"', "'")

        link_res = request("vod", "create_link", cmd=cmd, series=0, forced_storage=0, disable_ad=0, JsHttpRequest="1-xml")
        if link_res and "js" in link_res and isinstance(link_res["js"], dict) and "cmd" in link_res["js"]:
            url = clean_cmd(link_res["js"]["cmd"])
            if url:
                if "dummy=/movie/" not in url:
                    if "?" in url:
                        url += "&dummy=/movie/&type=movie"
                    else:
                        url += "?dummy=/movie/&type=movie"
                extinf = f'#EXTINF:-1 tvg-logo="{logo}" group-title="{cat_name}" description="{desc}" year="{year}" director="{director}" actors="{actors}",{name}'
                return f"{extinf}\n{url}"
        return None

    if vod_cats_res and "js" in vod_cats_res:
        vod_cats = [(c['id'], c['title']) for c in vod_cats_res['js'] if c['id'] != '*']
        count = 0
        for cat_id, cat_name in vod_cats:
            if is_target_lang(cat_name, args.lang):
                print(f"Cat VOD: {cat_name}", file=sys.stderr)
                page = 1
                all_vods = []
                while True:
                    vods_res = request("vod", "get_ordered_list", genre=cat_id, p=page)
                    if vods_res and "js" in vods_res and "data" in vods_res["js"] and vods_res["js"]["data"]:
                        all_vods.extend(vods_res["js"]["data"])
                        page += 1
                    else:
                        break
                with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
                    futures = [executor.submit(get_vod_link, v, cat_name) for v in all_vods]
                    for future in concurrent.futures.as_completed(futures):
                        res_str = future.result()
                        if res_str: m3u_output.append(res_str)
                count += 1
                if args.limit > 0 and count >= args.limit:
                    break

elif args.type == "series":
    print(f"Processing Series for {args.lang}...", file=sys.stderr)
    series_cats_res = request("series", "get_categories")

    def process_series(s, cat_name):
        series_output = []
        series_name = s.get("name", "Unknown Series")
        series_id = s.get("id")
        if ":" in str(series_id):
            series_id = str(series_id).split(":")[0]

        logo = s.get("screenshot_uri", "")
        desc = str(s.get("description", "")).replace('\n', ' ').replace('\r', '').replace('"', "'")
        year = s.get("year", "")
        director = str(s.get("director", "")).replace('"', "'")
        actors = str(s.get("actors", "")).replace('"', "'")

        s_res = request("series", "get_ordered_list", movie_id=series_id)
        if s_res and "js" in s_res and "data" in s_res["js"]:
            seasons = s_res["js"]["data"]
            for season in seasons:
                season_id = season.get("id")
                season_name = season.get("name", "Season 1")

                season_num = 1
                sn_match = re.search(r'\d+', season_name)
                if sn_match:
                    season_num = int(sn_match.group())

                episodes = season.get("series", [])
                if not episodes:
                    episodes = [1]

                for ep_num in episodes:
                    ep_name = f"{series_name} - S{season_num:02d}E{int(ep_num):02d}"
                    
                    cmd_data = {
                        "series_id": int(series_id),
                        "season_num": season_num,
                        "episode_num": int(ep_num),
                        "type": "series"
                    }
                    cmd_str = base64.b64encode(json.dumps(cmd_data, separators=(',', ':')).encode('utf-8')).decode('utf-8')

                    link_res = request("vod", "create_link", cmd=cmd_str, series=ep_num, forced_storage=0, disable_ad=0, JsHttpRequest="1-xml")
                    if link_res and "js" in link_res and isinstance(link_res["js"], dict) and "cmd" in link_res["js"]:
                        url = clean_cmd(link_res["js"]["cmd"])
                        if url:
                            if "dummy=/series/" not in url:
                                if "?" in url:
                                    url += "&dummy=/series/&type=movie"
                                else:
                                    url += "?dummy=/series/&type=movie"

                            extinf = f'#EXTINF:-1 tvg-logo="{logo}" group-title="{cat_name}" description="{desc}" year="{year}" director="{director}" actors="{actors}",{ep_name}'
                            series_output.append(f'{extinf}\n{url}')
        return series_output

    if series_cats_res and "js" in series_cats_res:
        series_cats = [(c['id'], c['title']) for c in series_cats_res['js'] if c['id'] != '*']
        count = 0
        for cat_id, cat_name in series_cats:
            if is_target_lang(cat_name, args.lang):
                print(f"Cat Series: {cat_name}", file=sys.stderr)
                page = 1
                all_series = []
                while True:
                    series_res = request("series", "get_ordered_list", genre=cat_id, p=page)
                    if series_res and "js" in series_res and "data" in series_res["js"] and series_res["js"]["data"]:
                        all_series.extend(series_res["js"]["data"])
                        page += 1
                    else:
                        break

                with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                    futures = [executor.submit(process_series, s, cat_name) for s in all_series]
                    for future in concurrent.futures.as_completed(futures):
                        res_lines = future.result()
                        if res_lines:
                            m3u_output.extend(res_lines)
                count += 1
                if args.limit > 0 and count >= args.limit:
                    break

with open(file_name, "w", encoding='utf-8') as f:
    f.write("\n".join(m3u_output))
print(f"Saved {len(m3u_output) - 1} items to {file_name}", file=sys.stderr)
