import requests, json, os, time, re
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import numpy as np
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES ---
output_dir = "../1-coleta"
os.makedirs(output_dir, exist_ok=True)
speedrun_file = os.path.join(output_dir, "speedrun_stats.csv")
final_analysis_file = os.path.join(output_dir, "youtube_full_impact_analysis.csv")

# --- CRIAÇÃO DO CLIENTE DA API ---
try:
    with open("auth.json", "r") as f:
        auth = json.load(f)
    YOUTUBE_API_KEY = auth["YOUTUBE_API_KEY"]
    youtube_client = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    print("Cliente da API do YouTube criado com sucesso!")
except Exception as e:
    print(f"Erro ao criar cliente da API: {e}. Verifique sua chave de API.")
    youtube_client = None

# obter as estatísticas dos videos do youtube
def obter_estatisticas_youtube(video_url, youtube):
    default_return = (None, None, None, None, None, None)
    if not youtube or not isinstance(video_url, str) or ('youtube.com' not in video_url and 'youtu.be' not in video_url):
        return default_return
    video_id_match = re.search(r'(?<=v=)[\w-]+|(?<=be/)[\w-]+', video_url)
    if not video_id_match: return default_return
    video_id = video_id_match.group(0)
    try:
        video_request = youtube.videos().list(part="statistics,snippet", id=video_id)
        video_response = video_request.execute()
        if 'items' in video_response and video_response['items']:
            video_item = video_response['items'][0]
            stats, snippet = video_item['statistics'], video_item['snippet']
            views = int(stats.get('viewCount', 0))
            likes = int(stats.get('likeCount', 0))
            comments = int(stats.get('commentCount', 0))
            published_at = snippet.get('publishedAt')
            channel_id = snippet.get('channelId')
            subscriber_count = 0
            if channel_id:
                channel_req = youtube.channels().list(part="statistics", id=channel_id)
                channel_resp = channel_req.execute()
                if 'items' in channel_resp and channel_resp['items']:
                    subscriber_count = int(channel_resp['items'][0]['statistics'].get('subscriberCount', 0))
            time.sleep(0.2)
            return (views, likes, comments, published_at, channel_id, subscriber_count)
    except Exception as e:
        print(f"  -> Erro em obter_estatisticas_youtube para ID {video_id}: {e}")
    return default_return

# função para analisar o canal antes e depois do recorde
def analisar_impacto_canal(youtube, channel_id, record_date_str, record_video_id):
    """
    Busca vídeos 5 dias antes e 5 dias depois de uma data e agrega suas estatísticas.
    """
    try:
        record_date = datetime.fromisoformat(record_date_str.replace('Z', '+00:00'))
        
        # definindo as janelas de tempo
        data_inicio_antes = (record_date - timedelta(days=5)).strftime('%Y-%m-%dT%H:%M:%SZ')
        data_fim_antes = record_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        data_inicio_depois = record_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        data_fim_depois = (record_date + timedelta(days=5)).strftime('%Y-%m-%dT%H:%M:%SZ')

        periodos = {
            "antes": (data_inicio_antes, data_fim_antes),
            "depois": (data_inicio_depois, data_fim_depois)
        }

        resultados = {
            'Views_5d_Antes': 0, 'Likes_5d_Antes': 0, 'NumVideos_5d_Antes': 0,
            'Views_5d_Depois': 0, 'Likes_5d_Depois': 0, 'NumVideos_5d_Depois': 0
        }

        for periodo, (start_date, end_date) in periodos.items():
            # busca por vídeos no período
            search_request = youtube.search().list(
                part="snippet",
                channelId=channel_id,
                publishedAfter=start_date,
                publishedBefore=end_date,
                type="video",
                maxResults=50 # limite máximo por chamada
            )
            search_response = search_request.execute()
            
            video_ids = []
            for item in search_response.get('items', []):
                video_id = item['id']['videoId']
                # garante que não estamos incluindo o próprio vídeo do recorde na contagem
                if video_id != record_video_id:
                    video_ids.append(video_id)
            
            if not video_ids:
                continue

            # pega as estatísticas dos vídeos encontrados
            stats_request = youtube.videos().list(
                part="statistics",
                id=",".join(video_ids)
            )
            stats_response = stats_request.execute()
            
            total_views = 0
            total_likes = 0
            for item in stats_response.get('items', []):
                total_views += int(item['statistics'].get('viewCount', 0))
                total_likes += int(item['statistics'].get('likeCount', 0))
            
            # salvando os resultados
            if periodo == "antes":
                resultados['Views_5d_Antes'] = total_views
                resultados['Likes_5d_Antes'] = total_likes
                resultados['NumVideos_5d_Antes'] = len(video_ids)
            else: 
                resultados['Views_5d_Depois'] = total_views
                resultados['Likes_5d_Depois'] = total_likes
                resultados['NumVideos_5d_Depois'] = len(video_ids)
        
        time.sleep(0.5) # pausa para não sobrecarregar a API
        return resultados

    except Exception as e:
        print(f"  -> Erro ao analisar impacto do canal {channel_id}: {e}")
        return None


