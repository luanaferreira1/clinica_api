# Exercício 8

## 1. Objetivo e método

Foi realizada uma revisão manual do código-fonte da API, sem uso de scanner
automatizado, buscando falhas que dependem do contexto de negócio. A revisão
considerou os endpoints, a autenticação, os controles de autorização e a
configuração HTTP existentes ao final do Exercício 6.

Para reproduzir exatamente o cenário proposto no enunciado, foram incluídas
duas identidades demonstrativas de pacientes e o endpoint
`GET /pacientes/consultas/{consulta_id}`. Este endpoint representa o estado
vulnerável anterior à correção: exige autenticação e confirma o papel de
paciente, mas não confirma se a consulta solicitada pertence ao paciente do
token. Essa implementação é intencionalmente insegura, existe somente para a
análise e para a evidência de antes e depois, e não está autorizada para
produção.

As categorias são apresentadas tanto no OWASP API Security Top 10:2023, quando
há correspondência específica para APIs, quanto no OWASP Top 10:2025.

## 2. Resumo dos achados

| ID         | Padrão vulnerável                                | Categoria OWASP                                                              | Evidência no código                                                                                                               | Severidade preliminar |
| ---------- | ------------------------------------------------ | ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| VULN-08-01 | BOLA no prontuário de consulta                   | API1:2023 Broken Object Level Authorization / A01:2025 Broken Access Control | `app/routes/prontuarios.py` autentica o paciente, busca pelo identificador fornecido e retorna o objeto sem verificar o ownership | Crítica               |
| VULN-08-02 | Login sem rate limiting ou bloqueio progressivo  | API2:2023 Broken Authentication / A07:2025 Authentication Failures           | `POST /auth/token` aceita tentativas consecutivas e nunca retorna 429                                                             | Alta                  |
| VULN-08-03 | Ausência de hardening HTTP                       | API8:2023 Security Misconfiguration / A02:2025 Security Misconfiguration     | `app/main.py` não configura CORS explícito nem HSTS, X-Frame-Options e X-Content-Type-Options                                     | Média                 |
| VULN-08-04 | Ausência de log e alerta de eventos de segurança | A09:2025 Security Logging and Alerting Failures                              | logins inválidos, negativas de autorização e acessos administrativos não produzem eventos estruturados de auditoria               | Média-alta            |

Os quatro itens pertencem a categorias diferentes. Os três primeiros satisfazem
o mínimo solicitado, e o quarto foi mantido porque afeta a capacidade de
detectar e investigar a exploração dos demais.

## 3. VULN-08-01 — BOLA no acesso ao prontuário

### 3.1 Padrão identificado

O JWT do paciente contém o claim `patient_id`. Entretanto, o endpoint vulnerável
executa apenas estas decisões:

1. confirma que existe um usuário autenticado;
2. confirma que o papel é `paciente`;
3. busca a consulta usando o `consulta_id` recebido na URL;
4. retorna a consulta encontrada.

Não existe comparação entre `usuario.paciente_id` e
`consulta.paciente_id`. Portanto, a autenticação é válida, mas a autorização no
nível do objeto está ausente.

```python
@router.get("/{consulta_id}", response_model=ConsultaPublic)
def obter_prontuario_consulta(
    consulta_id: ConsultaId,
    usuario: Annotated[UsuarioInternal, Depends(obter_usuario_atual)],
) -> ConsultaInternal:
    if usuario.papel != "paciente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a pacientes",
        )
    consulta = consulta_repository.obter(consulta_id)
    if consulta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consulta não encontrada",
        )
    return consulta
```

### 3.2 Exploração reproduzida

Uma consulta pertencente ao `paciente_id: 2` é criada. Em seguida, o usuário
`paciente1`, cujo token contém `patient_id: 1`, altera apenas o identificador na
URL e chama:

```http
GET /pacientes/consultas/1
Authorization: Bearer <token-do-paciente-1>
```

Resposta observada no estado vulnerável:

```http
HTTP/1.1 200 OK
```

```json
{
  "id": 1,
  "paciente_id": 2,
  "profissional_id": 8,
  "data_hora": "2030-06-12T09:00:00-03:00",
  "motivo": "Acompanhamento cardiológico",
  "observacoes": "Paciente relata histórico familiar de hipertensão.",
  "status": "agendada"
}
```

