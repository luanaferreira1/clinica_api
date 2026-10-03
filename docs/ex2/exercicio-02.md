# Exercício 2

## Resultado

O modelo persistido `ConsultaInternal` contém `criado_em`, `atualizado_em` e
`auditoria_id`, necessários para controles internos. As rotas, porém, declaram
`ConsultaPublic` em `response_model`. Esse contrato enumera somente os sete
campos autorizados e faz o FastAPI filtrar qualquer metadado adicional antes da
serialização JSON.

A página `/agenda` usa Jinja2 com herança: `agenda.html` estende `base.html`. O
autoescape foi habilitado explicitamente para HTML e XML em uma configuração
centralizada. Nenhum valor recebido do usuário usa o filtro `safe`; portanto,
tags como `<script>` são apresentadas como texto e não executadas pelo navegador.

Sem `response_model`, uma rota que retornasse diretamente o registro persistido
poderia incluir identificadores de auditoria, horários internos e futuramente
outros dados operacionais ou pessoais. Isso aumentaria a exposição de dados e
facilitaria correlação, enumeração de registros e reconhecimento da estrutura
interna da aplicação.

## Contrato público de consultas

Somente estes campos são expostos:

- `id`
- `paciente_id`
- `profissional_id`
- `data_hora`
- `motivo`
- `observacoes`
- `status`

Os campos `auditoria_id`, `criado_em` e `atualizado_em` permanecem apenas na
camada interna.
