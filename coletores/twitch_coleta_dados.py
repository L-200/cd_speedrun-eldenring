from twitch_auth import get_token
import requests, json

token = get_token()

with open("auth.json", "r") as f:
    auth = json.load(f)
CLIENT_ID = auth["client_id"]

headers = {
    "Client-ID": CLIENT_ID,
    "Authorization": f"Bearer {token}"
}

usuario = "hama7"
url = f"https://api.twitch.tv/helix/users?login={usuario}"

response = requests.get(url, headers=headers)
dados = response.json()

print(json.dumps(dados, indent=4))
