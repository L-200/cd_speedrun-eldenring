import requests, json, os, time
import pandas as pd
from datetime import datetime, timedelta
from twitch_auth import get_token

# Configuração de saída
output_dir = "../1-coleta"
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, "twitch_stats.csv")

# Carrega credenciais
with open("auth.json", "r") as f:
    auth = json.load(f)

CLIENT_ID = auth["client_id"]
token = get_token()

headers = {
    "Client-ID": CLIENT_ID,
    "Authorization": f"Bearer {token}"
}

usuario_login = "OrbitalHeelKick"
vod_id_recorde = "1537427035"

def get_vod_info(vod_id, contexto="recorde"):
    """Busca informações básicas de um VOD."""
    url = f"https://api.twitch.tv/helix/videos?id={vod_id}"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()["data"][0]
    return {
        "vod_id": data["id"],
        "contexto_video": contexto,
        "streamer_login": data["user_login"],
        "title": data["title"],
        "data_criacao": data["created_at"],
        "views": data["view_count"],
        "duration": data["duration"],
        "url": data["url"]
    }

def get_adjacent_vods_by_date(user_login, vod_id_recorde, days_before=5, days_after=5):
    """Busca VODs dentro da janela temporal antes e depois do recorde, com paginação."""
    user_resp = requests.get(f"https://api.twitch.tv/helix/users?login={user_login}", headers=headers)
    user_id = user_resp.json()["data"][0]["id"]

    vods = []
    cursor = None
    while True:
        url = f"https://api.twitch.tv/helix/videos?user_id={user_id}&first=100"
        if cursor:
            url += f"&after={cursor}"
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        vods.extend(data["data"])
        cursor = data.get("pagination", {}).get("cursor")
        if not cursor:
            break
        time.sleep(0.5)  # evita rate limit

    # Pega a data do recorde
    record_vod = next((v for v in vods if v["id"] == vod_id_recorde), None)
    if not record_vod:
        print("VOD de recorde não encontrado.")
        return []

    record_date = datetime.strptime(record_vod["created_at"], "%Y-%m-%dT%H:%M:%SZ")
    start_date = record_date - timedelta(days=days_before)
    end_date = record_date + timedelta(days=days_after)

    selected = []
    for vod in vods:
        vod_date = datetime.strptime(vod["created_at"], "%Y-%m-%dT%H:%M:%SZ")
        if start_date <= vod_date <= end_date:
            contexto = "recorde" if vod["id"] == vod_id_recorde else \
                       "antes_recorde" if vod_date < record_date else "depois_recorde"
            selected.append({
                "vod_id": vod["id"],
                "contexto_video": contexto,
                "streamer_login": vod["user_login"],
                "title": vod["title"],
                "data_criacao": vod["created_at"],
                "views": vod["view_count"],
                "duration": vod["duration"],
                "url": vod["url"]
            })
    return sorted(selected, key=lambda x: x["data_criacao"])

def collect_twitch_data_and_save():
    dados = get_adjacent_vods_by_date(usuario_login, vod_id_recorde, days_before=5, days_after=5)
    df = pd.DataFrame(dados)
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"{len(df)} VODs coletados e salvos em {output_file}")

if __name__ == "__main__":
    collect_twitch_data_and_save()