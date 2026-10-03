# Exercício 11

## 1. Objetivo e resultado

A persistência em memória foi substituída por um banco relacional acessado com
SQLModel. Consultas e usuários passaram a ser representados por tabelas, e as
operações de criação, leitura, atualização, exclusão e filtragem utilizam uma
sessão de banco recebida por injeção de dependência do FastAPI.

A configuração deixou de depender de valores sensíveis escritos no código. A
URL do banco, a chave JWT e o código de MFA são carregados por `BaseSettings` a
partir de variáveis de ambiente ou de um arquivo `.env` local. Somente o
`.env.example`, sem credenciais utilizáveis, integra a entrega.

O resultado foi validado por três testes específicos:

- permanência de uma consulta após o encerramento da conexão inicial e abertura
  de uma nova conexão com o mesmo banco;
- inspeção do SQL executado para confirmar o uso de parâmetro vinculado;
- carregamento das configurações por um arquivo `.env` temporário e ocultação
  do segredo por `SecretStr`.

Ao final, a suíte completa possui 25 testes aprovados.

## 2. Organização da camada de persistência

Os componentes foram separados para evitar que detalhes de banco se espalhem
pelas rotas:

| Componente                  | Responsabilidade                                                     |
| --------------------------- | -------------------------------------------------------------------- |
| `app/database/tables.py`    | Define as tabelas `consultas` e `usuarios` com SQLModel              |
| `app/database/session.py`   | Cria o engine, fornece sessões e inicializa o esquema                |
| `app/database/consultas.py` | Centraliza o CRUD e os filtros de consultas                          |
| `app/database/users.py`     | Consulta usuários e insere somente as contas demonstrativas ausentes |
| `app/config.py`             | Carrega URL do banco e segredos pelo ambiente                        |

`ConsultaDB` e `UsuarioDB` possuem chaves, limites, índices e tipos compatíveis
com seus usos. Os campos internos de auditoria continuam armazenados, mas os
`response_model` definidos anteriormente permanecem responsáveis por não
expô-los ao cliente.

## 3. Sessões por injeção de dependência

A função `get_session` abre uma sessão SQLModel para a requisição e a fecha ao
final do bloco `with`:

```python
def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session
```

As rotas declaram a dependência com `Depends(get_session)` e entregam a sessão
ao repositório. Dessa forma, as rotas não criam conexões manualmente e a regra
de ciclo de vida fica centralizada em um único módulo.

Na inicialização da aplicação, o `lifespan` chama `inicializar_banco`, que cria
as tabelas ausentes e cadastra as contas exclusivamente demonstrativas de modo
idempotente.

## 4. Queries parametrizadas

Nenhum valor recebido do cliente é concatenado a uma string SQL. Os filtros são
montados por expressões do SQLModel/SQLAlchemy:

```python
statement = select(ConsultaDB)
if status is not None:
    statement = statement.where(ConsultaDB.status == status)
```

Ao executar `GET /consultas?status=agendada` com o log do engine habilitado, o
driver registra a condição com um marcador separado do valor:

```text
WHERE consultas.status = ? ORDER BY consultas.data_hora, consultas.id
('agendada',)
```

O `?` é o placeholder e `('agendada',)` é o conjunto de parâmetros enviado
separadamente ao driver. Essa separação impede que o texto de entrada altere a
estrutura do comando SQL. As validações de whitelist e regex do Exercício 9
continuam sendo uma camada adicional, mas não substituem a parametrização.

## 5. Transações e persistência

O repositório usa `session.add`, `session.commit` e `session.refresh` ao criar
ou atualizar registros. Exclusões também são confirmadas com `commit`. Leituras
usam `session.get` ou `session.exec(select(...))`.

Para comprovar que os dados não dependem mais da memória do processo, a
evidência cria uma consulta em um banco SQLite temporário, encerra completamente
o servidor, inicia outro processo apontando para o mesmo arquivo e recupera o
registro com HTTP 200.

SQLite foi escolhido para a demonstração acadêmica porque permite entregar um
banco relacional reproduzível sem infraestrutura externa. A URL está isolada na
configuração, portanto outro driver relacional pode ser adotado sem transferir
essa decisão para as rotas.

## 6. Configuração segura com BaseSettings

`Settings` define os campos de configuração e usa
`SettingsConfigDict(env_file=".env")`. A chave JWT é representada por
`SecretStr`, validada com pelo menos 32 caracteres e só é revelada no ponto de
uso. O MFA aceita exatamente seis dígitos.

O arquivo `.env.example` documenta as variáveis necessárias:

```dotenv
APP_NAME=API de Agendamento de Consultas
APP_ENV=development
DATABASE_URL=sqlite:///./clinica.db
DATABASE_ECHO=false
JWT_SECRET_KEY=<GERE_UMA_CHAVE_ALEATORIA_COM_32_OU_MAIS_CARACTERES>
ADMIN_MFA_CODE=<DEFINA_UM_CODIGO_SIMULADO_DE_SEIS_DIGITOS>
```

Os padrões `*.db`, `*.sqlite`, `*.sqlite3` e `.env` estão no `.gitignore`. O
pacote final deve conter o `.env.example`, mas nunca o `.env` utilizado
localmente nem o arquivo de banco com dados de teste.

## 7. Rastreabilidade dos requisitos

| Requisito                         | Implementação                                 | Verificação                                            |
| --------------------------------- | --------------------------------------------- | ------------------------------------------------------ |
| Banco relacional                  | Modelos de tabela SQLModel                    | Consulta permanece após nova conexão e reinício da API |
| Queries parametrizadas            | `select`, `where`, `contains` e `session.get` | Log mostra `?` e parâmetros separados                  |
| Sessão por dependência            | `get_session` com `yield` e `Depends`         | Todos os endpoints continuam cobertos pela suíte       |
| Configuração externa              | `BaseSettings` e `.env.example`               | Teste carrega `.env` temporário                        |
| Ausência de credenciais hardcoded | `SecretStr`, `.env` ignorado e placeholders   | Revisão dos arquivos de configuração                   |
