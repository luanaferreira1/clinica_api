# Exercício 12 — Pipeline DevSecOps e auditoria automatizada

## 1. Objetivo e resultado

Foi construído um pipeline de segurança em GitHub Actions com testes pytest,
análise estática Bandit, auditoria de dependências pip-audit, análise dinâmica
passiva OWASP ZAP e um security gate próprio. O gate correlaciona os relatórios
automatizados com o registro de riscos do projeto e encerra o job com código 1
quando encontra um bloqueador.

A suíte de autorização foi derivada do threat model do Exercício 4 e ampliada
para cobrir adulteração de papel no JWT, alteração e exclusão de consulta sem
autorização e acesso indevido à agenda interna. A suíte completa passou com 35
testes.

O resultado atual do gate é intencionalmente **BLOQUEADO**. O Exercício 10 foi
adiado e o risco de força bruta no login permanece aberto com CVSS 7,5. Como o
limiar escolhido é CVSS 7,0, aprovar o deploy neste momento contrariaria o
critério definido.

## 2. Fases do SDLC e ferramentas

| Tipo | Ferramenta ou estratégia | Fase escolhida | Justificativa |
|---|---|---|---|
| SAST | Bandit | Codificação local e validação de pull request | Analisa o código sem executar a aplicação e devolve feedback antes do merge, quando a correção custa menos |
| SCA | pip-audit | Seleção/atualização de dependências, todo push e pull request | Uma dependência segura hoje pode receber um advisory depois; por isso a verificação deve ser repetida continuamente |
| IAST | Instrumentação futura em ambiente de integração | Testes de integração autenticados e staging | Precisa observar a aplicação em execução e associar requisições a caminhos internos; deve atuar com cenários reais de papéis e ownership |
| DAST | OWASP ZAP Baseline | Após iniciar a aplicação efêmera no CI e antes de liberar deploy | Avalia a superfície HTTP em execução sem depender do código-fonte; o baseline usa spider e análise passiva |

O pipeline implementa SAST, SCA e DAST. IAST foi posicionado formalmente no
staging, mas não foi simulado com um produto proprietário ou agente artificial.
Os testes de integração pytest já fornecem os fluxos autenticados que poderão
alimentar essa instrumentação quando ela for adotada.

## 3. Priorização CVSS e impacto de negócio

Foi adotado CVSS v3.1 porque o registro histórico do Assessment já utiliza esse
modelo. O score técnico não foi usado isoladamente: o impacto sobre dados de
saúde, operação clínica e LGPD foi registrado separadamente.

| Prioridade | ID e vulnerabilidade | CVSS v3.1 | Severidade | Impacto de negócio | Estado |
|---|---|---:|---|---|---|
| 1 | VULN-08-01 — BOLA | 8,1 — `AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N` | Alta | Exposição ou alteração de dados de saúde de outro paciente e impacto regulatório | Mitigada |
| 2 | VULN-08-02 — login sem rate limiting | 7,5 — `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N` | Alta | Força bruta pode comprometer uma conta com acesso a dados clínicos | Aberta, Exercício 10 adiado |
| 3 | THREAT-04-TM05 — mass assignment | 6,5 — `AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:H/A:N` | Média | Alteração de papel, ownership ou campo de auditoria | Mitigada |
| 4 | VULN-08-03 — hardening HTTP ausente | 6,1 — `AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N` | Média | Clickjacking e comportamento inseguro do navegador | Aberta, Exercício 10 adiado |
| 5 | THREAT-04-TM07 — XSS stored | 6,1 — `AV:N/AC:L/PR:L/UI:R/S:C/C:L/I:L/A:N` | Média | Comprometimento da sessão da recepção e ações no navegador interno | Mitigada |
| 6 | VULN-08-04 — logging insuficiente | 5,3 — `AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N` | Média | Dificulta detecção, resposta e comprovação de auditoria | Aberta |

Os vetores, impactos, estados e controles também estão armazenados em
`security/risk-register.json`, permitindo que o pipeline consuma a mesma fonte
utilizada pelo relatório.

## 4. Critério do security gate

O limiar de bloqueio escolhido é **CVSS 7,0**, início da faixa Alta no CVSS
v3.1. A decisão considera que a aplicação processa dados pessoais sensíveis e
que um achado alto não deve depender de uma aprovação informal para chegar ao
deploy.

