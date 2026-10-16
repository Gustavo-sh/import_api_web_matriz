from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options
import subprocess
from utils import resource_path, notify
from datetime import datetime
import json
import time


def generate_session_key(driver):
    
    sessionkey = driver.execute_script("""return JSON.parse(sessionStorage.getItem('SessionKey'))""")

    if not sessionkey:
        raise Exception("Session key não encontrada no session storage")

    notify(":: Session key obtida do session storage ::")

    with open("config_session.json", "w") as f:
        json.dump({"sessionKey": sessionkey}, f)

    notify(":: Sessionkey salva no json ::")

    return sessionkey

def get_session_key(username, password):

    notify(":: Obtendo session key ::")

    options = Options()
    options.add_argument("--start-maximized")
    driver = None

    try:
        driver = webdriver.Edge(options=options)
        wait = WebDriverWait(driver, 600)

        driver.get("https://aec.robbyson.com/administracao/#/login/")

        wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/form[1]/div/div/div[2]/div[1]/div/div/div/div/div[1]/div[3]/div/div/div/div[2]/div[2]/div/input[1]"))).send_keys(username) # usuario
        notify(":: Usuário preenchido :: ") 
        driver.find_element(By.XPATH, "/html/body/div/form[1]/div/div/div[2]/div[1]/div/div/div/div/div[1]/div[3]/div/div/div/div[4]/div/div/div/div/input").click() # avançar
        wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/form[1]/div/div/div[2]/div[1]/div/div/div/div/div/div[3]/div/div[2]/div/div[3]/div/div[2]/input"))).send_keys(password) # senha
        notify(":: Senha preenchida :: ")
        driver.find_element(By.XPATH, "/html/body/div/form[1]/div/div/div[2]/div[1]/div/div/div/div/div/div[3]/div/div[2]/div/div[5]/div/div/div/div/input").click() # avançar
        wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/form/div/div/div[2]/div[1]/div/div/div/div/div/div[3]/div/div[2]/div/div[3]/div[2]/div/div/div[2]/input"))).send_keys(Keys.ENTER) # avançar

        wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/nav/div/ul/li/a/div[1]"))).click() # sessao

        return generate_session_key(driver)

    finally:
        if driver is not None:
            try:
                driver.quit()
                notify(":: Edge encerrado ::")
            except Exception as e:
                notify(f":: Erro ao encerrar Edge: {e} ::")