import json
import re
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright


BASE_URL = "http://127.0.0.1:8000"
EVIDENCE_DIR = Path(__file__).resolve().parents[1] / "docs" / "ex6"


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


def abrir_para_execucao(operacao) -> None:
    operacao.locator(".opblock-summary").click()
    operacao.get_by_role("button", name="Try it out").click()


def aguardar_status(operacao, status_http: int) -> None:
    status = operacao.locator(
        ".live-responses-table .response-col_status:not(.col_header)"
    )
    expect(status).to_contain_text(str(status_http), timeout=10000)


def gerar_evidencias() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        navegador = playwright.chromium.launch(channel="msedge", headless=True)
        pagina = navegador.new_page(
            viewport={"width": 1440, "height": 1200},
            device_scale_factor=1,
        )
        pagina.goto(f"{BASE_URL}/docs", wait_until="networkidle")

        login = localizar_operacao(pagina, "POST", "/auth/token")
        abrir_para_execucao(login)
        login.locator('input[placeholder="mfa_code"]').fill("")
        login.locator('input[placeholder="grant_type"]').fill("password")
        login.locator('input[placeholder="username"]').fill("admin")
        login.locator('input[placeholder="password"]').fill("Admin@123")

        with pagina.expect_response(lambda resposta: resposta.url.endswith("/auth/token")) as captura:
            login.get_by_role("button", name="Execute").click()
        assert captura.value.status == 403
        aguardar_status(login, 403)
        login.screenshot(path=EVIDENCE_DIR / "mfa_sem_codigo_403.png")

        login.locator('input[placeholder="mfa_code"]').fill("654321")
        with pagina.expect_response(lambda resposta: resposta.url.endswith("/auth/token")) as captura:
            login.get_by_role("button", name="Execute").click()
        assert captura.value.status == 200
        aguardar_status(login, 200)
        login.screenshot(path=EVIDENCE_DIR / "mfa_com_codigo_200.png")

        pagina.locator("button.authorize").first.click()
        dialogo = pagina.locator(".dialog-ux")
        dialogo.locator("input").nth(0).fill("profissional7")
        dialogo.locator("input").nth(1).fill("Profissional@123")
        with pagina.expect_response(
            lambda resposta: resposta.url.endswith("/auth/token")
        ) as captura:
            dialogo.locator("button.modal-btn.auth.authorize").click(force=True)
        assert captura.value.status == 200
        expect(dialogo).to_contain_text("Authorized", timeout=10000)
        dialogo.get_by_role("button", name="Close").click()

        rota_admin = localizar_operacao(pagina, "GET", "/admin/usuarios")
        abrir_para_execucao(rota_admin)
        with pagina.expect_response(
            lambda resposta: resposta.url.endswith("/admin/usuarios")
        ) as captura:
            rota_admin.get_by_role("button", name="Execute").click()
        assert captura.value.status == 403
        aguardar_status(rota_admin, 403)
        rota_admin.screenshot(path=EVIDENCE_DIR / "admin_403.png")

        criar_consulta = localizar_operacao(pagina, "POST", "/consultas")
        abrir_para_execucao(criar_consulta)
        payload = {
            "paciente_id": 2,
            "profissional_id": 8,
            "data_hora": "2030-05-21T10:00:00-03:00",
            "motivo": "Tentativa de criar consulta para outro profissional",
            "observacoes": "Teste de ownership",
            "status": "agendada",
        }
        criar_consulta.locator("textarea.body-param__text").fill(
            json.dumps(payload, ensure_ascii=False, indent=2)
        )
        with pagina.expect_response(
            lambda resposta: resposta.url.rstrip("/").endswith("/consultas")
            and resposta.request.method == "POST"
        ) as captura:
            criar_consulta.get_by_role("button", name="Execute").click()
        assert captura.value.status == 403
        aguardar_status(criar_consulta, 403)
        criar_consulta.screenshot(path=EVIDENCE_DIR / "ownership_403.png")

        navegador.close()


if __name__ == "__main__":
    gerar_evidencias()