O pipeline é bloqueado quando ocorre qualquer uma destas condições:

- teste automatizado falha;
- risco conhecido com status `OPEN` possui CVSS maior ou igual a 7,0;
- Bandit informa severidade `HIGH` com confiança `MEDIUM` ou `HIGH`;
- ZAP informa `riskcode` 3, correspondente a risco alto;
- pip-audit encontra vulnerabilidade com CVSS maior ou igual a 7,0;
- pip-audit encontra vulnerabilidade sem severidade disponível, situação tratada
  de forma conservadora até a triagem humana;
- um relatório obrigatório está ausente ou possui JSON inválido.

Achados médios e baixos não são ignorados. Eles permanecem nos artefatos do job
e entram na fila de correção, mas não impedem merge automaticamente. Essa
separação reduz bloqueios por findings de baixo impacto sem relaxar a proteção
dos dados clínicos.

## 5. Pipeline GitHub Actions

O arquivo `.github/workflows/security.yml` executa, em ordem:

1. checkout com credenciais não persistidas;
2. preparação do Python e cache de dependências;
3. instalação de dependências;
4. suíte pytest e relatório JUnit;
5. SAST com Bandit em JSON;
6. SCA com pip-audit em JSON;
7. inicialização de uma instância efêmera da API;
8. ZAP Baseline com relatório JSON e HTML;
9. aplicação do security gate central;
10. publicação dos relatórios, inclusive quando o gate bloqueia.

O `GITHUB_TOKEN` recebe somente `contents: read`. Os valores JWT e MFA do
workflow são exclusivamente de teste e não correspondem a credenciais de
produção. O job possui timeout e concorrência por branch para evitar execuções
obsoletas em paralelo.

Para impedir efetivamente o merge, o check **Testes e security gate** deve ser
marcado como obrigatório na regra de proteção da branch `main`. O YAML produz o
resultado; a regra do repositório transforma esse resultado em bloqueio de
merge.

## 6. Estratégia de testes derivada do threat model

| Ameaça do Exercício 4 | Vetor testado | Teste rastreável | Resultado seguro |
|---|---|---|---|
| TM-01 — Spoofing | Token válido tem claim `role` adulterado | `test_tm01_token_com_papel_adulterado_e_rejeitado` | HTTP 401 |
| TM-02 — BOLA | Paciente tenta consultar recurso de outro paciente | `test_bola_paciente_nao_acessa_consulta_de_outro_paciente` | HTTP 403 |
| TM-03 — Tampering/EoP | Recepcionista tenta alterar ou excluir consulta | `test_tm03_recepcionista_nao_altera_consulta` e `test_tm03_recepcionista_nao_exclui_consulta` | HTTP 403 e registro preservado |
| TM-05 — Mass assignment | Cliente envia campo interno `papel` | `test_modelo_rejeita_campo_nao_declarado` | HTTP 422 |
| TM-06 — Disclosure | Resposta tenta expor campos internos | `test_response_model_oculta_campos_internos` | Conjunto exato de campos públicos |
| TM-07 — XSS stored | Conteúdo `<script>` é exibido na agenda | `test_agenda_html_aplica_autoescape_contra_xss` | Texto codificado e não executado |
| TM-08 — Agenda sem RBAC | Profissional tenta abrir página exclusiva da recepção | `test_tm08_profissional_nao_acessa_agenda_interna` | HTTP 403 |
| TM-10 — Perda de dados | Nova conexão abre o mesmo banco | `test_consulta_permanece_apos_nova_conexao` | Registro recuperado |

O acesso à agenda foi centralizado em `exigir_acesso_agenda`, permitindo somente
recepcionistas e administradores. A recepção pode visualizar consultas, mas os
testes confirmam que não pode alterar ou excluir os registros.

TM-09 e TM-11 continuam pendentes porque rate limiting e hardening de transporte
pertencem ao Exercício 10, que foi adiado. TM-12 depende do fluxo M2M do
Exercício 7, também adiado. Esses itens permanecem visíveis, em vez de serem
declarados falsamente como resolvidos.

## 7. Resultados locais

- pytest: 35 testes aprovados;
- Bandit: um finding baixo B105, confiança média;
- triagem B105: falso positivo em `token_type="access"`, que descreve o tipo do
  JWT e não contém senha, segredo ou token utilizável;
- pip-audit: nenhuma vulnerabilidade conhecida na data da execução;
- security gate: bloqueado por `VULN-08-02`, CVSS 7,5 e status aberto.

