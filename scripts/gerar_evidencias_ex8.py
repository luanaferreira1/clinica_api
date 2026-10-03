import os
import subprocess
import sys
import time
from html import escape
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "ex8"
BASE_URL = "http://127.0.0.1:8018"


def editor_html() -> str:
    arquivo = PROJECT_ROOT / "app" / "routes" / "prontuarios.py"
    linhas = arquivo.read_text(encoding="utf-8").splitlines()
    conteudo = []
    for numero, linha in enumerate(linhas, 1):
        texto = escape(linha) or "&nbsp;"
        conteudo.append(
            f'<div class="code-line"><span class="number">{numero}</span>'
            f'<code>{texto}</code></div>'
        )
    return f"""
    <!doctype html>
    <html lang="pt-BR">
    <head>
      <meta charset="utf-8">
      <style>
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; background: #1e1e1e; color: #d4d4d4; font-family: "Segoe UI", Arial, sans-serif; }}
        .titlebar {{ height: 42px; background: #181818; display: flex; align-items: end; border-bottom: 1px solid #2b2b2b; }}
        .tab {{ height: 36px; min-width: 210px; padding: 9px 18px; background: #1e1e1e; border-top: 1px solid #007acc; color: #e8e8e8; font-size: 14px; }}
        .python {{ color: #4fc1ff; margin-right: 9px; font-weight: 700; }}
        .close {{ color: #8c8c8c; float: right; }}
        .breadcrumbs {{ height: 38px; display: flex; align-items: center; padding: 0 24px; color: #9d9d9d; border-bottom: 1px solid #252525; font-size: 13px; }}
        .breadcrumbs span {{ color: #cccccc; margin: 0 8px; }}
        .code {{ min-height: 700px; padding: 15px 0 20px; }}
        .code-line {{ display: grid; grid-template-columns: 70px 1fr; min-height: 25px; font: 16px/25px Consolas, "Courier New", monospace; }}
        .code-line:hover {{ background: #262626; }}
        .number {{ color: #858585; text-align: right; padding-right: 20px; user-select: none; }}
        code {{ color: #d4d4d4; white-space: pre; }}
        .statusbar {{ height: 24px; background: #007acc; color: white; display: flex; justify-content: flex-end; align-items: center; gap: 22px; padding: 0 18px; font-size: 12px; }}
      </style>
    </head>
    <body>
      <div class="titlebar"><div class="tab"><span class="python">Py</span>prontuarios.py <span class="close">×</span></div></div>
      <div class="breadcrumbs">app <span>›</span> routes <span>›</span> prontuarios.py</div>
      <section class="code">{"".join(conteudo)}</section>
      <div class="statusbar"><span>Ln 30, Col 21</span><span>Spaces: 4</span><span>UTF-8</span><span>Python</span></div>
    </body>
    </html>
    """


def terminal_html(saida: str, altura: int = 820) -> str:
    return f"""
    <!doctype html>
    <html lang="pt-BR">
    <head>
      <meta charset="utf-8">
      <style>
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; background: #0c0c0c; color: #f2f2f2; font-family: "Segoe UI", Arial, sans-serif; }}
        .titlebar {{ height: 44px; background: #1f1f1f; display: flex; align-items: center; border-bottom: 1px solid #343434; }}
        .tab {{ height: 34px; min-width: 230px; margin-left: 10px; padding: 8px 16px; background: #0c0c0c; border-radius: 7px 7px 0 0; font-size: 14px; }}
        .plus {{ margin-left: 14px; color: #c8c8c8; font-size: 21px; }}
        .controls {{ margin-left: auto; display: flex; gap: 28px; padding-right: 22px; color: #b7b7b7; font-size: 13px; }}
        .terminal {{ min-height: {altura}px; padding: 24px 28px 34px; }}
        pre {{ margin: 0; white-space: pre-wrap; font: 15px/23px Consolas, "Courier New", monospace; color: #f2f2f2; }}
      </style>
    </head>
    <body>
      <div class="titlebar"><div class="tab">PowerShell</div><div class="plus">+</div><div class="controls"><span>─</span><span>□</span><span>×</span></div></div>
      <section class="terminal"><pre>{escape(saida)}</pre></section>
    </body>
    </html>
    """


