# RSS → Telegram: каркас приложения

Тестовое задание: периодический опрос RSS-ленты новостного сайта и уведомления в Telegram о новых постах. Есть рабочая реализация **RSSParser** (httpx + feedparser), **Storage** (SQLite **или** PostgreSQL по `DATABASE_URL`, дедуп по `guid`/ссылке и `content_hash`), **Notifier** (Telegram `sendMessage`), планировщик APScheduler, **Docker Compose** и юнит-тесты.

## Быстрый старт

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env            # при необходимости; заполните токен и URL ленты
python -m app.main
```

### Тесты

```bash
pip install -r requirements-dev.txt
pytest
```

На GitHub при пуше/PR в `main` или `master` запускается [CI](.github/workflows/ci.yml): pytest на Python 3.9 и 3.11 и сборка Docker-образа.

### Docker (приложение + PostgreSQL)

В контейнере по умолчанию используется **PostgreSQL**: та же таблица `seen_items` и UPSERT, что и в SQLite — удобно для продакшена и нескольких реплик. **Redis** для этой задачи тоже возможен (ключ → хэш), но как «основная БД» состояния уведомлений чаще выбирают реляционный движок с явной схемой и бэкапами тома.

```bash
cp .env.example .env
# заполните TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, RSS_FEED_URL
docker compose up --build
```

`docker-compose.yml` задаёт `DATABASE_URL=postgresql://rss:rss@postgres:5432/rss` и ждёт готовности Postgres по `healthcheck`. Данные БД лежат в volume `pgdata`. Сервис **app** публикует **`METRICS_PORT=9091`** — эндпоинт **`http://<хост>:9091/metrics`** в формате Prometheus.

### Prometheus и Grafana

**Prometheus** опрашивает цели по HTTP (pull) и хранит временные ряды. **Grafana** подключается к Prometheus как к datasource и строит дашборды — это стандартная связка для метрик приложений.

В репозитории уже есть счётчики и гистограмма в `app/metrics.py` (например `rss_poll_runs_total`, `rss_poll_duration_seconds`, `rss_telegram_sent_total`). Чтобы поднять стек мониторинга вместе с приложением:

```bash
docker compose --profile monitoring up --build
```

- **Prometheus**: [http://localhost:9090](http://localhost:9090) — вкладка Graph, запросы вроде `rate(rss_poll_runs_total[5m])`.
- **Grafana**: [http://localhost:3000](http://localhost:3000) (логин/пароль по умолчанию `admin` / `admin` — смените в проде). Источник **Prometheus** подхватывается из `deploy/grafana/provisioning/`.

Локально без Docker: задайте **`METRICS_PORT=9091`** в `.env` и откройте `http://127.0.0.1:9091/metrics`; Prometheus можно запустить отдельно и указать target на ваш хост.

Переменные окружения (см. `.env.example`):

| Переменная | Назначение |
|------------|------------|
| `TELEGRAM_BOT_TOKEN` или `API_KEY` | Токен бота от @BotFather |
| `TELEGRAM_CHAT_ID` | Куда слать (user / группа / канал). Без него сообщения не уходят и посты **не** помечаются в БД (чтобы не потерять уведомления) |
| `RSS_FEED_URL` | URL RSS или Atom |
| `DATABASE_URL` | Если задан — **PostgreSQL** (`psycopg`). В Docker Compose задаётся автоматически |
| `DATABASE_PATH` | Путь к файлу SQLite, если `DATABASE_URL` пуст (локальная разработка без Postgres) |
| `POLL_INTERVAL_SECONDS` | Период опроса (не меньше 30) |
| `METRICS_PORT` | Если задан — экспорт `/metrics` для Prometheus (в Compose для `app` уже **9091**) |

## 1. Схема взаимодействия компонентов

Текстом: **планировщик** по таймеру вызывает **оркестратор** (цикл в `main`). Оркестратор просит **RSSParser** скачать и разобрать ленту в список `Post`. **Storage** отфильтровывает уже виденные записи (по данным в **БД**). **Notifier** отправляет сообщения в Telegram Bot API. После успешной отправки **Storage** фиксирует факт обработки, чтобы при следующем запуске или рестарте дубликаты не ушли повторно.

```mermaid
flowchart LR
  subgraph process["Процесс приложения"]
    SCH[Scheduler]
    ORCH[Оркестратор / main]
    PARSER[RSSParser]
    ST[Storage]
    BOT[Notifier]
  end
  RSS[(RSS/Atom URL)]
  DB[(PostgreSQL / SQLite)]
  TG[Telegram Bot API]

  SCH -->|interval| ORCH
  ORCH --> PARSER
  PARSER --> RSS
  RSS --> PARSER
  PARSER -->|list Post| ORCH
  ORCH --> ST
  ST --> DB
  DB --> ST
  ORCH --> BOT
  BOT --> TG
  ORCH -->|mark_seen| ST
```

## 2. Модели данных

Доменная сущность описана в Pydantic: `app/models/post.py` — поля **title**, **link**, **published_at**, **content_hash**, опционально **external_id** (`guid` из RSS).

## 3. Логика дедупликации

1. **Стабильный ключ записи**: приоритет `guid` из элемента RSS (если есть и не пустой); иначе нормализованный **link** как первичный идентификатор материала.
2. **Хэш содержимого**: `content_hash` = SHA-256 от нормализованной строки (заголовок + ссылка + summary/body), см. `app/utils/hashing.py`. Это отличает «тот же URL, но текст поправили» от полного совпадения.
3. **Правило «новый пост»**: в БД нет строки с таким ключом **или** для этого ключа сохранённый `content_hash` отличается от текущего (редкий случай обновления материала).
4. **Идемпотентность при рестарте**: состояние хранится **в БД** (файл SQLite или PostgreSQL с томом в Docker), а не только в памяти процесса. После успешной отправки выполняется `mark_seen` (UPSERT). Если процесс упал **до** `mark_seen`, при повторе возможен повторный пуш одного поста — в проде обычно добавляют **outbox** с подтверждением от API или транзакцию «отправил → записал».

## 4. Почему такой подход к «кешированию»

- **Персистентное хранилище (SQLite или PostgreSQL)** вместо чистого in-memory: после перезапуска контейнера или сервера набор «уже отправленных» не теряется, что и требуется от антидубликата.
- **Не кешируем всю ленту**: храним минимальный набор (ключ + хэш + опционально время), чтобы не раздувать БД и не дублировать контент сайта.
- **content_hash** рядом с ключом: защита от ложного «уже видели», если издатель изменил заголовок/описание при том же URL.
- При необходимости поверх БД можно добавить **краткоживущий in-memory LRU** по ключам в рамках одного процесса, чтобы снизить число чтений при плотном polling.

## Структура репозитория

```
app/
  __init__.py
  main.py           # цикл опроса + APScheduler
  config.py         # настройки из .env
  rss_parser.py     # class RSSParser
  storage.py        # class Storage
  notifier.py       # class Notifier
  models/post.py    # Pydantic Post
  utils/hashing.py  # SHA-256 для дедупликации
```

Парсер RSS, хранилище и отправка в Telegram реализованы; конфигурация — через переменные окружения и Docker Compose.

## Безопасность

Не коммитьте `.env` с реальным токеном. Токен бота = секрет; при утечке перевыпустите его в @BotFather.