def main():
    if not youtube_client:
        print("Finalizando, cliente da API do YouTube não inicializado.")
        return

    if not os.path.exists(speedrun_file):
        print(f"Erro: Arquivo de entrada '{speedrun_file}' não encontrado.")
        return

    df = pd.read_csv(speedrun_file)
    
    # lista para armazenar os resultados de cada linha
    all_results = []

    print(f"Iniciando análise completa para {len(df)} runs. Isso pode demorar MUITO tempo...")

    for index, row in df.iterrows():
        print(f"\nProcessando run {index + 1}/{len(df)} - Runner: {row['player']}")
        
        # dicionário para guardar todos os dados desta run
        current_run_data = row.to_dict()

        # etapa 1: Obter estatísticas do vídeo do recorde
        video_url = row['video_link']
        (views, likes, comments, published_at, channel_id, subscribers) = obter_estatisticas_youtube(video_url, youtube_client)
        
        current_run_data.update({
            'Views': views, 'Likes': likes, 'Comments': comments,
            'PublishedAt': published_at, 'ChannelID': channel_id, 'CurrentSubscribers': subscribers
        })

        # etapa 2: Se a Etapa 1 funcionou, fazer a análise de antes/depois
        if channel_id and published_at:
            video_id_match = re.search(r'(?<=v=)[\w-]+|(?<=be/)[\w-]+', video_url)
            record_video_id = video_id_match.group(0) if video_id_match else None
            
            print(f"  -> Analisando impacto no canal {channel_id}...")
            impacto_canal = analisar_impacto_canal(youtube_client, channel_id, published_at, record_video_id)
            if impacto_canal:
                current_run_data.update(impacto_canal)
        
        all_results.append(current_run_data)

    # cria o DataFrame final com todos os dados coletados
    df_final = pd.DataFrame(all_results)
    
    # calcular as métricas de Nível 1 (ViewsPerDay, etc.)
    print("\nCalculando métricas de performance do vídeo...")
    df_final.dropna(subset=['Views', 'PublishedAt'], inplace=True)
    
    df_final['PublishedAtDT'] = pd.to_datetime(df_final['PublishedAt'])
    today_utc = pd.Timestamp.now(tz='UTC')
    df_final['VideoAgeDays'] = (today_utc - df_final['PublishedAtDT']).dt.days
    df_final['VideoAgeDays'] = df_final['VideoAgeDays'].apply(lambda x: 1 if x < 1 else x)
    df_final['ViewsPerDay'] = df_final['Views'] / df_final['VideoAgeDays']
    
    total_engagement = df_final['Likes'].fillna(0) + df_final['Comments'].fillna(0)
    df_final['EngagementRate'] = np.divide(total_engagement, df_final['Views'], out=np.zeros_like(total_engagement, dtype=float), where=df_final['Views']!=0) * 100

    # salvando o resultado final completo
    df_final.to_csv(final_analysis_file, index=False, encoding='utf-8')
    print(f"\nANÁLISE COMPLETA FINALIZADA! Resultados salvos em '{final_analysis_file}'")
    
    # exibe as colunas mais relevantes
    display_cols = [
        'player', 'ViewsPerDay', 'Views_5d_Antes', 'Views_5d_Depois',
        'NumVideos_5d_Antes', 'NumVideos_5d_Depois', 'CurrentSubscribers'
    ]
    # filtra colunas que existem no dataframe para evitar erros
    display_cols_exist = [col for col in display_cols if col in df_final.columns]
    print("\n--- Visualização do Resultado Final ---")
    print(df_final.sort_values(by='ViewsPerDay', ascending=False)[display_cols_exist].head(10).to_string(index=False))

if __name__ == "__main__":
    main()