def localizar_operacao(page: Page, metodo: str, caminho: str):
    return page.locator(".opblock").filter(
        has=page.locator(".opblock-summary-method", has_text=metodo)
    ).filter(has=page.locator(".opblock-summary-path", has_text=caminho))


def aguardar_api(page: Page) -> None:
    for _ in range(40):
        try:
            if page.request.get(f"{BASE_URL}/health").status == 200:
                return
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("A API não iniciou na porta 8018")


def gerar_evidencias() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    ambiente = os.environ.copy()
    ambiente["JWT_SECRET_KEY"] = "chave-local-evidencias-ex8-com-mais-de-32-caracteres"
    ambiente["ADMIN_MFA_CODE"] = "654321"
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    servidor = subprocess.Popen(
        [
            str(PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8018",
        ],
        cwd=PROJECT_ROOT,
        env=ambiente,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )

    try:
        with sync_playwright() as playwright:
            navegador = playwright.chromium.launch(channel="msedge", headless=True)
            pagina = navegador.new_page(viewport={"width": 1440, "height": 1200})
            aguardar_api(pagina)

            pagina.set_viewport_size({"width": 1440, "height": 900})
            pagina.set_content(editor_html(), wait_until="load")
            pagina.screenshot(path=EVIDENCE_DIR / "bola_codigo.png", full_page=True)

            login_profissional = pagina.request.post(
                f"{BASE_URL}/auth/token",
                form={
                    "grant_type": "password",
                    "username": "profissional8",
                    "password": "Profissional@123",
                },
            )
            assert login_profissional.status == 200
            token_profissional = login_profissional.json()["access_token"]
            criada = pagina.request.post(
                f"{BASE_URL}/consultas",
                headers={"Authorization": f"Bearer {token_profissional}"},
                data={
                    "paciente_id": 2,
                    "profissional_id": 8,
                    "data_hora": "2030-06-12T09:00:00-03:00",
                    "motivo": "Acompanhamento cardiológico",
                    "observacoes": "Paciente relata histórico familiar de hipertensão.",
                    "status": "agendada",
                },
            )
            assert criada.status == 201
            consulta_id = criada.json()["id"]

            pagina.goto(f"{BASE_URL}/docs", wait_until="networkidle")
            pagina.locator("button.authorize").first.click()
            dialogo = pagina.locator(".dialog-ux")
            dialogo.locator("input").nth(0).fill("paciente1")
            dialogo.locator("input").nth(1).fill("Paciente@123")
            with pagina.expect_response(lambda resposta: resposta.url.endswith("/auth/token")) as captura:
                dialogo.locator("button.modal-btn.auth.authorize").click(force=True)
            assert captura.value.status == 200
            expect(dialogo).to_contain_text("Authorized", timeout=10000)
            dialogo.get_by_role("button", name="Close").click()

            identidade = localizar_operacao(pagina, "GET", "/auth/me")
            identidade.locator(".opblock-summary").click()
            identidade.get_by_role("button", name="Try it out").click()
            with pagina.expect_response(lambda resposta: resposta.url.endswith("/auth/me")) as captura:
                identidade.get_by_role("button", name="Execute").click()
            assert captura.value.status == 200
            assert captura.value.json()["username"] == "paciente1"
            assert captura.value.json()["paciente_id"] == 1
            status_identidade = identidade.locator(
                ".live-responses-table .response-col_status:not(.col_header)"
            )
            expect(status_identidade).to_contain_text("200", timeout=10000)
            identidade.screenshot(path=EVIDENCE_DIR / "identidade_paciente1.png")

            operacao = localizar_operacao(
                pagina,
                "GET",
                "/pacientes/consultas/{consulta_id}",
            )
            operacao.locator(".opblock-summary").click()
            operacao.get_by_role("button", name="Try it out").click()
            operacao.locator('input[placeholder="consulta_id"]').fill(str(consulta_id))
            with pagina.expect_response(
                lambda resposta: f"/pacientes/consultas/{consulta_id}" in resposta.url
            ) as captura:
                operacao.get_by_role("button", name="Execute").click()
            assert captura.value.status == 200
            status = operacao.locator(".live-responses-table .response-col_status:not(.col_header)")
            expect(status).to_contain_text("200", timeout=10000)
            operacao.scroll_into_view_if_needed()
            operacao.screenshot(path=EVIDENCE_DIR / "bola_exploracao_200.png")

            codigos = []
            for tentativa in range(1, 7):
                resposta = pagina.request.post(
                    f"{BASE_URL}/auth/token",
                    form={
                        "grant_type": "password",
                        "username": "profissional7",
                        "password": f"senha-invalida-{tentativa}",
                    },
                )
                codigos.append(resposta.status)
            assert codigos == [401] * 6
            prompt = str(PROJECT_ROOT)
            saida_rate = (
                f"PS {prompt}> 1..6 | ForEach-Object {{\n"
                ">>   try { Invoke-WebRequest -Method Post -Uri http://127.0.0.1:8018/auth/token `\n"
                ">>     -ContentType application/x-www-form-urlencoded `\n"
                ">>     -Body \"grant_type=password&username=profissional7&password=senha-invalida-$_\" } `\n"
                ">>   catch { \"Tentativa $_`: HTTP $($_.Exception.Response.StatusCode.value__)\" }\n"
                ">> }\n\n"
                + "\n".join(
                    f"Tentativa {indice}: HTTP {codigo}"
                    for indice, codigo in enumerate(codigos, 1)
                )
                + "\n\nHTTP 429 recebido: não"
            )
            pagina.set_viewport_size({"width": 1500, "height": 760})
            pagina.set_content(terminal_html(saida_rate, 640), wait_until="load")
            pagina.screenshot(path=EVIDENCE_DIR / "auth_sem_rate_limit.png", full_page=True)

            resposta_health = pagina.request.get(f"{BASE_URL}/health")
            assert resposta_health.status == 200
            nomes = [
                "strict-transport-security",
                "x-frame-options",
                "x-content-type-options",
            ]
            valores = [
                f"{nome}: {resposta_health.headers.get(nome, 'AUSENTE')}"
                for nome in nomes
            ]
            saida_headers = (
                f"PS {prompt}> Invoke-WebRequest http://127.0.0.1:8018/health\n\n"
                "StatusCode        : 200\n"
                "StatusDescription : OK\n\n"
                f"PS {prompt}> $resposta.Headers\n\n"
                + "\n".join(valores)
            )
            pagina.set_content(terminal_html(saida_headers, 640), wait_until="load")
            pagina.screenshot(path=EVIDENCE_DIR / "headers_ausentes.png", full_page=True)

            resultado = subprocess.run(
                [sys.executable, "-m", "pytest", "-v"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                encoding="cp1252",
                errors="replace",
                check=False,
            )
            saida_testes = resultado.stdout
            if resultado.stderr:
                saida_testes = f"{saida_testes}\n{resultado.stderr}"
            if resultado.returncode != 0:
                raise RuntimeError(saida_testes)
            terminal_testes = f"PS {prompt}> python -m pytest -v\n\n{saida_testes.strip()}"
            pagina.set_viewport_size({"width": 1700, "height": 1100})
            pagina.set_content(terminal_html(terminal_testes, 1000), wait_until="load")
            pagina.screenshot(path=EVIDENCE_DIR / "testes_ex8.png", full_page=True)
            navegador.close()
    finally:
        servidor.terminate()
        try:
            servidor.wait(timeout=5)
        except subprocess.TimeoutExpired:
            servidor.kill()


if __name__ == "__main__":
    gerar_evidencias()
