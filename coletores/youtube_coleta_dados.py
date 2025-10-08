# coleta_dados.py

import requests, json, os, time, re
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configuração de saída
output_dir = "../1-coleta"
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, "youtube_stats.csv")
speedrun_file = "../1-coleta/speedrun_stats.csv"

# carrega credenciais
with open("auth.json", "r") as f:
    auth = json.load(f)
YOUTUBE_API_KEY = auth["YOUTUBE_API_KEY"]
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

try:
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=YOUTUBE_API_KEY)
    print("Cliente da API do YouTube criado com sucesso!")
except Exception as e:
    print(f"Erro ao criar cliente da API: {e}. Verifique sua chave de API.")

def obter_estatisticas_youtube(video_url, api_key=YOUTUBE_API_KEY):
    """Busca estatísticas de um vídeo do YouTube usando a API."""
    if 'youtube.com' not in video_url and 'youtu.be' not in video_url:
        return None, None, None

    video_id_match = re.search(r'(?<=v=)[\w-]+|(?<=be/)[\w-]+', video_url)
    if not video_id_match:
        return None, None, None
    
    video_id = video_id_match.group(0)
    
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.videos().list(part="statistics", id=video_id)
        response = request.execute()

        if 'items' in response and response['items']:
            stats = response['items'][0]['statistics']
            print(stats)
            return (
                int(stats.get('viewCount', 0)),
                int(stats.get('likeCount', 0)),
                int(stats.get('commentCount', 0))
            )
        time.slee(0.5)  # Respeita limites de taxa
    except Exception as e:
        print(f"  -> Erro ao processar vídeo ID {video_id}: {e}")
    
    return None, None, None

def main():
    """Função principal"""
    print("Buscando dados no YouTube para cada run (isso pode levar um tempo)...")

    df = pd.read_csv(speedrun_file)
    df['Video_URL'] = df['video_link'].fillna('')
    links_youtube = set()

    for index, row in df.iterrows():
        if "youtube" in row['Video_URL'] or "youtu.be" in row['Video_URL']:
            links_youtube.add(row["Video_URL"])
    for links in links_youtube:
        print(f"  -> {links}")
    print(f"{len(links_youtube)} Links encontrados do CSV")
    
    youtube_stats = df['Video_URL'].apply(lambda url: pd.Series(obter_estatisticas_youtube(links_youtube)))
    youtube_stats.columns = ['Views', 'Likes', 'Comments']
    
    df_final = youtube_stats

    print("Dados enriquecidos com sucesso.")
   
    df_final.to_csv(output_file, index=False, encoding='utf-8')
    
    print(f"Processo finalizado! Os dados foram salvos em '{output_file}'")
    print("Visualização das 5 primeiras linhas do resultado final:")
    print(df_final.head())

# Executa a função principal quando o script é chamado
if __name__ == "__main__":
    main()