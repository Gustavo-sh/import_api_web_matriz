import requests
from auth import get_session_key
from datetime import datetime
from utils import notify, resource_path, write_log
import time
import subprocess
import pandas as pd
import json 
from pathlib import Path
import shutil

def search_attribute(session, token, mes_ano, atributo):

    headers_get = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'origin': 'https://app.robbyson.com',
        'priority': 'u=1, i',
        'referer': 'https://app.robbyson.com/',
        'sec-ch-ua': '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'sessionkey': token,
        'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36',
        'x-system-id': '2',
    }

    params = {
        'active': 'true',
        'keyWord': mes_ano,
        'page': '1',
        'per': '42',
        'searchAttributesValueDescription': atributo,
    }

    response_get = session.get('https://api.robbyson.com/goal/adminList', params=params, headers=headers_get, timeout=60)

    notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " :: " + str(response_get.status_code) + " - Get do disable ::")
    write_log(response_get.text)
    notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+f" :: Descrição enviada neste get do disable: {mes_ano}, atributo: {atributo} ::")

    if response_get.status_code != 200:
        raise Exception(response_get.text)

    data = response_get.json()

    return data

def disable_attribute(session, token, mes_ano, atributo):

    for _ in range(3):

        data = search_attribute(session, token, mes_ano, atributo)
        
        items = data["data"]["items"]

        if not items:
            notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+f" :: Pulando o atributo {atributo} com descrição {mes_ano}, pois não encontrou nenhum item :: ")
            return None

        ids = [item["_id"] for item in items]

        notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" :: IDs encontrados: " + ", ".join(ids) + " :: ")

        headers_post = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'content-type': 'application/json;charset=UTF-8',
            'origin': 'https://app.robbyson.com',
            'priority': 'u=1, i',
            'referer': 'https://app.robbyson.com/',
            'sec-ch-ua': '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'sessionkey': token,
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36',
            'x-system-id': '2',
        }

        response_disable = session.post('https://api.robbyson.com/goal/disableMany', headers=headers_post, json={
                "_ids": ids
            }, timeout=60
        )

        notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " :: " + str(response_disable.status_code) + " - Post do disable ::")
        write_log(response_disable.text)

        if response_disable.status_code != 200:
            raise Exception(response_disable.text)

        time.sleep(1)

    return response_disable.json()

def process_pending_files(session, base_url, token, files):

    processed_dir = Path(__file__).resolve().parent / "processados"
    processed_dir.mkdir(parents=True, exist_ok=True)

    notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + f" :: {len(files)} arquivo(s) pendente(s) encontrado(s) ::")

    for file_path in files:

        notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+ f" :: Iniciando processamento: {file_path.name} ::")

        try:
            import_file(session,base_url,file_path,token)
            destination = processed_dir / file_path.name
            shutil.move(str(file_path),str(destination))
            notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + f" :: Arquivo processado com sucesso: {file_path.name} ::")

        except Exception as e:
            notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + f" :: Erro ao processar {file_path.name}: {e} ::")
            raise
        
