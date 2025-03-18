"""
Script para verificação automática de backlinks e disponibilidade de domínios
"""

import asyncio
import os
import json
import requests
import subprocess
import sys
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from config import *
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from datetime import datetime, timedelta

# Se modificar esses escopos, delete o arquivo token.json
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Configurações
HEADLESS = True  # Alterado para True para rodar sem interface gráfica
DELAY_BETWEEN_REQUESTS = 5  # segundos
MAX_RETRIES = 3
TIMEOUT = 60000  # 60 segundos

async def save_storage_state(context):
    """Salva o estado da sessão"""
    print("\nSalvando estado da sessão...")
    await context.storage_state(path="auth.json")
    print("Estado da sessão salvo!")

async def load_storage_state(context):
    """Carrega o estado da sessão"""
    try:
        if os.path.exists("auth.json"):
            print("\nCarregando estado da sessão...")
            await context.storage_state(path="auth.json")
            print("Estado da sessão carregado!")
            return True
    except Exception as e:
        print(f"Erro ao carregar estado da sessão: {str(e)}")
    return False

async def check_login_status(page):
    """Verifica se ainda está logado"""
    try:
        await page.goto(SEOPACK_DASHBOARD_URL, timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=60000)
        
        # Verifica se está na página de login
        current_url = page.url
        if "login" in current_url.lower():
            print("Sessão expirada, necessário fazer login novamente")
            return False
            
        print("Sessão ainda ativa!")
        return True
        
    except Exception as e:
        print(f"Erro ao verificar status do login: {str(e)}")
        return False

async def login_seopack(page):
    """Faz login no SEOPack"""
    try:
        print("\n=== Iniciando processo de login ===")
        print("Acessando página de login...")
        await page.goto(SEOPACK_LOGIN_URL, timeout=60000)
        print("Página carregada, aguardando elementos...")
        
        # Aguarda a página carregar completamente
        await page.wait_for_load_state('networkidle', timeout=60000)
        await page.wait_for_timeout(3000)  # Espera 3 segundos
        
        # Preenche usuário
        print("Preenchendo usuário...")
        await page.fill('input[name="usuario"]', SEOPACK_LOGIN)
        await page.wait_for_timeout(1000)  # Espera 1 segundo
        
        # Preenche senha
        print("Preenchendo senha...")
        await page.fill('input[type="password"]', SEOPACK_PASSWORD)
        await page.wait_for_timeout(1000)  # Espera 1 segundo
        
        # Clica no botão de login
        print("Clicando no botão de login...")
        await page.click('button.btn.btn-block.btn-primary.mb-4.rounded')
        
        # Aguarda o login completar
        print("Aguardando login completar...")
        await page.wait_for_load_state('networkidle', timeout=60000)
        await page.wait_for_timeout(3000)  # Espera 3 segundos
        
        # Verifica se o login foi bem sucedido
        current_url = page.url
        print(f"URL atual após login: {current_url}")
        
        if "login" in current_url.lower():
            print("ERRO: Login falhou - ainda na página de login")
            raise Exception("Falha no login - redirecionamento incorreto")
            
        print("Login realizado com sucesso!")
        
    except Exception as e:
        print(f"\nERRO no login: {str(e)}")
        try:
            current_url = page.url
            print("URL atual:", current_url)
            
            # Tenta capturar screenshot do erro
            await page.screenshot(path="debug/login_error.png")
            print("Screenshot do erro salvo em debug/login_error.png")
        except:
            print("Não foi possível obter informações adicionais do erro")
        raise

async def access_semrush(page):
    """Acessa o SEMrush através do SEOPack"""
    try:
        print("\n=== Acessando SEMrush ===")
        print("Navegando para o dashboard do SEMrush...")
        await page.goto(SEOPACK_DASHBOARD_URL, timeout=60000)
        await page.wait_for_load_state('networkidle', timeout=60000)
        await page.wait_for_timeout(5000)  # Espera 5 segundos
        
        print("Clicando no botão ACESS SEMRUSH 01...")
        
        # Espera por uma nova aba ser aberta quando clicar no botão
        async with page.context.expect_page() as new_page_info:
            await page.click('text=ACESS SEMRUSH 01', timeout=60000)
            popup = await new_page_info.value
            
        # Fecha a nova aba
        await popup.close()
        
        print("SEMrush acessado com sucesso!")
        
    except Exception as e:
        print(f"\nERRO ao acessar SEMrush: {str(e)}")
        try:
            current_url = page.url
            print("URL atual:", current_url)
            await page.screenshot(path="debug/semrush_error.png")
            print("Screenshot do erro salvo em debug/semrush_error.png")
        except:
            print("Não foi possível obter informações adicionais do erro")
        raise

