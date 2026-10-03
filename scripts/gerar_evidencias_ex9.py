import json
import os
import re
import subprocess
import sys
import time
from html import escape
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "ex9"
BASE_URL = "http://127.0.0.1:8019"


def localizar_operacao(page: Page, metodo: str, caminho: str):
    seletor_caminho = page.locator(
        ".opblock-summary-path",
        has_text=re.compile(rf"^{re.escape(caminho)}$"),
    )
    seletor_metodo = page.locator(
        ".opblock-summary-method",
        has_text=re.compile(rf"^{metodo}$"),
    )
    return page.locator(".opblock").filter(has=seletor_caminho).filter(has=seletor_metodo)


def autorizar(page: Page, username: str, password: str) -> None:
    page.locator("button.authorize").first.click()
    dialogo = page.locator(".dialog-ux")
    dialogo.locator("input").nth(0).fill(username)
    dialogo.locator("input").nth(1).fill(password)
    with page.expect_response(lambda resposta: resposta.url.endswith("/auth/token")) as captura:
        dialogo.locator("button.modal-btn.auth.authorize").click(force=True)
    assert captura.value.status == 200
    expect(dialogo).to_contain_text("Authorized", timeout=10000)
    dialogo.get_by_role("button", name="Close").click()


def aguardar_api(page: Page) -> None:
    for _ in range(40):
        try:
            if page.request.get(f"{BASE_URL}/health").status == 200:
                return
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("A API não iniciou na porta 8019")


def capturar_operacao(page: Page, operacao, destino: Path) -> None:
    operacao.scroll_into_view_if_needed()
    operacao.locator(
        ".responses-table:not(.live-responses-table)"
    ).evaluate_all(
        "elementos => elementos.forEach(elemento => elemento.style.display = 'none')"
    )
    operacao.screenshot(path=destino)