def import_file(session, base_url, file_path, token):

    if "alteracao" in file_path.name.lower():
        df = pd.read_excel(file_path, sheet_name="Plan1")
        mes_ano = datetime.now().strftime("%m/%Y")
        atributos = df["ATRIBUTOS"].drop_duplicates().tolist()
        notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+f" :: Desativando os seguintes atributos: {len(atributos)} atributos em 10 segundos:\n{atributos} ::")
        time.sleep(10)
        for atributo in atributos:
            disable_attribute(session, token, mes_ano, atributo)

    ### PASSO 1

    with open(file_path, "rb") as f:

        files = {
            "file": f
        }

        response = session.post(
            f"{base_url}/goal/import",
            files=files,
            timeout=60
        )

    if response.status_code != 200:
        notify("\n" + str(response.status_code) + " - " + response.text)
        raise Exception("Erro no import")

    notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+f" :: Import (passo 1) realizado com sucesso - status code: {response.status_code} ::")
    write_log("\n:: text do import ::\n" + response.text)

    data = response.json()

    cache_id = data["data"]["_id"]

    ### PASSO 2

    payload = {
        "goalImportingCache_id": cache_id,
        "timezone": 180
    }

    time.sleep(2)

    response_save = session.put(
        f"{base_url}/goal/save-importing-cache",
        json=payload,
        timeout=60
    )

    if response_save.status_code != 200:
        notify("\n" + str(response_save.status_code) + " - " + response_save.text)
        raise Exception("Erro ao salvar")

    notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+f" :: Save importing cache (passo 2) realizado com sucesso - status code: {response_save.status_code} ::")
    write_log("\n:: text do save importing cache ::\n" + response_save.text)

    ### PASSO 3

    trys = 0

    while True:

        response_get = session.get(
            f"{base_url}/goal/importingCache",
            params={
                "goalImportingCache_id": cache_id
            },
            timeout=60
        )

        if response_get.status_code != 200:
            raise Exception(f"Erro no passo 3 (get importing cache): {response_get.status_code}")

        data = response_get.json()

        status = data["data"]["status"]

        notify(f"Tentativa {trys + 1} - status: {status}")

        if status.lower() == "done":
            notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" :: Processamento concluído ::")
            break
        elif status.lower() == "error":
            
            notify(data["data"]["processingErrors"])
            
            raise Exception("Erro no processamento \n")

        trys += 1
        time.sleep(2)
        

    ### PASSO 4

    time.sleep(2)

    response_delete = session.delete(
        f"{base_url}/goal/importingCache",
        params={
            "goalImportingCache_id": cache_id
        },
        timeout=60
    )

    if response_delete.status_code != 200:
        notify("\n" + str(response_delete.status_code) + " - " + response_delete.text)
        raise Exception("Erro ao deletar cache")

    notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+f" :: Delete importing cache (passo 4) realizado com sucesso - status code: {response_delete.status_code} ::")
    write_log("\n:: text do delete importing cache ::\n" + response_delete.text)

    notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" :: Envio Robbyson encerrado :: ")

def import_api(username, password):
    try:
        pending_dir = Path(__file__).resolve().parent / "pendentes"
    
        pending_dir.mkdir(parents=True, exist_ok=True)
    
        files = sorted(pending_dir.glob("*.xls"),key=lambda file: file.name)
    
        if not files:
            notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " :: Nenhum arquivo pendente encontrado ::")
            return

        BASE_URL = "https://api.robbyson.com"
        
        notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" :: Automacao rodando, aguarde... :: ")

        TOKEN = None
        
        session = requests.Session()

        with open("config_session.json", "a+") as f:
            f.seek(0)
            try:
                dados = json.load(f)
            except:
                dados = {}
            TOKEN = dados.get("sessionKey", "")

        if not TOKEN:
            TOKEN = get_session_key(username, password)

        try:
            search_attribute(session, TOKEN, '06/2026', 'TEST ATTRIBUTE') # to validate the session token
            notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" :: Token obtido do json validado com sucesso ::")
            
        except Exception as e:
            if 'token' in str(e).lower() or 'session' in str(e).lower():
                notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" :: Token do json expirado, obtendo um novo token :: ")
                write_log("\n:: erro_token ::\n" + str(e))
                for i in range(3):
                    notify(f"Iniciando tentativa {i+1}/3 de obter a session key")
                    try:
                        TOKEN = get_session_key(username, password)
                        break
                    except Exception:
                        if i == 2:
                            raise
                        continue
            else:
                raise

        headers = {
            'accept': 'application/json, text/plain, */*',
            'origin': 'https://app.robbyson.com',
            'referer': 'https://app.robbyson.com/',
            'sessionkey': TOKEN,
            'timezoneoffset': '180',
            'user-agent': 'Mozilla/5.0',
            'x-system-id': '2'
        }

        session.headers.update(headers)

        process_pending_files(session, BASE_URL, TOKEN, files)

    except Exception as e:
        notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" :: Erro na import api: " + str(e) + " :: ")
        raise