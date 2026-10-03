# Exercício 6

## 1. Objetivo e resultado

A API passou a exigir autenticação para consultas e para a agenda interna. O
fluxo humano usa `OAuth2PasswordBearer`; as senhas ficam armazenadas somente como
hash bcrypt; os tokens JWT são assinados, expiram em 30 minutos e carregam claims
de identidade, papel, profissional vinculado e MFA. A autorização foi
centralizada em `app/auth/security.py`.

Foram implementados:

- `POST /auth/token` para autenticação por usuário e senha;
- `GET /auth/me` para consultar a identidade autenticada sem expor o hash;
- `GET /admin/usuarios`, restrito a administradores com MFA verificado;
- proteção de todas as rotas de consultas e da página `/agenda`;
- ownership baseado no `profissional_id` da consulta;
- filtragem da listagem para que o profissional veja somente seus recursos;
- testes de autenticação, RBAC, MFA, expiração e ownership.

`GET /health` permanece público porque expõe apenas o estado do processo e é
necessário para monitoramento de infraestrutura.

## 2. Modelo de autorização escolhido

Foi escolhido um modelo híbrido de **RBAC com autorização por recurso**.

O RBAC resolve as permissões gerais dos três papéis. A autorização por recurso
complementa o RBAC comparando o `profissional_id` do usuário com o
`profissional_id` da consulta. Um RBAC puro permitiria que qualquer profissional
com o mesmo papel operasse consultas de outro profissional. Um ABAC completo
seria desnecessariamente complexo neste estágio, pois ainda não existem políticas
dinâmicas baseadas em unidade, horário ou especialidade.

### Matriz de permissões

| Ação                                 | Profissional                          | Recepcionista | Administrador |
| ------------------------------------ | ------------------------------------- | ------------- | ------------- |
| Criar consulta                       | Sim, quando `profissional_id` é o seu | Não           | Não           |
| Listar consultas                     | Somente as próprias                   | Todas         | Todas         |
| Consultar uma consulta               | Somente a própria                     | Sim           | Sim           |
| Atualizar ou excluir                 | Somente a própria                     | Não           | Não           |
| Visualizar agenda                    | Somente itens próprios                | Todos         | Todos         |
| Listar usuários em `/admin/usuarios` | Não                                   | Não           | Sim, com MFA  |

A restrição de escrita segue literalmente o requisito de que somente
profissionais de saúde gerenciem consultas vinculadas ao próprio identificador.
O administrador administra identidades, mas não substitui o profissional em uma
operação clínica.

## 3. Autenticação e sessão

### 3.1 OAuth2PasswordBearer

O esquema `OAuth2PasswordBearer(tokenUrl="/auth/token")` informa ao FastAPI e ao
OpenAPI que as rotas protegidas recebem `Authorization: Bearer <token>`. O
endpoint de token usa formulário OAuth2 estrito, com `grant_type=password`,
`username` e `password`.

O fluxo foi adotado para cumprir o requisito deste exercício e atender o cliente
humano de primeira parte. Ele não será reutilizado para o laboratório M2M, que
terá fluxo próprio no Exercício 7.

### 3.2 Hash bcrypt

Nenhuma senha em texto claro é mantida no repositório de usuários. Os registros
demonstrativos contêm hashes bcrypt com fator de custo 12. Na autenticação, a
senha recebida é comparada com `bcrypt.checkpw`. Entradas acima de 72 bytes são
rejeitadas explicitamente por causa do limite do algoritmo.

### 3.3 JWT e expiração

O token é assinado com HS256 por uma chave obtida de `JWT_SECRET_KEY`. A chave
não possui valor padrão e deve ter pelo menos 32 caracteres. A validação fixa o
algoritmo aceito e exige os claims abaixo:

| Claim             | Finalidade                                     |
| ----------------- | ---------------------------------------------- |
| `sub`             | Identidade do usuário                          |
| `role`            | Papel RBAC                                     |
| `professional_id` | Vínculo usado no ownership                     |
| `mfa`             | Informa se a segunda etapa foi validada        |
| `iat`             | Momento de emissão                             |
| `exp`             | Expiração em 30 minutos                        |
| `iss`             | Emissor `clinicas-api`                         |
| `aud`             | Público `clinicas-clientes-humanos`            |
| `jti`             | Identificador único do token                   |
| `token_type`      | Impede aceitar outro tipo de token como acesso |

Além da assinatura e da expiração, o usuário é relido do repositório a
cada requisição. Papel e vínculo profissional do token devem continuar iguais
aos dados atuais; assim, uma mudança de privilégio invalida tokens antigos.

### 3.4 MFA administrativo simulado

Contas administrativas possuem `mfa_habilitado=True`. Mesmo com senha correta,
`POST /auth/token` responde 403 se `mfa_code` não for enviado. O código é
comparado em tempo constante com `ADMIN_MFA_CODE`, obtido do ambiente. Somente
depois dessa validação o JWT recebe `mfa=true`.

Este MFA é deliberadamente simulado: demonstra a segunda etapa, mas não possui
semente TOTP individual, rota de provisionamento, uso único ou recuperação. Não
deve ser tratado como MFA de produção.

## 4. Centralização dos controles

| Arquivo                                  | Responsabilidade                                                            |
| ---------------------------------------- | --------------------------------------------------------------------------- |
| `app/auth/security.py`                   | bcrypt, criação e validação JWT, usuário atual, RBAC, ownership e filtragem |
| `app/routes/auth.py`                     | Entrada de login, MFA e perfil autenticado                                  |
| `app/routes/admin.py`                    | Rota usada para comprovar a restrição administrativa                        |
| `app/models/usuario.py`                  | Modelos estritos de usuário, token e claims                                 |
| `app/database/users.py`                  | Repositório temporário de usuários com hashes bcrypt                        |
| `app/routes/consultas.py`                | Chama a política central sem duplicá-la                                     |
| `app/routes/pages.py`                    | Exige identidade e usa a mesma filtragem da API                             |
| `tests/test_auth.py`                     | Evidência automatizada dos controles de segurança                           |
| `scripts/gerar_evidencias_ex6.py`        | Reproduz os testes manuais no Swagger e gera os prints com Playwright       |
| `scripts/gerar_evidencias_locais_ex6.py` | Renderiza o código real e a saída real do pytest com Playwright             |

## 5. Rastreabilidade com o threat model

| Ameaça anterior                        | Controle deste exercício                                   | Evidência                                   |
| -------------------------------------- | ---------------------------------------------------------- | ------------------------------------------- |
| TM-01 — falsificação de identidade     | bcrypt, JWT assinado e validação de emissor/audiência      | Testes de login, token inválido e expiração |
| TM-02 — alteração indevida de consulta | Somente profissional owner pode escrever                   | Testes de ownership                         |
| TM-03 — negação de autoria             | `sub`, `jti`, `iat` e usuário atual associado à requisição | Claims JWT                                  |
| TM-04 — divulgação de dados            | Rotas protegidas e listagem filtrada pelo owner            | 401 sem token e 403 entre profissionais     |
| TM-06 — elevação de privilégio         | RBAC central e MFA administrativo                          | Teste obrigatório de não administrador      |
