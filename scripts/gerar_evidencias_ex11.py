import os
import re
import subprocess
import sys
import tempfile
import time
from html import escape
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "ex11"
BASE_URL = "http://127.0.0.1:8021"


def iniciar_servidor(ambiente: dict[str, str]) -> subprocess.Popen:
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    return subprocess.Popen(
        [
            str(PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8021",
        ],
        cwd=PROJECT_ROOT,
        env=ambiente,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )


def encerrar_servidor(servidor: subprocess.Popen) -> None:
    servidor.terminate()
    try:
        servidor.wait(timeout=5)
    except subprocess.TimeoutExpired:
        servidor.kill()
        servidor.wait()


def aguardar_api(page: Page) -> None:
    for _ in range(50):
        try:
            if page.request.get(f"{BASE_URL}/health").status == 200:
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("A API não iniciou na porta 8021")


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


def capturar_operacao(operacao, destino: Path) -> None:
    operacao.locator(
        ".responses-table:not(.live-responses-table)"
    ).evaluate_all(
        "elementos => elementos.forEach(elemento => elemento.style.display = 'none')"
    )
    operacao.screenshot(path=destino)


def linhas_editor(arquivo: Path) -> str:
    conteudo = []
    for numero, linha in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), 1):
        texto = escape(linha) or "&nbsp;"
        conteudo.append(
            f'<div class="code-line"><span class="number">{numero}</span>'
            f'<code>{texto}</code></div>'
        )
    return "".join(conteudo)


def editor_html() -> str:
    config = linhas_editor(PROJECT_ROOT / "app" / "config.py")
    session = linhas_editor(PROJECT_ROOT / "app" / "database" / "session.py")
    return f"""
    <!doctype html>
    <html lang="pt-BR">
    <head>
      <meta charset="utf-8">
      <style>
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; background: #1e1e1e; color: #d4d4d4; font-family: "Segoe UI", Arial, sans-serif; }}
        .titlebar {{ height: 42px; background: #181818; display: flex; align-items: end; border-bottom: 1px solid #2b2b2b; }}
        .tab {{ height: 36px; min-width: 180px; padding: 9px 16px; background: #1e1e1e; color: #e8e8e8; font-size: 14px; }}
        .tab.active {{ border-top: 1px solid #007acc; }}
        .python {{ color: #4fc1ff; margin-right: 8px; font-weight: 700; }}
        .close {{ color: #8c8c8c; float: right; }}
        .workspace {{ display: grid; grid-template-columns: 1fr 1fr; min-height: 1030px; }}
        .pane:first-child {{ border-right: 1px solid #3b3b3b; }}
        .breadcrumbs {{ height: 38px; display: flex; align-items: center; padding: 0 20px; color: #9d9d9d; border-bottom: 1px solid #252525; font-size: 13px; }}
        .breadcrumbs span {{ color: #cccccc; margin: 0 7px; }}
        .code {{ padding: 14px 0 24px; overflow: hidden; }}
        .code-line {{ display: grid; grid-template-columns: 58px 1fr; min-height: 23px; font: 14px/23px Consolas, "Courier New", monospace; }}
        .number {{ color: #858585; text-align: right; padding-right: 16px; user-select: none; }}
        code {{ color: #d4d4d4; white-space: pre; }}
        .statusbar {{ height: 24px; background: #007acc; color: white; display: flex; justify-content: flex-end; align-items: center; gap: 22px; padding: 0 18px; font-size: 12px; }}
      </style>
    </head>
    <body>
      <div class="titlebar">
        <div class="tab active"><span class="python">Py</span>config.py <span class="close">×</span></div>
        <div class="tab"><span class="python">Py</span>session.py <span class="close">×</span></div>
      </div>
      <div class="workspace">
        <section class="pane"><div class="breadcrumbs">app <span>›</span> config.py</div><div class="code">{config}</div></section>
        <section class="pane"><div class="breadcrumbs">app <span>›</span> database <span>›</span> session.py</div><div class="code">{session}</div></section>
      </div>
      <div class="statusbar"><span>Spaces: 4</span><span>UTF-8</span><span>Python</span></div>
    </body>
    </html>
    """


def terminal_html(saida: str, altura: int) -> str:
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


def extrair_query_parametrizada(log: str) -> str:
    linhas = log.splitlines()
    indice = next(
        indice
        for indice, linha in enumerate(linhas)
        if "WHERE consultas.status = ?" in linha
    )
    inicio = max(0, indice - 2)
    fim = min(len(linhas), indice + 3)
    return "\n".join(linhas[inicio:fim])


