import urllib.request
import urllib.parse
import json
import re
import sys
import concurrent.futures
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

def is_es_fr_en(cat_name):
    lower_cat = cat_name.lower()
    return re.search(r'(?:es|esp)\|', lower_cat) or re.search(r'\|(?:es|esp)', lower_cat) or "español" in lower_cat or "spain" in lower_cat

def is_es_fr(cat_name):
    lower_cat = cat_name.lower()
    return re.search(r'(?:es|esp)\|', lower_cat) or re.search(r'\|(?:es|esp)', lower_cat) or "español" in lower_cat or "spain" in lower_cat

res = request("stb", "handshake")
if res and "js" in res and "token" in res["js"]:
    headers["Authorization"] = f"Bearer {res['js']['token']}"

m3u_output = ["#EXTM3U"]

print("Processing Live TV...", file=sys.stderr)
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
        for genre_id, genre_name in live_genres.items():
            if is_es_fr_en(genre_name) or genre_name.startswith("ES|") or genre_name.startswith("ESP|"):
                print(f"Cat Live: {genre_name}", file=sys.stderr)
                futures.append(executor.submit(fetch_live_cat, genre_id, genre_name))

        for future in concurrent.futures.as_completed(futures):
            res_lines = future.result()
            m3u_output.extend(res_lines)

print("Processing VOD...", file=sys.stderr)
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
            if "type=movie" not in url:
                url += "&dummy=/movie/video.mp4&type=movie"
            extinf = f'#EXTINF:-1 tvg-logo="{logo}" group-title="{cat_name} (VOD)" description="{desc}" year="{year}" director="{director}" actors="{actors}",{name}'
            return f"{extinf}\n{url}"
    return None

if vod_cats_res and "js" in vod_cats_res:
    vod_cats = [(c['id'], c['title']) for c in vod_cats_res['js'] if c['id'] != '*']
    for cat_id, cat_name in vod_cats:
        if is_es_fr(cat_name):
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

print("Processing Series...", file=sys.stderr)
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

    raw_series = s.get("series", "")
    seasons_data = None
    if isinstance(raw_series, str) and raw_series.strip():
        try:
            seasons_data = json.loads(raw_series)
        except json.JSONDecodeError:
            print(f"[{series_name}] no pude parsear 'series': {raw_series[:200]}", file=sys.stderr)
    elif isinstance(raw_series, list):
        seasons_data = raw_series

    if not seasons_data:
        ss = request("series", "get_seasons", movie_id=series_id)
        if ss and "js" in ss and "data" in ss["js"]:
            seasons_data = ss["js"]["data"]

    if not seasons_data:
        ss = request("series", "get_ordered_list", movie_id=series_id)
        if ss and "js" in ss and "data" in ss["js"]:
            seasons_data = ss["js"]["data"]

    if not seasons_data:
        print(f"[{series_name}] SIN temporadas. raw_series={str(raw_series)[:300]}", file=sys.stderr)
        return series_output

    for season in seasons_data:
        season_id = None
        if isinstance(season, dict):
            season_num = season.get("season_number") or season.get("number")
            if not season_num:
                sn_match = re.search(r'\d+', season.get("name", ""))
                season_num = int(sn_match.group()) if sn_match else 1
            episodes = season.get("episodes", season.get("series", []))
            season_id = season.get("id")
        else:
            season_num = season
            episodes = []

        if isinstance(episodes, str) and episodes.strip():
            try: episodes = json.loads(episodes)
            except: episodes = []

        if not episodes:
            if season_id:
                ep_res = request("series", "get_ordered_list", movie_id=season_id)
                if ep_res and "js" in ep_res and "data" in ep_res["js"]:
                    episodes = ep_res["js"]["data"]
                    
            if not episodes:
                ep_res = request("series", "get_ordered_list", movie_id=series_id, season=season_num)
                if ep_res and "js" in ep_res and "data" in ep_res["js"]:
                    episodes = ep_res["js"]["data"]

        for ep in episodes:
            if isinstance(ep, dict):
                ep_num = ep.get("num") or ep.get("number") or ep.get("episode_num")
                if not ep_num:
                    num_match = re.search(r'\d+', ep.get("name", ""))
                    ep_num = int(num_match.group()) if num_match else None
                ep_title = ep.get("name", "")
                ep_cmd = ep.get("cmd", "")
            else:
                ep_num = ep
                ep_title = ""
                ep_cmd = ""

            if not ep_num:
                continue

            link_res = None
            url = ""
            
            if ep_cmd:
                link_res = request("vod", "create_link", cmd=ep_cmd, series="", forced_storage=0, disable_ad=0, JsHttpRequest="1-xml")
            
            if not link_res or "js" not in link_res or not link_res.get("js", {}).get("cmd"):
                cmd_data = {"series_id": int(series_id), "season_num": season_num, "episode_num": ep_num, "type": "series"}
                cmd_str = base64.b64encode(json.dumps(cmd_data).encode('utf-8')).decode('utf-8')
                link_res = request("vod", "create_link", cmd=cmd_str, series="", forced_storage=0, disable_ad=0, JsHttpRequest="1-xml")

            if not link_res or "js" not in link_res or not link_res.get("js", {}).get("cmd"):
                series_cmd = s.get("cmd", "")
                if series_cmd:
                    link_res = request("series", "create_link", cmd=series_cmd, series=ep_num, forced_storage=0, disable_ad=0, JsHttpRequest="1-xml")
                    
            if not link_res or "js" not in link_res or not link_res.get("js", {}).get("cmd"):
                ep_cmd_format = f"series:/play/series/{season_num}/{ep_num}/{series_id}"
                link_res = request("vod", "create_link", cmd=ep_cmd_format, series="", forced_storage=0, disable_ad=0, JsHttpRequest="1-xml")

            if link_res and "js" in link_res and isinstance(link_res["js"], dict) and "cmd" in link_res["js"]:
                url = clean_cmd(link_res["js"]["cmd"])
                
            if url:
                if "?" in url:
                    url += "&dummy=/series/video.mp4&type=movie"
                else:
                    url += "?dummy=/series/video.mp4&type=movie"
                label = f"{series_name} - S{int(season_num):02d}E{int(ep_num):02d}"
                if ep_title and "Season" not in ep_title and "Episode" not in ep_title:
                    label += " - " + str(ep_title)
                extinf = (f'#EXTINF:-1 tvg-logo="{logo}" group-title="{cat_name} (Series)" '
                          f'description="{desc}" year="{year}" director="{director}" actors="{actors}",'
                          f'{label}')
                series_output.append(f"{extinf}\n{url}")

    return series_output

if series_cats_res and "js" in series_cats_res:
    series_cats = [(c['id'], c['title']) for c in series_cats_res['js'] if c['id'] != '*']
    for cat_id, cat_name in series_cats:
        if is_es_fr(cat_name):
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

with open("lista_iptv.m3u", "w", encoding='utf-8') as f:
    f.write("\n".join(m3u_output))
print("Done", file=sys.stderr)
