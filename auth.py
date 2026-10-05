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
    try:
        sessionkey = driver.execute_script("""
        return JSON.parse(sessionStorage.getItem('SessionKey'))
        """)

        notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" :: Session key obtida do session storage :: ")

        with open("config_session.json", "w") as f:
            json.dump({"sessionKey": sessionkey}, f)

        notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" :: Sessionkey salva no json ::")

        try:
            driver.quit()
        except:
            pass

        return sessionkey

    except Exception as e:
        notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" :: Erro ao obter session key :: " + str(e))
    finally:
        # deslig_proxy = resource_path("desligar_proxy.bat")
        # subprocess.run(deslig_proxy, shell=True)

        # notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" :: Proxy desligado :: ")

        try:
            driver.quit()
        except:
            pass

def get_session_key(username, password):
    # proxy_active = subprocess.run(resource_path("ligar_proxy.bat"), shell=True)
    # if proxy_active.returncode != 0:
    #     notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" :: Falha ao ligar proxy, verifique o arquivo ligar_proxy.bat :: ")
    #     raise Exception("Falha ao ligar proxy")
    # time.sleep(1)
    notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" :: Obtendo session key :: ")
    options = Options()
    options.add_argument("--start-maximized")
    driver = webdriver.Edge(options=options)
    wait_4m = WebDriverWait(driver, 60)

    driver.get("https://aec.robbyson.com/administracao/#/login/")

    # try:
    #     wait_4m.until(EC.presence_of_element_located((By.XPATH, "/html/body/nav/div/ul/li/a/div[1]"))).click()
    #     notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" :: Usuario logado, gerando session key :: ")
    #     return generate_session_key(driver)
    # except:
    #     pass

    wait_4m.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/form[1]/div/div/div[2]/div[1]/div/div/div/div/div[1]/div[3]/div/div/div/div[2]/div[2]/div/input[1]"))).send_keys(username) # usuario
    notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" :: Usuário preenchido :: ") 
    driver.find_element(By.XPATH, "/html/body/div/form[1]/div/div/div[2]/div[1]/div/div/div/div/div[1]/div[3]/div/div/div/div[4]/div/div/div/div/input").click() # avançar
    wait_4m.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/form[1]/div/div/div[2]/div[1]/div/div/div/div/div/div[3]/div/div[2]/div/div[3]/div/div[2]/input"))).send_keys(password) # senha
    notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" :: Senha preenchida :: ")
    driver.find_element(By.XPATH, "/html/body/div/form[1]/div/div/div[2]/div[1]/div/div/div/div/div/div[3]/div/div[2]/div/div[5]/div/div/div/div/input").click() # avançar
    wait_4m.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/form/div/div/div[2]/div[1]/div/div/div/div/div/div[3]/div/div[2]/div/div[3]/div[2]/div/div/div[2]/input"))).send_keys(Keys.ENTER) # avançar

    wait_4m.until(EC.element_to_be_clickable((By.XPATH, "/html/body/nav/div/ul/li/a/div[1]"))).click() # sessao

    deslig_proxy = resource_path("desligar_proxy.bat")
    proxy_inactive = subprocess.run(deslig_proxy, shell=True)
    if proxy_inactive.returncode != 0:
        notify(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" :: Falha ao desligar proxy, verifique o arquivo ligar_proxy.bat :: ")

    return generate_session_key(driver)