def gerar_evidencias() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    servidor: subprocess.Popen | None = None
    with tempfile.TemporaryDirectory(prefix="clinica-ex11-") as diretorio:
        banco = Path(diretorio) / "evidencia.db"
        ambiente = os.environ.copy()
        ambiente["APP_ENV"] = "development"
        ambiente["DATABASE_URL"] = f"sqlite:///{banco.as_posix()}"
        ambiente["DATABASE_ECHO"] = "true"
        ambiente["JWT_SECRET_KEY"] = "chave-local-evidencias-ex11-com-mais-de-32-caracteres"
        ambiente["ADMIN_MFA_CODE"] = "654321"

        try:
            with sync_playwright() as playwright:
                navegador = playwright.chromium.launch(channel="msedge", headless=True)
                pagina = navegador.new_page(viewport={"width": 1440, "height": 1100})

                servidor = iniciar_servidor(ambiente)
                aguardar_api(pagina)
                login = pagina.request.post(
                    f"{BASE_URL}/auth/token",
                    form={
                        "grant_type": "password",
                        "username": "profissional7",
                        "password": "Profissional@123",
                    },
                )
                assert login.status == 200
                token = login.json()["access_token"]
                criada = pagina.request.post(
                    f"{BASE_URL}/consultas",
                    headers={"Authorization": f"Bearer {token}"},
                    data={
                        "paciente_id": 1,
                        "profissional_id": 7,
                        "data_hora": "2030-08-10T09:30:00-03:00",
                        "motivo": "Consulta mantida após reinício do servidor",
                        "observacoes": "Persistência comprovada em SQLite.",
                        "status": "agendada",
                    },
                )
                assert criada.status == 201
                encerrar_servidor(servidor)
                servidor = None

                servidor = iniciar_servidor(ambiente)
                aguardar_api(pagina)
                pagina.goto(f"{BASE_URL}/docs", wait_until="networkidle")
                autorizar(pagina, "profissional7", "Profissional@123")
                listar = localizar_operacao(pagina, "GET", "/consultas")
                listar.locator(".opblock-summary").click()
                listar.get_by_role("button", name="Try it out").click()
                with pagina.expect_response(
                    lambda resposta: resposta.request.method == "GET"
                    and resposta.url.rstrip("/").endswith("/consultas")
                ) as captura:
                    listar.get_by_role("button", name="Execute").click()
                assert captura.value.status == 200
                assert captura.value.json()[0]["motivo"] == "Consulta mantida após reinício do servidor"
                status = listar.locator(
                    ".live-responses-table .response-col_status:not(.col_header)"
                )
                expect(status).to_contain_text("200", timeout=10000)
                capturar_operacao(
                    listar,
                    EVIDENCE_DIR / "persistencia_apos_reinicio.png",
                )

                login_reinicio = pagina.request.post(
                    f"{BASE_URL}/auth/token",
                    form={
                        "grant_type": "password",
                        "username": "profissional7",
                        "password": "Profissional@123",
                    },
                )
                assert login_reinicio.status == 200
                token_reinicio = login_reinicio.json()["access_token"]
                filtrada = pagina.request.get(
                    f"{BASE_URL}/consultas?status=agendada",
                    headers={"Authorization": f"Bearer {token_reinicio}"},
                )
                assert filtrada.status == 200
                encerrar_servidor(servidor)
                servidor = None
                resultado_query = subprocess.run(
                    [
                        str(PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"),
                        "-c",
                        "from sqlmodel import Session; from app.database import consulta_repository, get_engine; session = Session(get_engine()); consulta_repository.listar(session, status='agendada'); session.close()",
                    ],
                    cwd=PROJECT_ROOT,
                    env=ambiente,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=True,
                )
                log = f"{resultado_query.stdout}\n{resultado_query.stderr}"
                trecho_query = extrair_query_parametrizada(log)
                prompt = str(PROJECT_ROOT)
                saida_query = (
                    f"PS {prompt}> GET /consultas?status=agendada\n\n"
                    "HTTP 200\n\n"
                    f"{trecho_query}"
                )
                pagina.set_viewport_size({"width": 1700, "height": 620})
                pagina.set_content(terminal_html(saida_query, 520), wait_until="load")
                pagina.screenshot(
                    path=EVIDENCE_DIR / "query_parametrizada.png",
                    full_page=True,
                )

                pagina.set_viewport_size({"width": 1900, "height": 1150})
                pagina.set_content(editor_html(), wait_until="load")
                pagina.screenshot(
                    path=EVIDENCE_DIR / "basesettings_sessao.png",
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
                saida_testes = resultado.stdout
                if resultado.stderr:
                    saida_testes = f"{saida_testes}\n{resultado.stderr}"
                if resultado.returncode != 0:
                    raise RuntimeError(saida_testes)
                terminal = f"PS {prompt}> python -m pytest -v\n\n{saida_testes.strip()}"
                pagina.set_viewport_size({"width": 1800, "height": 1300})
                pagina.set_content(terminal_html(terminal, 1200), wait_until="load")
                pagina.screenshot(
                    path=EVIDENCE_DIR / "testes_persistencia.png",
                    full_page=True,
                )
                navegador.close()
        finally:
            if servidor is not None and servidor.poll() is None:
                encerrar_servidor(servidor)


if __name__ == "__main__":
    gerar_evidencias()
