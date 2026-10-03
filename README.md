# API de Agendamento de Consultas

API REST para uma rede de clínicas médicas, desenvolvida com FastAPI e
organizada em módulos independentes. A versão atual possui autenticação humana
com OAuth2PasswordBearer, senhas em bcrypt, JWT com expiração, MFA administrativo
simulado, autorização combinando papéis e ownership das consultas e persistência
relacional com SQLModel.

## Estrutura

```text
app/
├── auth/           Autenticação, JWT e autorização centralizadas
├── database/       SQLModel, sessões e repositórios
├── models/         Modelos Pydantic e validações
├── routes/         Endpoints definidos com APIRouter
└── main.py         Fábrica e instância da aplicação FastAPI
tests/              Testes automatizados com pytest
docs/               Relatório de evidências por exercício
```

## Preparação do ambiente no Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Se a política do PowerShell impedir a ativação, o ambiente continua podendo ser
usado diretamente:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## Execução

Crie a configuração local a partir do exemplo:

```powershell
Copy-Item .env.example .env
```

No arquivo `.env`, substitua os placeholders da chave JWT e do código MFA. A
configuração padrão usa `DATABASE_URL=sqlite:///./clinica.db`. O `.env` e o
arquivo do banco são locais e não devem ser incluídos no ZIP da entrega.

Com o ambiente virtual ativado:

```powershell
uvicorn app.main:app --reload
```

A API ficará disponível em `http://127.0.0.1:8000` e a documentação interativa
em `http://127.0.0.1:8000/docs`.

A agenda HTML interna pode ser consultada em
`http://127.0.0.1:8000/agenda?data=2030-05-20`. O ambiente Jinja2 usa herança de
templates e autoescape explícito para impedir a interpretação de conteúdo de
usuário como HTML ou JavaScript. A agenda e as rotas de consultas exigem token
Bearer válido.

## Contas exclusivamente demonstrativas

| Papel          | Usuário         | Senha de demonstração | MFA                            |
| -------------- | --------------- | --------------------- | ------------------------------ |
| Profissional 7 | `profissional7` | `Profissional@123`    | Não                            |
| Profissional 8 | `profissional8` | `Profissional@123`    | Não                            |
| Recepcionista  | `recepcao`      | `Recepcao@123`        | Não                            |
| Administrador  | `admin`         | `Admin@123`           | Sim, valor de `ADMIN_MFA_CODE` |
| Paciente 1     | `paciente1`     | `Paciente@123`        | Não                            |
| Paciente 2     | `paciente2`     | `Paciente@123`        | Não                            |

O código-fonte contém apenas os hashes bcrypt dessas senhas de demonstração.

## Testes automatizados

```powershell
python -m pytest
```
