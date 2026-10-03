import json
import os
import subprocess
import sys
from html import escape
from pathlib import Path

from playwright.sync_api import sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "ex12"
REPORTS_DIR = PROJECT_ROOT / "reports"


def executar(argumentos: list[str]) -> subprocess.CompletedProcess[str]:
    ambiente = os.environ.copy()
    ambiente["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        argumentos,
        cwd=PROJECT_ROOT,
        env=ambiente,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def linhas_codigo(texto: str, inicio: int = 1) -> str:
    linhas = []
    for numero, linha in enumerate(texto.splitlines(), inicio):
        linhas.append(
            f'<div class="line"><span class="number">{numero}</span>'
            f'<span class="source">{escape(linha) or " "}</span></div>'
        )
    return "".join(linhas)


def editor_html(workflow: str, riscos: str) -> str:
    return f"""
    <!doctype html>
    <html lang="pt-BR">
    <head>
      <meta charset="utf-8">
      <style>
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; background: #181818; color: #d4d4d4; font-family: "Segoe UI", Arial, sans-serif; }}
        .tabs {{ height: 42px; display: flex; background: #181818; border-bottom: 1px solid #303030; }}
        .tab {{ padding: 11px 20px; background: #1f1f1f; border-right: 1px solid #303030; font-size: 14px; }}
        .tab span {{ color: #4ec9b0; margin-right: 8px; font-weight: 600; }}
        .workspace {{ display: grid; grid-template-columns: 56% 44%; min-height: 1010px; }}
        .pane {{ overflow: hidden; border-right: 1px solid #3a3a3a; }}
        .crumb {{ height: 38px; padding: 11px 18px; color: #b9b9b9; background: #1f1f1f; font-size: 13px; }}
        .code {{ padding: 14px 0 28px; font: 14px/21px Consolas, "Courier New", monospace; }}
        .line {{ display: flex; min-height: 21px; }}
        .number {{ width: 52px; padding-right: 14px; color: #858585; text-align: right; user-select: none; }}
        .source {{ white-space: pre; color: #dcdcdc; }}
        .status {{ height: 24px; padding: 4px 18px; background: #007acc; color: white; text-align: right; font-size: 12px; }}
      </style>
    </head>
    <body>
      <div class="tabs"><div class="tab"><span>◇</span>security.yml</div><div class="tab"><span>{{}}</span>risk-register.json</div></div>
      <main class="workspace">
        <section class="pane"><div class="crumb">.github › workflows › security.yml</div><div class="code">{linhas_codigo(workflow)}</div></section>
        <section class="pane"><div class="crumb">security › risk-register.json</div><div class="code">{linhas_codigo(riscos)}</div></section>
      </main>
      <div class="status">Spaces: 2&nbsp;&nbsp;&nbsp; UTF-8&nbsp;&nbsp;&nbsp; GitHub Actions</div>
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
        body {{ margin: 0; background: #0c0c0c; color: #f1f1f1; font-family: "Segoe UI", Arial, sans-serif; }}
        .titlebar {{ height: 44px; background: #1f1f1f; display: flex; align-items: center; border-bottom: 1px solid #333; }}
        .tab {{ height: 34px; min-width: 230px; margin-left: 10px; padding: 8px 16px; background: #0c0c0c; border-radius: 7px 7px 0 0; font-size: 14px; }}
        .plus {{ margin-left: 14px; color: #c8c8c8; font-size: 21px; }}
        .controls {{ margin-left: auto; padding-right: 22px; color: #b7b7b7; letter-spacing: 20px; }}
        .terminal {{ min-height: {altura}px; padding: 24px 28px 34px; }}
        pre {{ margin: 0; white-space: pre-wrap; font: 15px/23px Consolas, "Courier New", monospace; }}
      </style>
    </head>
    <body>
      <div class="titlebar"><div class="tab">PowerShell</div><div class="plus">+</div><div class="controls">─ □ ×</div></div>
      <section class="terminal"><pre>{escape(saida)}</pre></section>
    </body>
    </html>
    """


def resumo_scanners() -> tuple[int, int]:
    bandit = json.loads((REPORTS_DIR / "bandit.json").read_text(encoding="utf-8"))
    audit = json.loads((REPORTS_DIR / "pip-audit.json").read_text(encoding="utf-8"))
    achados_altos = sum(
        resultado.get("issue_severity") == "HIGH"
        for resultado in bandit.get("results", [])
    )
    vulnerabilidades = sum(
        len(dependencia.get("vulns", []))
        for dependencia in audit.get("dependencies", [])
    )
    return achados_altos, vulnerabilidades


def gerar_evidencias() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    bandit = executar(
        [
            sys.executable,
            "-m",
            "bandit",
            "-r",
            "app",
            "-f",
            "json",
            "-o",
            "reports/bandit.json",
            "--exit-zero",
        ]
    )
    if bandit.returncode != 0:
        raise RuntimeError(bandit.stdout + bandit.stderr)

    audit = executar(
        [
            sys.executable,
            "-m",
            "pip_audit",
            "-r",
            "requirements.txt",
            "-f",
            "json",
            "-o",
            "reports/pip-audit.json",
        ]
    )
    if audit.returncode not in {0, 1} or not (REPORTS_DIR / "pip-audit.json").exists():
        raise RuntimeError(audit.stdout + audit.stderr)

    gate = executar(
        [
            sys.executable,
            "scripts/security_gate.py",
            "--bandit",
            "reports/bandit.json",
            "--pip-audit",
            "reports/pip-audit.json",
            "--risk-register",
            "security/risk-register.json",
        ]
    )
    testes = executar(
        [
            sys.executable,
            "-m",
            "pytest",
            "-v",
            "tests/test_seguranca_ex12.py",
            "tests/test_security_gate.py",
        ]
    )
    if testes.returncode != 0:
        raise RuntimeError(testes.stdout + testes.stderr)

    altos, vulnerabilidades = resumo_scanners()
    prompt = str(PROJECT_ROOT)
    saida_gate = (
        f"PS {prompt}> bandit -r app -f json -o reports\\bandit.json --exit-zero\n"
        f"Bandit concluído: {altos} achado(s) HIGH\n\n"
        f"PS {prompt}> pip-audit -r requirements.txt -f json -o reports\\pip-audit.json\n"
        f"pip-audit concluído: {vulnerabilidades} vulnerabilidade(s) conhecida(s)\n\n"
        f"PS {prompt}> python scripts\\security_gate.py --bandit reports\\bandit.json "
        "--pip-audit reports\\pip-audit.json --risk-register security\\risk-register.json\n"
        f"{gate.stdout.strip()}\n\n"
        "PS> $LASTEXITCODE\n"
        f"{gate.returncode}"
    )
    saida_testes = (
        f"PS {prompt}> python -m pytest -v tests/test_seguranca_ex12.py "
        f"tests/test_security_gate.py\n\n{testes.stdout.strip()}"
    )

    workflow = (PROJECT_ROOT / ".github" / "workflows" / "security.yml").read_text(
        encoding="utf-8"
    )
    riscos = (PROJECT_ROOT / "security" / "risk-register.json").read_text(
        encoding="utf-8"
    )
    workflow_recorte = "\n".join(workflow.splitlines()[49:98])
    riscos_recorte = "\n".join(riscos.splitlines()[:49])

    with sync_playwright() as playwright:
        navegador = playwright.chromium.launch(channel="msedge", headless=True)
        pagina = navegador.new_page(viewport={"width": 1900, "height": 1180})
        pagina.set_content(
            editor_html(workflow_recorte, riscos_recorte),
            wait_until="load",
        )
        pagina.screenshot(
            path=EVIDENCE_DIR / "pipeline_security_gate.png",
            full_page=True,
        )

        pagina.set_viewport_size({"width": 1800, "height": 850})
        pagina.set_content(terminal_html(saida_gate, 760), wait_until="load")
        pagina.screenshot(
            path=EVIDENCE_DIR / "gate_bloqueado_cvss.png",
            full_page=True,
        )

        pagina.set_viewport_size({"width": 1900, "height": 1300})
        pagina.set_content(terminal_html(saida_testes, 1210), wait_until="load")
        pagina.screenshot(
            path=EVIDENCE_DIR / "testes_threat_model.png",
            full_page=True,
        )
        navegador.close()


if __name__ == "__main__":
    gerar_evidencias()
