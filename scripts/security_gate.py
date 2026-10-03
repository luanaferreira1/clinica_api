import argparse
import json
import sys
from pathlib import Path
from typing import Any


def carregar_json(caminho: Path) -> dict[str, Any]:
    with caminho.open(encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
    if not isinstance(dados, dict):
        raise ValueError(f"Formato JSON inválido em {caminho}")
    return dados


def bloqueios_bandit(dados: dict[str, Any]) -> list[str]:
    bloqueios = []
    for resultado in dados.get("results", []):
        severidade = str(resultado.get("issue_severity", "UNKNOWN")).upper()
        confianca = str(resultado.get("issue_confidence", "UNKNOWN")).upper()
        if severidade == "HIGH" and confianca in {"MEDIUM", "HIGH"}:
            bloqueios.append(
                f"Bandit {resultado.get('test_id', 'sem-id')} em "
                f"{resultado.get('filename', 'arquivo desconhecido')}: "
                f"severidade {severidade}, confiança {confianca}"
            )
    return bloqueios


def nivel_cvss(vulnerabilidade: dict[str, Any]) -> float | None:
    campos = (
        vulnerabilidade.get("cvss"),
        vulnerabilidade.get("score"),
        vulnerabilidade.get("cvss_score"),
    )
    for valor in campos:
        try:
            return float(valor)
        except (TypeError, ValueError):
            continue
    return None


def bloqueios_dependencias(
    dados: dict[str, Any],
    limiar: float,
    bloquear_desconhecida: bool,
) -> list[str]:
    bloqueios = []
    for dependencia in dados.get("dependencies", []):
        nome = dependencia.get("name", "dependência desconhecida")
        versao = dependencia.get("version", "versão desconhecida")
        for vulnerabilidade in dependencia.get("vulns", []):
            identificador = vulnerabilidade.get("id", "sem-id")
            pontuacao = nivel_cvss(vulnerabilidade)
            if pontuacao is None and bloquear_desconhecida:
                bloqueios.append(
                    f"Dependência {nome} {versao}, {identificador}: "
                    "severidade não informada, bloqueada por precaução"
                )
            elif pontuacao is not None and pontuacao >= limiar:
                bloqueios.append(
                    f"Dependência {nome} {versao}, {identificador}: CVSS {pontuacao:.1f}"
                )
    return bloqueios


def bloqueios_zap(dados: dict[str, Any]) -> list[str]:
    bloqueios = []
    for site in dados.get("site", []):
        for alerta in site.get("alerts", []):
            try:
                codigo_risco = int(alerta.get("riskcode", 0))
            except (TypeError, ValueError):
                codigo_risco = 0
            if codigo_risco >= 3:
                bloqueios.append(
                    f"ZAP {alerta.get('pluginid', 'sem-id')}: "
                    f"{alerta.get('alert', 'alerta de severidade alta')}"
                )
    return bloqueios


def bloqueios_riscos(dados: dict[str, Any], limiar: float) -> list[str]:
    bloqueios = []
    for risco in dados.get("risks", []):
        status = str(risco.get("status", "OPEN")).upper()
        pontuacao = float(risco.get("cvss", 0))
        if status == "OPEN" and pontuacao >= limiar:
            bloqueios.append(
                f"Risco {risco.get('id', 'sem-id')}: {risco.get('title', 'sem título')} "
                f"com CVSS {pontuacao:.1f} permanece aberto"
            )
    return bloqueios


def avaliar_gate(
    bandit: dict[str, Any],
    dependencias: dict[str, Any],
    riscos: dict[str, Any],
    zap: dict[str, Any] | None = None,
) -> tuple[float, list[str]]:
    limiar = float(riscos.get("blocking_threshold", 7.0))
    bloquear_desconhecida = bool(
        riscos.get("unknown_dependency_severity_blocks", True)
    )
    bloqueios = bloqueios_bandit(bandit)
    bloqueios.extend(
        bloqueios_dependencias(dependencias, limiar, bloquear_desconhecida)
    )
    if zap is not None:
        bloqueios.extend(bloqueios_zap(zap))
    bloqueios.extend(bloqueios_riscos(riscos, limiar))
    return limiar, bloqueios


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bandit", type=Path, required=True)
    parser.add_argument("--pip-audit", type=Path, required=True)
    parser.add_argument("--risk-register", type=Path, required=True)
    parser.add_argument("--zap", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    argumentos = criar_parser().parse_args(argv)
    try:
        bandit = carregar_json(argumentos.bandit)
        dependencias = carregar_json(argumentos.pip_audit)
        riscos = carregar_json(argumentos.risk_register)
        zap = carregar_json(argumentos.zap) if argumentos.zap else None
        limiar, bloqueios = avaliar_gate(bandit, dependencias, riscos, zap)
    except (OSError, ValueError, json.JSONDecodeError) as erro:
        print(f"SECURITY GATE: ERRO\n{erro}")
        return 2

    print(f"Critério: bloquear CVSS >= {limiar:.1f}, Bandit HIGH e ZAP HIGH")
    if zap is None:
        print("DAST ZAP: relatório não informado nesta execução local")
    if bloqueios:
        print("SECURITY GATE: BLOQUEADO")
        for bloqueio in bloqueios:
            print(f"- {bloqueio}")
        return 1

    print("SECURITY GATE: APROVADO")
    print("Nenhum achado acima do critério de bloqueio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
