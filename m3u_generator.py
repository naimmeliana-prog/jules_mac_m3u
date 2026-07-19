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
                url += "&dummy=vod/movie.mp4"
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
            
            # Fetch episodes using season_id
            ep_res = request("series", "get_ordered_list", movie_id=season_id)
            if ep_res and "js" in ep_res and "data" in ep_res["js"]:
                episodes = ep_res["js"]["data"]
                
                # Check if episodes array actually has elements
                if episodes:
                    for ep in episodes:
                        # Some portals return Season itself as an episode when it's not divided into episodes, but has a "series" array of ints inside.
                        ep_title = ep.get("name", f"Episode")
                        ep_series_arr = ep.get("series", [])
                        
                        if ep_series_arr and isinstance(ep_series_arr, list) and len(ep_series_arr) > 0 and type(ep_series_arr[0]) == int:
                            # It's a season container with episode numbers
                            for ep_num in ep_series_arr:
                                ep_name = f"{series_name} - S{season_num:02d}E{ep_num:02d}"
                                cmd_data = {
                                    "series_id": int(series_id),
                                    "season_num": season_num,
                                    "episode_num": ep_num,
                                    "type": "series"
                                }
                                cmd_str = base64.b64encode(json.dumps(cmd_data).encode('utf-8')).decode('utf-8')
                                link_res = request("vod", "create_link", cmd=cmd_str, series="", forced_storage=0, disable_ad=0, JsHttpRequest="1-xml")
                                if link_res and "js" in link_res and isinstance(link_res["js"], dict) and "cmd" in link_res["js"]:
                                    url = clean_cmd(link_res["js"]["cmd"])
                                    if url:
                                        if "?" in url:
                                            url += "&dummy=series/episode.mp4"
                                        else:
                                            url += "?dummy=series/episode.mp4"
                                        extinf = f'#EXTINF:-1 tvg-logo="{logo}" group-title="{cat_name} (Series)" description="{desc}" year="{year}" director="{director}" actors="{actors}",{ep_name}'
                                        series_output.append(f'{extinf}\n{url}')
                        else:
                            # It's a direct episode with a cmd
                            ep_name = f"{series_name} - {season_name} - {ep_title}"
                            ep_cmd = ep.get("cmd")
                            if ep_cmd:
                                link_res = request("vod", "create_link", cmd=ep_cmd, series="", forced_storage=0, disable_ad=0, JsHttpRequest="1-xml")
                                if link_res and "js" in link_res and isinstance(link_res["js"], dict) and "cmd" in link_res["js"]:
                                    url = clean_cmd(link_res["js"]["cmd"])
                                    if url:
                                        if "?" in url:
                                            url += "&dummy=series/episode.mp4"
                                        else:
                                            url += "?dummy=series/episode.mp4"
                                        extinf = f'#EXTINF:-1 tvg-logo="{logo}" group-title="{cat_name} (Series)" description="{desc}" year="{year}" director="{director}" actors="{actors}",{ep_name}'
                                        series_output.append(f'{extinf}\n{url}')
                else:
                    # Fallback to season's 'series' array
                    ep_nums = season.get("series", [])
                    if not ep_nums:
                        ep_nums = [1]
                    for ep_num in ep_nums:
                        ep_name = f"{series_name} - S{season_num:02d}E{ep_num:02d}"
                        cmd_data = {
                            "series_id": int(series_id),
                            "season_num": season_num,
                            "episode_num": ep_num,
                            "type": "series"
                        }
                        cmd_str = base64.b64encode(json.dumps(cmd_data).encode('utf-8')).decode('utf-8')
                        link_res = request("vod", "create_link", cmd=cmd_str, series="", forced_storage=0, disable_ad=0, JsHttpRequest="1-xml")
                        if link_res and "js" in link_res and isinstance(link_res["js"], dict) and "cmd" in link_res["js"]:
                            url = clean_cmd(link_res["js"]["cmd"])
                            if url:
                                if "?" in url:
                                    url += "&dummy=series/episode.mp4"
                                else:
                                    url += "?dummy=series/episode.mp4"
                                extinf = f'#EXTINF:-1 tvg-logo="{logo}" group-title="{cat_name} (Series)" description="{desc}" year="{year}" director="{director}" actors="{actors}",{ep_name}'
                                series_output.append(f'{extinf}\n{url}')
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
