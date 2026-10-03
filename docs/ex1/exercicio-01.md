# Exercício 1

## Resultado

A aplicação foi criada com FastAPI e dividida nos módulos `routes`, `models` e
`database`. O recurso `consultas` usa `APIRouter` e oferece o ciclo REST completo:
criar, listar, consultar por ID, atualizar parcialmente e excluir. O ponto de
entrada contém apenas a criação da aplicação e o registro dos routers.

A persistência inicial é intencionalmente mantida em memória e encapsulada no
`ConsultaRepository`. Essa separação evita lógica de armazenamento nas rotas e
permite substituir a implementação por SQLModel sem alterar o contrato HTTP.

Os modelos Pydantic validam IDs positivos, textos com limites, status permitidos,
data e hora com fuso explícito e rejeitam campos não declarados. O isolamento de
dependências é feito por `.venv`; a pasta não deve ser enviada no arquivo final,
pois pode ser reconstruída com os arquivos de requisitos.

## Endpoints

| Método   | Caminho           | Resultado de sucesso            |
| -------- | ----------------- | ------------------------------- |
| `POST`   | `/consultas`      | `201 Created` e consulta criada |
| `GET`    | `/consultas`      | `200 OK` e lista de consultas   |
| `GET`    | `/consultas/{id}` | `200 OK` e consulta encontrada  |
| `PATCH`  | `/consultas/{id}` | `200 OK` e consulta atualizada  |
| `DELETE` | `/consultas/{id}` | `204 No Content`                |
| `GET`    | `/health`         | `200 OK` e `{"status":"ok"}`    |