O HTTP 200 comprova a falha: o paciente autenticado recebe dados de saúde de
outra pessoa. Um scanner pode reconhecer que o endpoint possui autenticação,
mas não conhece a relação de negócio entre o paciente do token e o objeto;
por isso, a leitura manual e o teste contextual são necessários.

### 3.3 Impacto e correção planejada

O impacto é crítico porque há violação direta de confidencialidade de dados de
saúde, com risco regulatório sob a LGPD, dano ao paciente e acesso em escala por
enumeração de IDs. A correção do Exercício 9 deverá centralizar a verificação de
ownership e impedir o retorno quando `patient_id != paciente_id`, com teste
negativo esperando HTTP 403.

## 4. VULN-08-02 — autenticação sem proteção contra força bruta

O endpoint `POST /auth/token` valida as credenciais, porém não possui limite por
IP ou conta, atraso progressivo, bloqueio temporário ou resposta HTTP 429. Seis
tentativas consecutivas com senhas incorretas são processadas normalmente e
todas retornam 401.

Esse comportamento permite força bruta e credential stuffing. O bcrypt aumenta
o custo de cada tentativa, mas não limita a quantidade de requisições recebidas.
O risco é alto porque o comprometimento de uma conta permite acesso a dados
clínicos. O Exercício 10 deverá aplicar rate limiting mais restritivo ao login,
preferencialmente combinando origem e identidade, sem bloquear indefinidamente
uma conta por ação de terceiros.

## 5. VULN-08-03 — configuração HTTP insegura

A criação da aplicação em `app/main.py` não instala middleware de CORS com
allowlist e não adiciona os cabeçalhos `Strict-Transport-Security`,
`X-Frame-Options` e `X-Content-Type-Options`. A execução local também utiliza
HTTP direto.

Consequências possíveis:

- política de origem indefinida para os clientes web;
- ausência de orientação ao navegador para manter HTTPS;
- possibilidade de incorporação da interface em frame;
- MIME sniffing sem bloqueio explícito.

Este achado é classificado como médio no ambiente de desenvolvimento, mas sua
severidade aumentaria se a mesma configuração fosse publicada. O Exercício 10
deverá implementar a allowlist CORS e os cabeçalhos de hardening; TLS deverá ser
terminado na infraestrutura de produção.

## 6. VULN-08-04 — falhas de logging e alertas

A API depende apenas do access log básico do servidor. Não são registrados como
eventos estruturados o usuário, o resultado, o tipo de operação, o recurso, a
origem e um identificador de correlação para:

- tentativas de login inválidas;
- falhas de MFA;
- negativas por papel ou ownership;
- acesso a rotas administrativas;
- sequência anormal de IDs compatível com exploração de BOLA.

O campo `auditoria_id` da consulta identifica um registro, mas não substitui um
log de auditoria imutável. Sem esses eventos, a clínica pode não detectar o
ataque ou não conseguir reconstruí-lo. A correção futura deve usar logging
centralizado sem gravar senhas, tokens ou dados clínicos completos, além de
alertas para padrões anormais.

## 7. Padrões avaliados que não foram classificados como vulneráveis

A revisão não classificou SQL injection, mass assignment ou XSS stored como
falhas atuais. A persistência ainda é em memória e não executa SQL; os modelos
Pydantic usam `extra="forbid"`; e o Jinja2 foi configurado com autoescape. Essa
distinção evita atribuir categorias apenas para completar quantidade e mantém o
relatório vinculado ao código realmente observado.

## 8. Priorização e decisão de liberação

| Prioridade | Achado                            | Justificativa de negócio                                                                 |
| ---------- | --------------------------------- | ---------------------------------------------------------------------------------------- |
| 1          | VULN-08-01 — BOLA                 | Expõe diretamente dados de saúde de outro paciente e pode ser explorada alterando um ID  |
| 2          | VULN-08-02 — força bruta          | Pode levar ao comprometimento de contas e ampliar o acesso aos dados clínicos            |
| 3          | VULN-08-04 — logging insuficiente | Reduz detecção, resposta a incidentes e rastreabilidade regulatória                      |
| 4          | VULN-08-03 — hardening HTTP       | Aumenta a superfície de ataque quando a aplicação é exposta em navegador ou rede externa |

Decisão: **o deploy deve permanecer bloqueado**. A BOLA é uma falha explorável
de controle de acesso com exposição comprovada de dados pessoais sensíveis.
Este exercício apenas identifica e reproduz as falhas; as mudanças defensivas
serão rastreadas nos exercícios seguintes.
