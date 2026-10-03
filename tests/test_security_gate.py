from scripts.security_gate import avaliar_gate


RELATORIO_LIMPO = {"results": []}
DEPENDENCIAS_LIMPAS = {"dependencies": []}
ZAP_LIMPO = {"site": []}


def registro(status: str = "MITIGATED") -> dict[str, object]:
    return {
        "blocking_threshold": 7.0,
        "unknown_dependency_severity_blocks": True,
        "risks": [
            {
                "id": "TESTE-01",
                "title": "Risco de teste",
                "cvss": 8.1,
                "status": status,
            }
        ],
    }


def test_gate_aprova_relatorios_sem_achados_bloqueadores() -> None:
    limiar, bloqueios = avaliar_gate(
        RELATORIO_LIMPO,
        DEPENDENCIAS_LIMPAS,
        registro(),
        ZAP_LIMPO,
    )

    assert limiar == 7.0
    assert bloqueios == []


def test_gate_bloqueia_achado_bandit_alto() -> None:
    bandit = {
        "results": [
            {
                "test_id": "B999",
                "filename": "app/exemplo.py",
                "issue_severity": "HIGH",
                "issue_confidence": "HIGH",
            }
        ]
    }

    _, bloqueios = avaliar_gate(
        bandit,
        DEPENDENCIAS_LIMPAS,
        registro(),
        ZAP_LIMPO,
    )

    assert len(bloqueios) == 1
    assert "Bandit B999" in bloqueios[0]


def test_gate_bloqueia_dependencia_sem_severidade_publicada() -> None:
    dependencias = {
        "dependencies": [
            {
                "name": "pacote-exemplo",
                "version": "1.0.0",
                "vulns": [{"id": "PYSEC-TESTE"}],
            }
        ]
    }

    _, bloqueios = avaliar_gate(
        RELATORIO_LIMPO,
        dependencias,
        registro(),
        ZAP_LIMPO,
    )

    assert len(bloqueios) == 1
    assert "bloqueada por precaução" in bloqueios[0]


def test_gate_bloqueia_alerta_zap_alto() -> None:
    zap = {
        "site": [
            {
                "alerts": [
                    {
                        "pluginid": "40018",
                        "alert": "SQL Injection",
                        "riskcode": "3",
                    }
                ]
            }
        ]
    }

    _, bloqueios = avaliar_gate(
        RELATORIO_LIMPO,
        DEPENDENCIAS_LIMPAS,
        registro(),
        zap,
    )

    assert len(bloqueios) == 1
    assert "ZAP 40018" in bloqueios[0]


def test_gate_bloqueia_risco_conhecido_alto_e_aberto() -> None:
    _, bloqueios = avaliar_gate(
        RELATORIO_LIMPO,
        DEPENDENCIAS_LIMPAS,
        registro("OPEN"),
        ZAP_LIMPO,
    )

    assert len(bloqueios) == 1
    assert "CVSS 8.1 permanece aberto" in bloqueios[0]
