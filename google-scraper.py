import asyncio
import re
from urllib.parse import quote
from playwright.async_api import async_playwright

PESQUISA = "site:://youtube.com ozempic" # restringindo pesquisas do google ao site youtube
ARQUIVO_SAIDA = "links.txt"
MAX_PAGINAS = 1000

JS_STEALTH = """
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

window.chrome = {
    runtime: {}
};

Object.defineProperty(navigator, 'languages', {
    get: () => ['pt-BR', 'pt', 'en-US', 'en']
});

Object.defineProperty(navigator, 'plugins', {
    get: () => [
        { name: 'Chrome PDF Plugin' },
        { name: 'Chrome PDF Viewer' },
        { name: 'Native Client' }
    ]
});
"""

async def extrair_links(page):
    return await page.evaluate("""
        () => {
            const links = [];
            document.querySelectorAll('div#search a').forEach(a => {
                const href = a.href;
                if (!href) return;
                if (!href.startsWith('http')) return;
                if (href.includes('google.com')) return;
                links.push(href);
            });
            return [...new Set(links)];
        }
    """)

async def obter_url_proxima_pagina(page):
    """Retorna o link (href) do botão 'Próxima' se ele existir"""
    return await page.evaluate("""
        () => {
            const botao = document.querySelector('#pnnext');
            if (!botao) return null;
            return botao.href;
        }
    """)

def salvar_links_arquivo(links_set):
    """Salva os links gradualmente para não perder dados se o script parar"""
    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as arquivo:
        for link in links_set:
            arquivo.write(link + "\n")

async def main():
    # URL inicial da pesquisa
    url_atual = (
        "https://www.google.com/search" +
        "?q=" + quote(PESQUISA) +
        "&hl=pt-BR" +
        "&num=10"
    )

    todos_links = set()
    pagina_atual = 1

    async with async_playwright() as p:
        
        # LOOP EXTERNO: Responsável por gerenciar a vida útil do navegador (Restart)
        while pagina_atual <= MAX_PAGINAS:
            
            print("\n" + "=" * 70)
            print(f" INICIANDO/RETOMANDO NAVEGADOR - ALVO: PÁGINA {pagina_atual}")
            print("=" * 70)

            navegador = await p.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-infobars"
                ]
            )

            contexto = await navegador.new_context(
                viewport={"width": 1280, "height": 800},
                locale="pt-BR",
                timezone_id="America/Sao_Paulo"
            )

            page = await contexto.new_page()
            await page.add_init_script(JS_STEALTH)

            try:
                print(f" Acessando: {url_atual}")
                await page.goto(url_atual, wait_until="domcontentloaded", timeout=60000)

                # LOOP INTERNO: Fica extraindo enquanto não for bloqueado
                while pagina_atual <= MAX_PAGINAS:
                    await asyncio.sleep(3)

                    print("\n" + "-" * 70)
                    print(f" PÁGINA {pagina_atual}")
                    print("-" * 70)
                    print(f" URL atual: {page.url}")

                    # 1. Verifica se fomos jogados para uma página de CAPTCHA
                    captcha = await page.locator('form[action="/sorry/index"]').count()
                    if captcha > 0:
                        raise Exception("Bloqueio detectado (Google Captcha).")

                    # 2. Extrai os links
                    links = await extrair_links(page)
                    print(f" Links encontrados na página: {len(links)}")

                    # VERIFICAÇÃO 1: Fim dos resultados (0 links encontrados)
                    if len(links) == 0:
                        print("\n🏁 Nenhum link encontrado nesta página.")
                        print("🏁 Fim dos resultados alcançado (Última página do Google).")
                        pagina_atual = MAX_PAGINAS + 1  # Força a saída do loop externo
                        break                           # Sai do loop interno

                    novos = 0
                    for link in links:
                        # Limpa o parâmetro de tempo do YouTube (ex: &t=120s, &t=1h2m)
                        # Remove o '&t=' seguido por qualquer letra ou número
                        link = re.sub(r'&t=[a-zA-Z0-9]+', '', link)

                        if link not in todos_links:
                            todos_links.add(link)
                            novos += 1

                    print(f" Links novos: {novos}")
                    print(f" Total acumulado: {len(todos_links)}")
                    
                    # Salva os links extraídos até o momento
                    salvar_links_arquivo(todos_links)

                    # 3. Pega a URL da próxima página ANTES de tentar mudar
                    proxima_url = await obter_url_proxima_pagina(page)

                    # VERIFICAÇÃO 2: Botão "Próxima" não existe (Última página do Google)
                    if not proxima_url:
                        print("\n Botão 'Próxima' não encontrado.")
                        print(" Fim dos resultados do Google.")
                        pagina_atual = MAX_PAGINAS + 1  # Força a saída do loop externo
                        break

                    url_atual = proxima_url

                    # Rola até o final
                    await page.evaluate("""
                        () => {
                            window.scrollTo({
                                top: document.body.scrollHeight,
                                behavior: 'smooth'
                            });
                        }
                    """)
                    await asyncio.sleep(1)

                    # 5. Navega para a próxima página acessando a URL salva
                    print(" Carregando próxima página...")
                    await page.goto(proxima_url, wait_until="domcontentloaded", timeout=60000)
                    
                    pagina_atual += 1
                    await asyncio.sleep(4)

            except Exception as e:
                print(f" Fluxo interrompido: {e}")
                print(" O navegador será fechado para resetar o perfil. Retomaremos na última URL...")
            
            finally:
                await navegador.close()
                if pagina_atual <= MAX_PAGINAS:
                    print(" Aguardando 5 segundos para resfriar a conexão...")
                    await asyncio.sleep(5)

    print("\n" + "=" * 70)
    print(" PESQUISA FINALIZADA TOTALMENTE")
    print("=" * 70)
    print(f" Links únicos capturados: {len(todos_links)}")
    print(f" Arquivo final: {ARQUIVO_SAIDA}")

if __name__ == "__main__":
    asyncio.run(main())
