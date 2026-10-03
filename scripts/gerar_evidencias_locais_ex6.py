import subprocess
import sys
from html import escape
from pathlib import Path

from playwright.sync_api import sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "ex6"


def montar_linhas_codigo() -> str:
    arquivo = PROJECT_ROOT / "app" / "auth" / "security.py"
    linhas = arquivo.read_text(encoding="utf-8").splitlines()
    intervalos = ((5, 8), (12, 18), (23, 31), (34, 38), (48, 69), (80, 104))
    conteudo = []
    for indice, (inicio, fim) in enumerate(intervalos):
        if indice:
            conteudo.append('<div class="separator">⋮</div>')
        for numero in range(inicio, fim + 1):
            texto = escape(linhas[numero - 1]) or "&nbsp;"
            conteudo.append(
                f'<div class="code-line"><span class="number">{numero}</span>'
                f'<code>{texto}</code></div>'
            )
    return "".join(conteudo)


def html_codigo() -> str:
    return f"""
    <!doctype html>
    <html lang="pt-BR">
    <head>
      <meta charset="utf-8">
      <style>
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; background: #1e1e1e; color: #d4d4d4; font-family: "Segoe UI", Arial, sans-serif; }}
        .titlebar {{ height: 42px; background: #181818; display: flex; align-items: end; border-bottom: 1px solid #2b2b2b; }}
        .tab {{ height: 36px; min-width: 190px; padding: 9px 18px; background: #1e1e1e; border-top: 1px solid #007acc; color: #e8e8e8; font-size: 14px; }}
        .python {{ color: #4fc1ff; margin-right: 9px; font-weight: 700; }}
        .close {{ color: #8c8c8c; float: right; }}
        .breadcrumbs {{ height: 38px; display: flex; align-items: center; padding: 0 24px; background: #1e1e1e; color: #9d9d9d; border-bottom: 1px solid #252525; font-size: 13px; }}
        .breadcrumbs span {{ color: #cccccc; margin: 0 8px; }}
        .code {{ background: #1e1e1e; padding: 15px 0 20px; overflow: hidden; }}
        .code-line {{ display: grid; grid-template-columns: 74px 1fr; min-height: 24px; font: 15px/24px Consolas, "Courier New", monospace; }}
        .code-line:hover {{ background: #262626; }}
        .number {{ color: #858585; text-align: right; padding-right: 20px; user-select: none; }}
        code {{ color: #dcdcaa; white-space: pre; }}
        .separator {{ color: #858585; padding-left: 37px; font: 20px/28px Consolas, monospace; }}
        .statusbar {{ height: 24px; background: #007acc; color: white; display: flex; justify-content: flex-end; align-items: center; gap: 22px; padding: 0 18px; font-size: 12px; }}
      </style>
    </head>
    <body>
      <div class="titlebar"><div class="tab"><span class="python">Py</span>security.py <span class="close">×</span></div></div>
      <div class="breadcrumbs">app <span>›</span> auth <span>›</span> security.py</div>
      <section class="code">{montar_linhas_codigo()}</section>
      <div class="statusbar"><span>Ln 104, Col 53</span><span>Spaces: 4</span><span>UTF-8</span><span>Python</span></div>
    </body>
    </html>
    """


def executar_testes() -> str:
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
    return saida.strip()


def html_testes(saida: str) -> str:
    terminal = escape(f"PS {PROJECT_ROOT}> python -m pytest -v\n\n{saida}")
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
        .terminal {{ min-height: 900px; padding: 24px 28px 34px; background: #0c0c0c; }}
        pre {{ margin: 0; white-space: pre-wrap; font: 15px/23px Consolas, "Courier New", monospace; color: #f2f2f2; }}
      </style>
    </head>
    <body>
      <div class="titlebar">
        <div class="tab">PowerShell</div><div class="plus">+</div>
        <div class="controls"><span>─</span><span>□</span><span>×</span></div>
      </div>
      <section class="terminal"><pre>{terminal}</pre></section>
    </body>
    </html>
    """


def gerar_evidencias() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    saida_testes = executar_testes()

    with sync_playwright() as playwright:
        navegador = playwright.chromium.launch(channel="msedge", headless=True)
        pagina = navegador.new_page(viewport={"width": 1800, "height": 1200})
        pagina.set_content(html_codigo(), wait_until="load")
        pagina.screenshot(
            path=EVIDENCE_DIR / "oauth2_jwt_bcrypt.png",
            full_page=True,
        )
        pagina.set_viewport_size({"width": 1700, "height": 1100})
        pagina.set_content(html_testes(saida_testes), wait_until="load")
        pagina.screenshot(
            path=EVIDENCE_DIR / "testes_autorizacao.png",
            full_page=True,
        )
        navegador.close()


if __name__ == "__main__":
    gerar_evidencias()