O resultado do pip-audit é temporal. Uma execução futura pode detectar um novo
advisory mesmo sem alteração no projeto, justificando sua presença em todo push
e pull request.

## 8. Manual de execução e resultados esperados

### 8.1 Preparar o ambiente

No PowerShell, a partir da raiz do projeto:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
New-Item -ItemType Directory -Force -Path reports
```

### 8.2 Executar os testes de segurança

Para executar somente as ampliações do Exercício 12:

```powershell
python -m pytest -v tests/test_seguranca_ex12.py tests/test_security_gate.py
```

Resultado esperado:

```text
10 passed
```

Para executar toda a suíte:

```powershell
python -m pytest -v
```

Resultado esperado:

```text
35 passed
```

### 8.3 Executar o SAST manualmente

```powershell
bandit -r app -f json -o reports/bandit.json --exit-zero
```

Para conferir o resumo:

```powershell
$bandit = Get-Content reports/bandit.json -Raw | ConvertFrom-Json
$bandit.results | Select-Object test_id, issue_severity, issue_confidence, filename, line_number
```

Resultado esperado nesta versão: B105 com severidade `LOW` em
`app/auth/security.py`, sem finding `HIGH`. O achado é preservado para triagem e
não bloqueia o gate.

### 8.4 Executar o SCA manualmente

```powershell
pip-audit -r requirements.txt -f json -o reports/pip-audit.json
```

Resultado observado na validação:

```text
No known vulnerabilities found
```

Como a base de advisories muda, um resultado diferente no futuro deve ser
investigado, não apagado ou forçado a passar.

### 8.5 Executar o gate manualmente

```powershell
python scripts/security_gate.py `
    --bandit reports/bandit.json `
    --pip-audit reports/pip-audit.json `
    --risk-register security/risk-register.json

$LASTEXITCODE
```

Resultado correto enquanto o Exercício 10 estiver pendente:

```text
Critério: bloquear CVSS >= 7.0, Bandit HIGH e ZAP HIGH
DAST ZAP: relatório não informado nesta execução local
SECURITY GATE: BLOQUEADO
- Risco VULN-08-02: Login sem rate limiting com CVSS 7.5 permanece aberto
1
```

O código de saída 1 é a evidência de que o gate realmente interrompe a etapa.
Não altere o risco para `MITIGATED` apenas para obter uma tela verde; essa
mudança só deve ocorrer quando o Exercício 10 implementar e testar o controle.

### 8.6 Executar o ZAP do pipeline manualmente

Este passo exige Docker Desktop. No primeiro PowerShell:

```powershell
$env:APP_ENV="test"
$env:DATABASE_URL="sqlite:///./zap-ex12.db"
$env:DATABASE_ECHO="false"
$env:JWT_SECRET_KEY="chave-local-zap-com-mais-de-32-caracteres"
$env:ADMIN_MFA_CODE="654321"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Mantenha o servidor aberto. No segundo PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path reports
docker run --rm `
    -v "${PWD}\reports:/zap/wrk/:rw" `
    ghcr.io/zaproxy/zaproxy:stable `
    zap-baseline.py `
    -t http://host.docker.internal:8000 `
    -J zap-report.json `
    -r zap-report.html `
    -I `
    -m 1
```

Resultados esperados: `reports/zap-report.json` e
`reports/zap-report.html`. O baseline pode registrar avisos de hardening porque
o Exercício 10 ainda não foi realizado.

Execute novamente o gate incluindo o relatório:

```powershell
python scripts/security_gate.py `
    --bandit reports/bandit.json `
    --pip-audit reports/pip-audit.json `
    --zap reports/zap-report.json `
    --risk-register security/risk-register.json
```

O resultado continua bloqueado enquanto existir o risco alto de autenticação.

### 8.7 Executar no GitHub Actions

1. Envie o projeto para um repositório GitHub sem `.env`, banco ou credenciais
   reais.
2. Abra a aba **Actions**.
3. Selecione **Security Pipeline**.
4. Clique em **Run workflow** ou abra um pull request para `main`.
5. Abra o job **Testes e security gate**.
6. Confirme os testes, Bandit, pip-audit, ZAP e a etapa final do gate.
7. Baixe o artefato `security-reports` para preservar os JSONs, o HTML do ZAP e
   o JUnit.

