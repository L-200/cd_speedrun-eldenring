import requests, json, time, os
import pandas as pd

output_dir = "../1-coleta"
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, "bilibili_stats.csv")

# carrega os headers para evitar o erro http 412 (so montar o user agent)
try:
    with open("bilibili_headers.json", "r") as f:
        headers = json.load(f)
except FileNotFoundError:
    print("ERRO: O arquivo 'bilibili_headers.json' não foi encontrado.")
    
def get_bilibili_stats(bvid_video):
    """
    Busca os dados do vídeo na API publica do Bilibili, extrai algumas métricas
    (views, danmaku, likes) e informações do criador, retorna um dicionário 
    pronto para analise. Retorna None em caso de erro na conexão ou na API.
    """
    api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid_video}"

    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status() # lança exceçao pra outros erros HTTP
        dados = response.json()

        if dados.get("code") == 0 and "stat" in dados["data"]:
            dados = dados.get("data")
            # como tem muito dado e o json é imenso, retorna so alguns, podemos mudar dps
            return {
                "bvid": dados.get("bvid"),
                "title": dados.get("title"),
                "name_streamer": dados["owner"].get("name"),
                # tem que tratar a data pq ela vem fora do nosso padrao
                "data_publicacao": time.strftime('%Y-%m-%d', time.localtime(dados.get("pubdate"))),
                "views": dados["stat"].get("view"),
                "likes": dados["stat"].get("like"),
                "danmaku": dados["stat"].get("danmaku"), 
                "coins": dados["stat"].get("coin"),
                "shares": dados["stat"].get("share"),
                "favorites": dados["stat"].get("favorite"),
                "comments": dados["stat"].get("reply")
            }
        elif dados.get("code") != 0:
            print(f"Erro na API Bilibili (código {dados.get('code')}): {dados.get('message')}")
            return None
        else:
            print("Estrutura nao é json")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Erro de Conexão: {e}")
        return None

# bvid é tipo o id do video no bilibili
bvid_videos = ["BV1ooXWYiEr2", "BV1ZNBBYBEEn"]
dados_json = []
for bvid in bvid_videos:
    dados = get_bilibili_stats(bvid)
    if dados:
        dados_json.append(dados)

df = pd.DataFrame(dados_json)
df.to_csv(output_file, index=False, encoding='utf-8')