def terminal_html(saida: str) -> str:
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
        .terminal {{ min-height: 1050px; padding: 24px 28px 34px; }}
        pre {{ margin: 0; white-space: pre-wrap; font: 15px/23px Consolas, "Courier New", monospace; color: #f2f2f2; }}
      </style>
    </head>
    <body>
      <div class="titlebar"><div class="tab">PowerShell</div><div class="plus">+</div><div class="controls"><span>─</span><span>□</span><span>×</span></div></div>
      <section class="terminal"><pre>{escape(saida)}</pre></section>
    </body>
    </html>
    """


def gerar_evidencias() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    ambiente = os.environ.copy()
    ambiente["APP_ENV"] = "test"
    ambiente["DATABASE_URL"] = "sqlite://"
    ambiente["DATABASE_ECHO"] = "false"
    ambiente["JWT_SECRET_KEY"] = "chave-local-evidencias-ex9-com-mais-de-32-caracteres"
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
            "8019",
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
            pagina = navegador.new_page(viewport={"width": 1440, "height": 1100})
            aguardar_api(pagina)

            login_profissional8 = pagina.request.post(
                f"{BASE_URL}/auth/token",
                form={
                    "grant_type": "password",
                    "username": "profissional8",
                    "password": "Profissional@123",
                },
            )
            assert login_profissional8.status == 200
            token_profissional8 = login_profissional8.json()["access_token"]
            consulta_paciente2 = pagina.request.post(
                f"{BASE_URL}/consultas",
                headers={"Authorization": f"Bearer {token_profissional8}"},
                data={
                    "paciente_id": 2,
                    "profissional_id": 8,
                    "data_hora": "2030-07-15T09:00:00-03:00",
                    "motivo": "Acompanhamento cardiológico",
                    "observacoes": "Retorno clínico programado.",
                    "status": "agendada",
                },
            )
            assert consulta_paciente2.status == 201
            consulta_id = consulta_paciente2.json()["id"]

            pagina.goto(f"{BASE_URL}/docs", wait_until="networkidle")
            autorizar(pagina, "paciente1", "Paciente@123")
            prontuario = localizar_operacao(
                pagina,
                "GET",
                "/pacientes/consultas/{consulta_id}",
            )
            prontuario.locator(".opblock-summary").click()
            prontuario.get_by_role("button", name="Try it out").click()
            prontuario.locator('input[placeholder="consulta_id"]').fill(str(consulta_id))
            with pagina.expect_response(
                lambda resposta: f"/pacientes/consultas/{consulta_id}" in resposta.url
            ) as captura:
                prontuario.get_by_role("button", name="Execute").click()
            assert captura.value.status == 403
            status_bola = prontuario.locator(
                ".live-responses-table .response-col_status:not(.col_header)"
            )
            expect(status_bola).to_contain_text("403", timeout=10000)
            capturar_operacao(
                pagina,
                prontuario,
                EVIDENCE_DIR / "bola_corrigida_403.png",
            )

            contexto_profissional = navegador.new_context()
            pagina_profissional = contexto_profissional.new_page()
            pagina_profissional.set_viewport_size({"width": 1440, "height": 1200})
            pagina_profissional.goto(f"{BASE_URL}/docs", wait_until="networkidle")
            autorizar(pagina_profissional, "profissional7", "Profissional@123")
            criar = localizar_operacao(pagina_profissional, "POST", "/consultas")
            criar.locator(".opblock-summary").click()
            criar.get_by_role("button", name="Try it out").click()
            payload_invalido = {
                "paciente_id": 1,
                "profissional_id": 7,
                "data_hora": "2030-07-15T10:00:00-03:00",
                "motivo": "Retorno'; DROP TABLE consultas;--",
                "observacoes": "Teste controlado de validação.",
                "status": "agendada' OR 1=1--",
                "papel": "administrador",
            }
            campo_payload = criar.locator("textarea.body-param__text")
            campo_payload.fill(
                json.dumps(payload_invalido, ensure_ascii=False, indent=2)
            )
            campo_payload.evaluate(
                "elemento => { elemento.style.minHeight = '0'; elemento.style.height = '180px'; }"
            )
            with pagina_profissional.expect_response(
                lambda resposta: resposta.url.rstrip("/").endswith("/consultas")
                and resposta.request.method == "POST"
            ) as captura:
                criar.get_by_role("button", name="Execute").click()
            assert captura.value.status == 422
            detalhes = captura.value.json()["detail"]
            tipos = {detalhe["type"] for detalhe in detalhes}
            assert {
                "string_pattern_mismatch",
                "literal_error",
                "extra_forbidden",
            }.issubset(tipos)
            status_entrada = criar.locator(
                ".live-responses-table .response-col_status:not(.col_header)"
            )
            expect(status_entrada).to_contain_text("422", timeout=10000)
            capturar_operacao(
                pagina_profissional,
                criar,
                EVIDENCE_DIR / "entrada_rejeitada_422.png",
            )

            login_profissional7 = pagina.request.post(
                f"{BASE_URL}/auth/token",
                form={
                    "grant_type": "password",
                    "username": "profissional7",
                    "password": "Profissional@123",
                },
            )
            assert login_profissional7.status == 200
            token_profissional7 = login_profissional7.json()["access_token"]
            consulta_xss = pagina.request.post(
                f"{BASE_URL}/consultas",
                headers={"Authorization": f"Bearer {token_profissional7}"},
                data={
                    "paciente_id": 1,
                    "profissional_id": 7,
                    "data_hora": "2030-07-15T11:00:00-03:00",
                    "motivo": "Consulta de acompanhamento",
                    "observacoes": '<script>alert("XSS")</script>',
                    "status": "agendada",
                },
            )
            assert consulta_xss.status == 201

            login_recepcao = pagina.request.post(
                f"{BASE_URL}/auth/token",
                form={
                    "grant_type": "password",
                    "username": "recepcao",
                    "password": "Recepcao@123",
                },
            )
            assert login_recepcao.status == 200
            token_recepcao = login_recepcao.json()["access_token"]

            contexto_agenda = navegador.new_context(
                extra_http_headers={"Authorization": f"Bearer {token_recepcao}"}
            )
            pagina_agenda = contexto_agenda.new_page()
            pagina_agenda.set_viewport_size({"width": 1440, "height": 900})
            pagina_agenda.goto(
                f"{BASE_URL}/agenda?data=2030-07-15",
                wait_until="networkidle",
            )
            expect(pagina_agenda.locator("body")).to_contain_text(
                '<script>alert("XSS")</script>'
            )
            assert pagina_agenda.locator("script").count() == 0
            pagina_agenda.screenshot(
                path=EVIDENCE_DIR / "xss_autoescape.png",
                full_page=True,
            )

            resultado = subprocess.run(
                [sys.executable, "-m", "pytest", "-v"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                encoding="cp1252",
                errors="replace",
                check=False,
            )
            saida = resultado.stdout
            if resultado.stderr:
                saida = f"{saida}\n{resultado.stderr}"
            if resultado.returncode != 0:
                raise RuntimeError(saida)
            prompt = str(PROJECT_ROOT)
            terminal = f"PS {prompt}> python -m pytest -v\n\n{saida.strip()}"
            pagina_terminal = navegador.new_page(viewport={"width": 1750, "height": 1200})
            pagina_terminal.set_content(terminal_html(terminal), wait_until="load")
            pagina_terminal.screenshot(
                path=EVIDENCE_DIR / "testes_seguranca_ex9.png",
                full_page=True,
            )
            navegador.close()
    finally:
        servidor.terminate()
        try:
            servidor.wait(timeout=5)
        except subprocess.TimeoutExpired:
            servidor.kill()


if __name__ == "__main__":
    gerar_evidencias()