Estado esperado nesta fase: a etapa do gate fica vermelha e informa
`VULN-08-02`. Isso demonstra que o pipeline impede a liberação acima do limiar.

Para impedir o merge de fato, abra as configurações do repositório, crie uma
regra para `main`, habilite a exigência de status checks e selecione o check
**Testes e security gate**. Depois disso, um pull request não poderá ser
mesclado enquanto o job estiver bloqueado.

### 8.8 Gerar as evidências principais com Playwright

```powershell
python scripts/gerar_evidencias_ex12.py
```

O gerador executa os testes específicos, lê os relatórios reais e produz três
imagens em `docs/ex12/`. A porta da aplicação não é necessária para essas três
evidências; o ZAP permanece demonstrado no workflow e no procedimento manual.

## 9. Evidências principais e legendas

1. **Foto:** `pipeline_security_gate.png`  
   **Legenda:** Figura — Pipeline DevSecOps e critério de severidade: o workflow
   executa testes, Bandit, pip-audit e OWASP ZAP antes de aplicar o gate, enquanto
   o registro de riscos define CVSS 7,0 como limiar de bloqueio.

2. **Foto:** `gate_bloqueado_cvss.png`  
   **Legenda:** Figura — Security gate funcionando: os scanners locais não
   apresentam achado alto, mas a liberação termina com código 1 porque o risco
   de login sem rate limiting permanece aberto com CVSS 7,5 após o adiamento do
   Exercício 10.

3. **Foto:** `testes_threat_model.png`  
   **Legenda:** Figura — Testes de segurança rastreáveis ao threat model: os
   cenários de adulteração de JWT, alteração e exclusão sem autorização, RBAC da
   agenda e comportamento do próprio gate são aprovados pelo pytest.

As três imagens representam as partes principais exigidas: construção do
pipeline, priorização e bloqueio por severidade e expansão rastreável dos testes.

## 10. Riscos residuais e decisão de liberação

O deploy permanece bloqueado. O risco alto de força bruta não foi aceito, pois
o comprometimento de uma conta pode expor dados de saúde. A ausência de headers
e o logging insuficiente também permanecem registrados, embora estejam abaixo
do limiar automático atual.

O fluxo M2M do Exercício 7 e os controles do Exercício 10 devem ser concluídos
antes da auditoria final. Após o rate limiting ser implementado e testado, o
status de VULN-08-02 poderá ser alterado para `MITIGATED`, permitindo nova
avaliação pelo mesmo gate.

## 11. Referências técnicas

- [FIRST — CVSS v3.1 Specification](https://www.first.org/cvss/v3-1/specification-document)
- [NIST SP 800-218 — Secure Software Development Framework](https://csrc.nist.gov/pubs/sp/800/218/final)
- [PyCQA Bandit](https://github.com/PyCQA/bandit)
- [PyPA pip-audit](https://github.com/pypa/pip-audit)
- [OWASP ZAP Baseline Scan](https://www.zaproxy.org/docs/docker/baseline-scan/)
- [GitHub Actions — Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)

## 🎥 Roteiro para o vídeo — Exercício 12

- Explicar onde SAST, SCA, IAST e DAST entram no SDLC e mostrar o workflow.
- Justificar CVSS 7,0 como limiar e demonstrar o bloqueio atual do gate.

Texto sugerido:

> Neste exercício eu construí um pipeline DevSecOps com testes pytest, análise
> estática pelo Bandit, auditoria de dependências pelo pip-audit e análise
> dinâmica passiva pelo OWASP ZAP. O SAST e o SCA atuam antes do merge, o DAST
> atua contra uma instância efêmera antes do deploy e o IAST foi posicionado nos
> testes de integração e no staging, onde pode observar os fluxos autenticados.
> Para o security gate eu defini o limiar CVSS 7,0, que corresponde ao início da
> severidade alta. Achados abaixo disso continuam registrados, mas riscos altos
> ou críticos impedem a liberação. Como o Exercício 10 foi adiado, o login ainda
> não possui rate limiting e esse risco permanece aberto com CVSS 7,5. Por isso,
> o gate termina com código 1 e bloqueia corretamente o deploy. Também ampliei
> os testes a partir do threat model, cobrindo adulteração de papel no JWT,
> alteração e exclusão sem autorização e acesso indevido à agenda interna. A
> suíte completa terminou com 35 testes aprovados.
