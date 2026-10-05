from connect_db import exec_generator, update_importado_sistema_matriz
from file_manager import generate_files
from api import import_api
from utils import notify
from dotenv import load_dotenv
from telegram_config import notify_telegram
import os

load_dotenv(r"C:\Users\e.gustavo.santos.GRUPO_A&C\Documents\Github\import_api_web_matriz\.env")

def main():
    try:
        importacao, alteracao = exec_generator()
        if importacao or alteracao:
            notify(f"Gerando {len(importacao)+len(alteracao)} linhas para importações no total.")
            generate_files(importacao, alteracao)
        import_api("e.gustavo.santos@aec.com.br", os.getenv("PASSWORD"))
        update_importado_sistema_matriz()
        notify("Processo de importação de matrizes finalizado com sucesso.")
        notify_telegram("Processo de importação de matrizes finalizado com sucesso.")
    except Exception as e:
        notify(f"Erro geral no processo de importação de matrizes: {e}")
        notify_telegram(f"Erro geral no processo de importação de matrizes: {e}")
        raise

if __name__ == "__main__": 
    main()