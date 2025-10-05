import requests, json, os

def get_token(auth_path="auth.json", token_path="token.json"):
    """Obtem o token de acesso da Twitch, usa o cache em token.json se ja existir um token válido"""
    
    # se ja tem token salvo vai usar ele
    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            dados = json.load(f)
        if "access_token" in dados:
            return dados["access_token"]

    # se nao ele gera um novo token com o auth.json
    with open(auth_path, "r") as f:
        auth = json.load(f)

    CLIENT_ID = auth["client_id"]
    CLIENT_SECRET = auth["client_secret"]

    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }

    response = requests.post(url, params=params)
    dados = response.json()

    if "access_token" not in dados:
        raise Exception(f"Erro ao gerar token: {dados}")
    
    # salva token no arquivo de token_path
    with open("token.json", "w") as f:
        json.dump(dados, f, indent=4)
    print(f"Novo token gerado e salvo em {token_path}")
    return dados["access_token"]    

if __name__ == "__main__":
    token = get_token()
    print("Token ativo:", token)