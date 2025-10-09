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
    
def get_bilibili_stats(bvid_video, contexto):
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
            criador = dados["owner"].get("mid")
            link = f"https://space.bilibili.com/{criador}"
            # como tem muito dado e o json é imenso, retorna so alguns, podemos mudar dps
            return {
                "bvid": dados.get("bvid"),
                "context_video": contexto,
                "title": dados.get("title"),
                "name_streamer": dados["owner"].get("name"),
                "link_channel": link,
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

def main():
    """
    Define os BVIDs, mapeia o contexto (recorde/antes/depois), coleta os dados
    e salva o resultado em um arquivo CSV.
    """
    # bvid é tipo o id do video no bilibili
    bvid_videos_record = ["BV1ooXWYiEr2", "BV1ZNBBYBEEn"]
    # videos base antes-depois de BV1ZNBBYBEEn
    bvid_videos_antes_BEEn = ["BV1V9DxY8EEM","BV1Sr1tYmE6i"]
    bvid_videos_depois_BEEn = ["BV1NTi1YYE8D","BV1cLqkYWEdH"]
    # videos base antes-depois de BV1ooXWYiEr2
    bvid_videos_antes_iEr2 = ["BV1bw9wYZEkG", "BV1YAP4ehEie"]
    bvid_videos_depois_iEr2 = ["BV17ufPY8ERN", "BV18z5bzJEsH"]

    bvid_contexto = {}

    # define o contexto de acordo com o bvid
    for bvid in bvid_videos_record:
        bvid_contexto[bvid] = "recorde"

    for bvid in bvid_videos_antes_BEEn + bvid_videos_antes_iEr2:
        bvid_contexto[bvid] = "antes_recorde"

    for bvid in bvid_videos_depois_BEEn + bvid_videos_depois_iEr2:
        bvid_contexto[bvid] = "depois_recorde"

    todos_bvid = list(bvid_contexto)
    dados_json = []

    # faz as coletas dos dados
    for bvid in todos_bvid:
        contexto = bvid_contexto[bvid]
        dados = get_bilibili_stats(bvid, contexto)
        if dados:
            dados_json.append(dados)
        time.sleep(1)

    # salva no csv e termina
    if dados_json:
        df = pd.DataFrame(dados_json)
        df.to_csv(output_file, index=False, encoding='utf-8')

# se chamar direto pelo script.py executa como main
if __name__ == "__main__":
    main()