import requests
import csv
from datetime import datetime, timedelta

# --- Configuração ---
GAME_NAME = "Elden Ring"
CATEGORY_NAME = "Any%"
VARIABLE_NAME = "Any% - Subcategories"
VALUE_LABEL = "Glitchless"  # SEU OBJETIVO ORIGINAL
OUTPUT_FILE = "historico_recordes_elden_ring_glitchless_final_garantido.csv"

# --- Funções de API ---

def get_api_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Erro crítico ao acessar a API na URL: {url}")
        raise e

def get_game_id(game_name):
    data = get_api_data(f"https://www.speedrun.com/api/v1/games?name={game_name}")['data']
    if not data: raise ValueError(f"Jogo '{game_name}' não encontrado.")
    return data[0]["id"]

def get_category_id(game_id, category_name):
    data = get_api_data(f"https://www.speedrun.com/api/v1/games/{game_id}/categories")['data']
    for cat in data:
        if cat["name"].lower() == category_name.lower():
            return cat["id"]
    raise ValueError(f"Categoria '{category_name}' não encontrada.")

def get_variable_info(category_id, variable_name, value_label):
    all_vars_data = get_api_data(f"https://www.speedrun.com/api/v1/categories/{category_id}/variables")['data']
    for var in all_vars_data:
        if var["name"].lower() == variable_name.lower():
            variable_id = var["id"]
            for val_id, val_data in var["values"]["values"].items():
                if val_data["label"].lower() == value_label.lower():
                    return variable_id, val_id, val_data["label"] # Retorna também o label para debug
    raise ValueError(f"Variável/Valor não encontrados.")

# --- FUNÇÃO DE BUSCA ALTERADA: BUSCA TUDO E DEIXA O FILTRO PARA DEPOIS ---
def fetch_all_runs_for_category(game_id, category_id):
    all_runs = []
    # Removemos o filtro de variável daqui, buscaremos todas as runs de Any%
    base_url = (f"https://www.speedrun.com/api/v1/runs?game={game_id}&category={category_id}"
                f"&status=verified&obsoleted=true"
                f"&orderby=date&direction=asc&embed=players")
    url = base_url
    print(f"DEBUG: URL de busca de todas as runs: {url}") # Para verificar se a URL está correta
    while url:
        response_data = get_api_data(url)
        runs_page = response_data['data']
        all_runs.extend(runs_page)
        print(f"Processadas {len(all_runs)} runs no total de '{CATEGORY_NAME}'...")
        next_link = [link['uri'] for link in response_data['pagination']['links'] if link['rel'] == 'next']
        url = next_link[0] if next_link else None
    return all_runs

def format_time(seconds):
    if seconds is None: return "N/A"
    delta = timedelta(seconds=float(seconds))
    time_str = str(delta)
    return time_str[:-3] if '.' in time_str else time_str

def analisar_progressao_recorde(runs_ordenadas, target_var_id, target_val_id, target_val_label):
    print("\nAnalisando a progressão histórica dos recordes...")
    historico, melhor_tempo = [], float('inf')
    
    # --- FILTRO LOCAL EXPLICITO ---
    runs_filtradas_localmente = []
    for run in runs_ordenadas:
        run_values = run.get('values', {})
        # Verifica se a run tem a variável e o valor que queremos
        if target_var_id in run_values and run_values[target_var_id] == target_val_id:
            runs_filtradas_localmente.append(run)
    
    print(f"Total de runs baixadas para '{CATEGORY_NAME}': {len(runs_ordenadas)}")
    print(f"Total de runs filtradas localmente para '{target_val_label}': {len(runs_filtradas_localmente)}")
    # -------------------------------

    if not runs_filtradas_localmente:
        print("Nenhuma run encontrada após o filtro local para a sub-categoria desejada.")
        return []

    for run in runs_filtradas_localmente:
        tempo_atual = float(run["times"]["primary_t"])
        if tempo_atual < melhor_tempo:
            melhor_tempo = tempo_atual
            player_name = run["players"]['data'][0].get("name", run["players"]['data'][0]['id'])
            video_link = "N/A"
            if run.get("videos") and run["videos"].get("links"):
                video_link = run["videos"]["links"][0]["uri"]
            historico.append({
                "date": run.get("date", "N/A"),
                "player": player_name,
                "time_seconds": tempo_atual,
                "time_formatted": format_time(tempo_atual),
                "run_link": run["weblink"],
                "video_link": video_link
            })
    print(f"-> Análise concluída. Encontradas {len(historico)} runs que foram recorde mundial para '{target_val_label}'.")
    return historico

def main():
    try:
        print(f"Procurando jogo '{GAME_NAME}'...")
        game_id = get_game_id(GAME_NAME)
        print(f"Procurando categoria '{CATEGORY_NAME}'...")
        category_id = get_category_id(game_id, CATEGORY_NAME)
        print(f"Buscando variável '{VARIABLE_NAME}' com valor '{VALUE_LABEL}'...")
        
        # Retorna o ID da variável, o ID do valor e o LABEL do valor
        variable_id, value_id, value_label_found = get_variable_info(category_id, VARIABLE_NAME, VALUE_LABEL)
        print(f"-> ID da Variável: {variable_id}, ID do Valor: {value_id}, Label encontrado: {value_label_found}")

        print(f"\nBuscando TODO o histórico de runs de '{CATEGORY_NAME}' (sem filtro inicial de sub-categoria)...")
        # Chama a NOVA função que busca tudo para a categoria principal
        todas_as_runs_da_categoria = fetch_all_runs_for_category(game_id, category_id)
        
        if not todas_as_runs_da_categoria:
            print("Nenhuma run encontrada no histórico geral da categoria.")
            return

        print("\nGarantindo a ordem cronológica de todas as runs baixadas...")
        runs_ordenadas_com_data = [r for r in todas_as_runs_da_categoria if r.get('date')]
        runs_ordenadas = sorted(runs_ordenadas_com_data, key=lambda r: r['date'])
        
        # Passa os IDs da variável e do valor para que a análise possa filtrar localmente
        historico = analisar_progressao_recorde(runs_ordenadas, variable_id, value_id, value_label_found)
        
        if not historico:
            print("Não foi possível gerar um histórico de recordes.")
            return

        print(f"\nSalvando o histórico de {len(historico)} recordes em '{OUTPUT_FILE}'...")
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["date", "player", "time_seconds", "time_formatted", "run_link", "video_link"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(historico)
        
        print(f"\n✅ Sucesso! O histórico de recordes foi salvo em '{OUTPUT_FILE}'.")

    except Exception as e:
        print(f"\n❌ Erro: {e}")

if __name__ == "__main__":
    main()