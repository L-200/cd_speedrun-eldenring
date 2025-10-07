import requests
import csv
from datetime import datetime, timedelta
from pathlib import Path

# --- Configuração ---
GAME_NAME = "Elden Ring"
CATEGORY_NAME = "Any%" 
VARIABLE_NAME = "Any% - Subcategories" # nome da variável que define a sub-categoria
VALUE_LABEL = "Glitchless" # valor específico da variável para filtrar

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = SCRIPT_DIR.parent / "1-coleta" / "speedrun_stats.csv"

def get_api_data(url): # função que se comunica com o site
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Erro crítico ao acessar a API na URL: {url}")
        raise e

def get_game_id(game_name): # pega a id do game baseado em seu nome
    data = get_api_data(f"https://www.speedrun.com/api/v1/games?name={game_name}")['data']
    if not data: raise ValueError(f"Jogo '{game_name}' não encontrado.")
    return data[0]["id"]

def get_category_id(game_id, category_name): # usando o game_id, pega o id da categoria
    data = get_api_data(f"https://www.speedrun.com/api/v1/games/{game_id}/categories")['data']
    for cat in data:
        if cat["name"].lower() == category_name.lower():
            return cat["id"]
    raise ValueError(f"Categoria '{category_name}' não encontrada.")

def get_variable_info(category_id, variable_name, value_label): # pega o id da variável subcategories e do valor específico para glitchless
    all_vars_data = get_api_data(f"https://www.speedrun.com/api/v1/categories/{category_id}/variables")['data']
    for var in all_vars_data:
        if var["name"].lower() == variable_name.lower():
            variable_id = var["id"]
            for val_id, val_data in var["values"]["values"].items():
                if val_data["label"].lower() == value_label.lower():
                    return variable_id, val_id, val_data["label"]
    raise ValueError(f"Variável/Valor não encontrados.")

def fetch_all_runs_for_category(game_id, category_id):
    all_runs = []
    base_url = (f"https://www.speedrun.com/api/v1/runs?game={game_id}&category={category_id}"
                f"&status=verified&obsoleted=true" #runs verificadas e obsoletas para pegar o histórico completo
                f"&orderby=date&direction=asc&embed=players")
    url = base_url
    while url:
        response_data = get_api_data(url)
        runs_page = response_data['data']
        all_runs.extend(runs_page)
        # Removido o print de progresso para uma saída mais limpa
        next_link = [link['uri'] for link in response_data['pagination']['links'] if link['rel'] == 'next']
        url = next_link[0] if next_link else None
    print(f"Total de {len(all_runs)} runs da categoria principal foram baixadas.")
    return all_runs

def format_time(seconds):
    if seconds is None: return "N/A"
    delta = timedelta(seconds=float(seconds))
    time_str = str(delta)
    return time_str[:-3] if '.' in time_str else time_str

def analisar_progressao_recorde(runs_ordenadas, target_var_id, target_val_id, target_val_label): #filtra as runs pela sub-categoria desejada e analisa a progressão de recordes na categoria
    historico, melhor_tempo = [], float('inf')
    
    runs_filtradas_localmente = [
        run for run in runs_ordenadas
        if target_var_id in run.get('values', {}) and run['values'][target_var_id] == target_val_id
    ]
    
    print(f"Filtrando: {len(runs_filtradas_localmente)} runs encontradas para '{target_val_label}'.")

    if not runs_filtradas_localmente:
        print("Nenhuma run encontrada após o filtro local para a sub-categoria desejada.")
        return []

    for run in runs_filtradas_localmente:
        tempo_atual = float(run["times"]["primary_t"])
        if tempo_atual < melhor_tempo:
            melhor_tempo = tempo_atual
            player_name = run["players"]['data'][0].get("name", run["players"]['data'][0]['id'])
            video_link = run.get("videos", {}).get("links", [{}])[0].get("uri", "N/A")
            historico.append({
                "date": run.get("date", "N/A"),
                "player": player_name,
                "time_seconds": tempo_atual,
                "time_formatted": format_time(tempo_atual),
                "run_link": run["weblink"],
                "video_link": video_link
            })
    print(f"Análise concluída. Encontrados {len(historico)} recordes mundiais.")
    return historico

def main():
    try:
        print(f"Procurando jogo '{GAME_NAME}'...")
        game_id = get_game_id(GAME_NAME)
        print(f"Procurando categoria '{CATEGORY_NAME}'...")
       
        category_id = get_category_id(game_id, CATEGORY_NAME)
        print(f"Buscando variável '{VARIABLE_NAME}' com valor '{VALUE_LABEL}'...")
        
        variable_id, value_id, value_label_found = get_variable_info(category_id, VARIABLE_NAME, VALUE_LABEL)
        print(f"-> IDs encontrados. Iniciando busca de runs...")

        todas_as_runs_da_categoria = fetch_all_runs_for_category(game_id, category_id)
        
        if not todas_as_runs_da_categoria:
            print("Nenhuma run encontrada no histórico geral da categoria.")
            return

        runs_ordenadas = sorted([r for r in todas_as_runs_da_categoria if r.get('date')], key=lambda r: r['date'])
        
        historico = analisar_progressao_recorde(runs_ordenadas, variable_id, value_id, value_label_found)
        
        if not historico:
            print("Não foi possível gerar um histórico de recordes.")
            return

        print(f"Salvando o histórico de {len(historico)} recordes em '{OUTPUT_FILE}'...")
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["date", "player", "time_seconds", "time_formatted", "run_link", "video_link"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(historico)
        
        print(f"\nSUCESSO: O histórico de recordes foi salvo em '{OUTPUT_FILE}'.")

    except Exception as e:
        print(f"\nERRO: {e}")

if __name__ == "__main__":
    main()