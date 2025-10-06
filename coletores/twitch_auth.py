import requests, json, os, time

def get_token(auth_path="auth.json", token_path="token.json"):
    """Obtém e salva o token de acesso da Twitch."""
    
    # se já tem token salvo, tenta usar
    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            dados = json.load(f)
        # verifica se ainda é válido
        if "access_token" in dados and "expires_at" in dados:
            if time.time() < dados["expires_at"]:
                return dados["access_token"]

    # se não tem token válido, gera um novo
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

    # calcula o tempo de expiração absoluta (em segundos UNIX)
    dados["expires_at"] = time.time() + dados.get("expires_in", 0)

    # salva token no cache
    with open(token_path, "w") as f:
        json.dump(dados, f, indent=4)

    print(f"Novo token gerado e salvo em {token_path}")
    return dados["access_token"]


if __name__ == "__main__":
    token = get_token()
    print("Token ativo:", token)