async def upload_to_drive(file_path):
    """Faz upload do arquivo para o Google Drive usando gdown"""
    try:
        print("\n=== Fazendo upload para o Google Drive ===")
        
        # Verifica se o arquivo existe
        if not os.path.exists(file_path):
            print(f"ERRO: Arquivo {file_path} não encontrado!")
            return False
            
        print(f"Arquivo encontrado: {file_path}")
        print(f"Tamanho: {os.path.getsize(file_path)} bytes")
        
        # Instala gdown se necessário
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "gdown"])
        except:
            print("Erro ao instalar gdown, tentando continuar...")
        
        # ID da pasta pública
        FOLDER_ID = "18YfwC0NOI5vhB3ih-1mAdh8QfBR0luGf"
        
        # Prepara o nome do arquivo com timestamp
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"backlinks_{now}.xlsx"
        
        print(f"Iniciando upload do arquivo {file_name}...")
        
        # Usa gdown para fazer o upload
        try:
            import gdown
            url = f"https://drive.google.com/drive/folders/{FOLDER_ID}"
            gdown.upload(file_path, url, fuzzy=True)
            print("Upload concluído com sucesso!")
            return True
        except Exception as e:
            print(f"Erro ao usar gdown: {str(e)}")
            print("Tentando método alternativo...")
            
            # Tenta método alternativo usando curl
            try:
                curl_cmd = f'curl -X POST -L -F "file=@{file_path}" "https://drive.google.com/drive/folders/{FOLDER_ID}?usp=sharing"'
                result = subprocess.run(curl_cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print("Upload concluído com sucesso (método alternativo)!")
                    return True
                else:
                    print(f"Erro no upload alternativo: {result.stderr}")
                    return False
            except Exception as e2:
                print(f"Erro no método alternativo: {str(e2)}")
                return False
            
    except Exception as e:
        print(f"\nERRO ao fazer upload para o Drive: {str(e)}")
        print("Detalhes do erro:", str(e.__class__.__name__))
        raise

async def download_backlinks_excel(page, domain):
    """Faz o download do arquivo Excel de backlinks"""
    try:
        print("\n=== Baixando arquivo Excel de backlinks ===")
        
        # Clica no botão Export
        print("Clicando no botão Export...")
        export_button = await page.wait_for_selector('span[data-ui-name="Button.Text"]:text("Export"):not(:has-text("PDF"))', timeout=60000)
        if not export_button:
            raise Exception("Botão Export não encontrado")
        await export_button.click()
        await page.wait_for_timeout(2000)
        
        # Clica na opção Excel
        print("Selecionando formato Excel...")
        excel_option = await page.wait_for_selector('div[data-ui-name="DropdownMenu.Item"][data-test-export-type="xls"]', timeout=60000)
        if not excel_option:
            raise Exception("Opção Excel não encontrada")
        await excel_option.click()
        
        # Espera o download começar e terminar
        print("Aguardando download...")
        async with page.expect_download() as download_info:
            await page.wait_for_timeout(5000)  # Espera o download iniciar
            download = await download_info.value
            
            # Cria pasta Google Drive se não existir
            drive_folder = "Google Drive"
            if not os.path.exists(drive_folder):
                os.makedirs(drive_folder)
                print(f"Pasta {drive_folder} criada")
            
            # Salva o arquivo na pasta Google Drive com timestamp e nome do domínio
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"backlinks_{domain}_{now}.xlsx"
            file_path = os.path.join(drive_folder, file_name)
            
            await download.save_as(file_path)
            print(f"Download concluído: {file_path}")
            
            return file_path
            
    except Exception as e:
        print(f"\nERRO ao baixar Excel: {str(e)}")
        await page.screenshot(path="debug/download_error.png")
        print("Screenshot do erro salvo em debug/download_error.png")
        raise

async def upload_to_cleaner(page, excel_file):
    """Faz upload do arquivo Excel para o limpador de domínios"""
    try:
        print("\n=== Fazendo upload para o limpador de domínios ===")
        
        # Acessa a página do limpador
        print("Acessando página do limpador...")
        await page.goto("https://limpar-dominio.vercel.app/", timeout=60000)
        await page.wait_for_load_state('networkidle')
        
        # Faz upload do arquivo
        print("Fazendo upload do arquivo...")
        input_file = await page.wait_for_selector('input[type="file"]')
        await input_file.set_input_files(excel_file)
        
        # Aguarda um tempo para o processamento
        print("Aguardando processamento...")
        await page.wait_for_timeout(10000)  # Espera 10 segundos
        
        print("Upload concluído!")
        
    except Exception as e:
        print(f"\nERRO ao fazer upload: {str(e)}")
        await page.screenshot(path="debug/cleaner_error.png")
        print("Screenshot do erro salvo em debug/cleaner_error.png")
        raise

async def upload_to_verifier(page, excel_file):
    """Faz upload do arquivo Excel para o verificador de domínios e espera o processamento"""
    try:
        print("\n=== Fazendo upload para o verificador de domínios ===")
        
        # Acessa a página do verificador
        print("Acessando página do verificador...")
        await page.goto("https://verificador-dominios-v4.vercel.app/", timeout=60000)
        await page.wait_for_load_state('networkidle')
        
        # Faz upload do arquivo
        print("Fazendo upload do arquivo...")
        input_file = await page.wait_for_selector('input[type="file"]')
        await input_file.set_input_files(excel_file)
        
        # Aguarda o processamento inicial
        print("Aguardando processamento inicial...")
        await page.wait_for_timeout(5000)
        
        # Espera pelo texto de processamento concluído
        print("Aguardando conclusão do processamento...")
        await page.wait_for_selector('text=Processamento concluído!', timeout=300000)
        print("Processamento concluído detectado!")
        
        # Aguarda mais alguns segundos para garantir que o link está clicável
        await page.wait_for_timeout(2000)
        
        # Procura pelo link de download
        print("Procurando link de download...")
        download_link = await page.wait_for_selector('a.download-button', timeout=30000)
        
        if download_link:
            print("Link de download encontrado, baixando arquivo...")
            
            # Clica e espera o download
            async with page.expect_download() as download_info:
                await download_link.click()
                download = await download_info.value
                
                # Salva o arquivo processado
                processed_file = "dominios_verificados.xlsx"
                await download.save_as(processed_file)
                print(f"Arquivo processado salvo como: {processed_file}")
                
                return processed_file
        else:
            print("Link de download não encontrado!")
            await page.screenshot(path="debug/no_download_link.png")
            return None
            
    except Exception as e:
        print(f"\nERRO ao fazer upload: {str(e)}")
        await page.screenshot(path="debug/verifier_error.png")
        print("Screenshot do erro salvo em debug/verifier_error.png")
        raise

async def get_backlinks(page, domain):
    """Verifica backlinks para um domínio específico"""
    try:
        print(f"\n=== Verificando backlinks para {domain} ===")
        
        # Acessa a página de backlinks
        print("Acessando página de backlinks...")
        for attempt in range(MAX_RETRIES):
            try:
                print(f"Tentativa {attempt + 1} de {MAX_RETRIES}...")
                await page.goto(f"https://smr.seopacktools.com/analytics/backlinks/backlinks/?q={domain}&searchType=domain", timeout=TIMEOUT)
                await page.wait_for_load_state("networkidle")
                print("Página carregada com sucesso!")
                break
            except Exception as e:
                print(f"Erro ao carregar página: {str(e)}")
                if attempt == MAX_RETRIES - 1:
                    raise
                await page.wait_for_timeout(5000)
        
        # Clica na aba Backlinks
        print("Clicando na aba Backlinks...")
        backlinks_tab = await page.wait_for_selector('a[data-test="backlinks-tab"]', timeout=TIMEOUT)
        if not backlinks_tab:
            raise Exception("Aba Backlinks não encontrada")
        await backlinks_tab.click()
        await page.wait_for_timeout(5000)
        
        # Baixa o arquivo Excel
        file_path = await download_backlinks_excel(page, domain)
        print(f"Arquivo baixado com sucesso: {file_path}")
        
        print("Processo de backlinks concluído!")
        
    except Exception as e:
        print(f"\nERRO ao verificar backlinks para {domain}: {str(e)}")
        print(f"URL atual: {page.url}")
        await page.screenshot(path=f"debug/backlinks_error_{domain}.png")
        print(f"Screenshot do erro salvo em debug/backlinks_error_{domain}.png")
        raise

def load_domains():
    """Carrega a lista de domínios do arquivo domains.txt"""
    try:
        with open('domains.txt', 'r', encoding='utf-8') as f:
            domains = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        if not domains:
            raise Exception("Nenhum domínio encontrado no arquivo domains.txt")
        return domains
    except Exception as e:
        print(f"Erro ao ler arquivo de domínios: {str(e)}")
        raise

def remove_domain_from_list(domain):
    """Remove um domínio da lista após processamento bem sucedido"""
    try:
        # Lê todas as linhas do arquivo
        with open('domains.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Remove o domínio processado
        with open('domains.txt', 'w', encoding='utf-8') as f:
            for line in lines:
                if line.strip() != domain:
                    f.write(line)
        
        print(f"Domínio {domain} removido da lista")
    except Exception as e:
        print(f"Erro ao remover domínio da lista: {str(e)}")

async def launch(headless=False):
    """Inicia o navegador usando Playwright"""
    playwright = await async_playwright().start()
    return await playwright.chromium.launch(headless=headless)

def load_domain_history():
    """Carrega o histórico de domínios processados"""
    try:
        if os.path.exists('domain_history.json'):
            with open('domain_history.json', 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Erro ao carregar histórico: {str(e)}")
        return {}

def save_domain_history(history):
    """Salva o histórico de domínios processados"""
    try:
        with open('domain_history.json', 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Erro ao salvar histórico: {str(e)}")

def update_domain_history(domain):
    """Atualiza o histórico com um domínio processado"""
    history = load_domain_history()
    history[domain] = {
        'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'success'
    }
    save_domain_history(history)

def get_domains_to_check():
    """Retorna lista de domínios que precisam ser verificados"""
    history = load_domain_history()
    domains = load_domains()
    
    # Domínios que nunca foram verificados
    new_domains = [d for d in domains if d not in history]
    
    # Domínios que precisam ser rechecados (mais de 7 dias)
    recheck_domains = []
    for domain in domains:
        if domain in history:
            last_check = datetime.strptime(history[domain]['last_check'], '%Y-%m-%d %H:%M:%S')
            if datetime.now() - last_check > timedelta(days=7):
                recheck_domains.append(domain)
    
    return new_domains + recheck_domains

async def main():
    """Função principal"""
    try:
        print("\n=== Iniciando script de verificação de backlinks ===")
        
        # Carrega os domínios que precisam ser verificados
        domains = get_domains_to_check()
        if not domains:
            print("Nenhum domínio precisa ser verificado no momento")
            return
            
        print(f"Domínios para verificação: {domains}")
        
        # Inicializa o navegador
        browser = await launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Faz login no SEOPack
        await login_seopack(page)
        
        # Acessa o SEMrush
        await access_semrush(page)
        
        # Processa cada domínio
        for domain in domains:
            try:
                print(f"\nProcessando domínio: {domain}")
                await get_backlinks(page, domain)
                print(f"Domínio {domain} processado com sucesso!")
                
                # Atualiza o histórico
                update_domain_history(domain)
                
                # Aguarda um tempo entre os domínios
                print(f"Aguardando {DELAY_BETWEEN_REQUESTS} segundos antes do próximo domínio...")
                await asyncio.sleep(DELAY_BETWEEN_REQUESTS)
                
            except Exception as e:
                print(f"\nERRO ao verificar backlinks para {domain}: {str(e)}")
                print(f"URL atual: {page.url}")
                await page.screenshot(path=f"debug/backlinks_error_{domain}.png")
                print(f"Screenshot do erro salvo em debug/backlinks_error_{domain}.png")
                print("Continuando com o próximo domínio...")
                continue
        
        print("\nProcessamento de todos os domínios concluído!")
        
        # Fecha o navegador
        await browser.close()
        
    except Exception as e:
        print(f"\nErro durante a execução: {str(e)}")
        if 'page' in locals():
            await page.screenshot(path="debug/main_error.png")
            print("Screenshot do erro salvo em debug/main_error.png")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 