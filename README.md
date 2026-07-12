# fastapi-bookshop

## Быстрый старт

```bash
cp .env.example .env   # заполнить секреты (пароли, ключи Stripe/OAuth/LLM)
# положить JWT-ключи в ./cert (jwt-private.pem, jwt-public.pem)
docker compose up --build
```

Приложение: http://127.0.0.1:8000. Инфраструктурные порты (postgres 5432,
elasticsearch 9200, qdrant 6333, rabbitmq 5672/15672) слушают только 127.0.0.1.

После изменения зависимостей (`pyproject.toml` / `poetry.lock`):

```bash
docker compose up --build
```

`.venv` живёт внутри образа (в контейнеры монтируется только код), поэтому
пересборка образа сразу обновляет зависимости во всех сервисах.
