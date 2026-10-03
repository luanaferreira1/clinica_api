# Exercício 9

## 1. Objetivo e resultado

As vulnerabilidades de entrada, saída e autorização foram tratadas de forma
centralizada. O ataque BOLA reproduzido no Exercício 8 deixou de retornar dados
de outro paciente: a mesma requisição agora recebe HTTP 403.

Também foi identificado um segundo endpoint com o mesmo padrão. Em
`GET /consultas`, a função de filtragem anterior tratava somente profissionais;
qualquer outro papel, inclusive paciente, recebia a lista completa. A filtragem
central agora restringe pacientes pelo `paciente_id`. Como `/agenda` utiliza a
mesma função, a correção também protege a página HTML sem duplicar regras.

Foram aplicados os seguintes controles:

- validação de ownership centralizada na camada de autenticação;
- JWT validado em uma única dependência `obter_usuario_atual`;
- dependências reutilizáveis para leitura e gerenciamento de consultas;
- whitelist para o status por meio de `Literal`;
- regex positiva para motivo e termo de busca;
- modelos Pydantic com `extra="forbid"`;
- rejeição de payloads semelhantes a SQL injection antes da camada de dados;
- autoescape explícito do Jinja2 para conteúdo armazenado e exibido em HTML.

## 2. Correção centralizada da BOLA

### 2.1 Estado anterior

No Exercício 8, o usuário `paciente1`, vinculado ao `patient_id: 1`, alterava o
ID da URL e obtinha a consulta do `paciente_id: 2` com HTTP 200. O endpoint
validava somente o papel do usuário.

### 2.2 Estado corrigido

A função `autorizar_consulta` recebe o usuário, o objeto carregado e a operação.
Para pacientes, a leitura somente é autorizada quando:

```text
usuario.paciente_id == consulta.paciente_id
```

As dependências `obter_consulta_para_leitura` e
`obter_consulta_para_gerenciamento` executam, em um único local:

1. a validação do JWT por `obter_usuario_atual`;
2. a obtenção do recurso solicitado;
3. o retorno 404 quando o recurso não existe;
4. a verificação de papel e ownership;
5. o retorno 403 quando o usuário não possui permissão.

O endpoint de prontuário não implementa sua própria comparação de IDs: ele usa
a dependência central. Isso evita que novos endpoints esqueçam a autorização no
nível do objeto.

### 2.3 Resultado do mesmo ataque

```http
GET /pacientes/consultas/1
Authorization: Bearer <token-do-paciente-1>
```

Resultado anterior:

```http
HTTP/1.1 200 OK
```

Resultado após a correção:

```http
HTTP/1.1 403 Forbidden
```

```json
{
  "detail": "Usuário sem permissão sobre esta consulta"
}
```

## 3. Endpoint adicional com o mesmo padrão

O endpoint `GET /consultas` não foi citado no Exercício 8. A implementação
anterior filtrava pelo `profissional_id` apenas quando o papel era
`profissional` e retornava todas as consultas para os demais papéis. Portanto,
um paciente autenticado conseguia listar registros de outros pacientes.

A função `filtrar_consultas_visiveis` agora aplica estas regras:

| Papel         | Resultado da listagem                                         |
| ------------- | ------------------------------------------------------------- |
| Paciente      | Somente consultas cujo `paciente_id` corresponde ao token     |
| Profissional  | Somente consultas cujo `profissional_id` corresponde ao token |
| Recepcionista | Todas, conforme a função operacional definida                 |
| Administrador | Todas, conforme a função administrativa definida              |

Com consultas dos pacientes 1 e 2 armazenadas, `paciente1` recebe somente o
registro cujo `paciente_id` é 1. A página `/agenda` herda a mesma proteção.

## 4. Validação por whitelist e regex

O campo `status` utiliza a whitelist:

```text
agendada, confirmada, cancelada, concluida
```

Qualquer outro valor recebe HTTP 422. Os campos `motivo` e `busca` usam uma
expressão regular positiva: somente letras, caracteres latinos acentuados,
números, espaços e um conjunto reduzido de pontuação são aceitos. Símbolos
típicos de manipulação de comandos, como `;` e `=`, ficam fora da whitelist.

O filtro de consultas foi modelado com `ConsultaFiltros`, também derivado de
`ModeloEstrito`. Assim, parâmetros desconhecidos não são ignorados.

## 5. Rejeição de campos não declarados

Todos os modelos de entrada herdam de `ModeloEstrito`, cuja configuração é:

```python
model_config = ConfigDict(extra="forbid")
```

Um cliente não pode acrescentar campos como `papel`, `administrador` ou
`auditoria_id` esperando que sejam processados silenciosamente. O Pydantic
retorna HTTP 422 com o tipo `extra_forbidden`.

Essa proteção reduz riscos de mass assignment e impede que mudanças futuras no
repositório transformem propriedades inesperadas em atributos persistidos.

## 6. Prevenção de SQL injection

A persistência desta etapa ainda é em memória e, portanto, não executa SQL. A
proteção foi aplicada na fronteira que futuramente alimentará a consulta ao
banco:

- `status` aceita somente valores da whitelist;
- `busca` deve corresponder à regex positiva;
- campos extras são rejeitados;
- o código de filtragem compara valores, sem interpretar expressões recebidas.

Os payloads `agendada' OR 1=1--` e `'; DROP TABLE consultas;--` recebem HTTP
422 antes de alcançar o repositório. No Exercício 11, a migração para SQLModel
deverá manter essa validação e usar exclusivamente queries parametrizadas. A
validação não será tratada como substituta da parametrização.

## 7. Correção de XSS stored

O campo `observacoes` pode conter texto livre e é armazenado sem transformar seu
significado. A proteção ocorre na saída: o ambiente Jinja2 usa
`select_autoescape` para HTML e XML, e o template imprime valores com a sintaxe
normal `{{ ... }}`.

Ao armazenar:

```html
<script>
  alert("XSS");
</script>
```

o HTML enviado contém:

```html
&lt;script&gt;alert(&#34;XSS&#34;)&lt;/script&gt;
```

O navegador mostra o conteúdo como texto e não executa JavaScript. A aplicação
não usa `|safe`, concatenação de HTML ou desativação local do autoescape.

## 8. Rastreabilidade das correções

| Controle                     | Implementação                                        | Teste associado                                               |
| ---------------------------- | ---------------------------------------------------- | ------------------------------------------------------------- |
| Ownership do prontuário      | `autorizar_consulta` e `obter_consulta_para_leitura` | `test_bola_paciente_nao_acessa_consulta_de_outro_paciente`    |
| Endpoint adicional protegido | `filtrar_consultas_visiveis`                         | `test_endpoint_adicional_lista_somente_consultas_do_paciente` |
| Whitelist                    | `StatusConsulta` com `Literal`                       | `test_status_aplica_whitelist_e_rejeita_sql_injection`        |
| Regex positiva               | `PadraoTextoClinico` e `TextoBusca`                  | `test_busca_aplica_regex_e_rejeita_sql_injection`             |
| Campos extras                | `ConfigDict(extra="forbid")`                         | `test_modelo_rejeita_campo_nao_declarado`                     |
| Output encoding              | Jinja2 com `select_autoescape`                       | `test_agenda_html_aplica_autoescape_contra_xss`               |
