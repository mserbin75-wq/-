# 🤖 Бот ПроСвет

Telegram-бот на базе GigaChat для хакатона «ПроСвет». Бот общается с пользователями через нейросеть Сбера, поддерживает контекст диалога и автоматически выбирает доступную модель GigaChat.

## 📋 Содержание

- [Возможности](#возможности)
- [Структура проекта](#структура-проекта)
- [Требования](#требования)
- [Установка](#установка)
- [Запуск без Docker](#запуск-без-docker)
- [Запуск через Docker](#запуск-через-docker)
- [Деплой на сервер](#деплой-на-сервер)
- [Переменные окружения](#переменные-окружения)
- [Частые проблемы](#частые-проблемы)

## Возможности

- 💬 Общение через GigaChat (нейросеть Сбера)
- 🔄 Автоматический выбор доступной модели при запуске
- 📝 Поддержка контекста диалога
- 🔁 Автоперезапуск при сбое (через Docker)
- 🐳 Готов к деплою через Docker Compose

## Структура проекта

```
ai-bot/
├── bot.py              # Основной код бота
├── Dockerfile          # Рецепт сборки Docker-образа
├── docker-compose.yml  # Конфигурация запуска контейнера
├── requirements.txt    # Python-зависимости
└── README.md           # Этот файл
```

## Требования

- Python 3.11+
- Telegram Bot Token (получить у [@BotFather](https://t.me/BotFather))
- GigaChat API Credentials (получить на [developers.sber.ru](https://developers.sber.ru/))
- Docker и Docker Compose (для запуска в контейнере)

## Установка

### 1. Клонировать репозиторий

```bash
git clone https://github.com/ТВОЙ_ЛОГИН/ai-bot.git
cd ai-bot
```

### 2. Установить зависимости

```bash
pip install -r requirements.txt
```

### 3. Настроить токены

Открой `bot.py` в текстовом редакторе и вставь свои ключи:

```python
BOT_TOKEN = "ТВОЙ_ТОКЕН_ОТ_BOTFATHER"
GIGACHAT_CREDENTIALS = "ТВОИ_CREDENTIALS_ОТ_GIGACHAT"
```

## Запуск без Docker

### Пример запуска через командную строку

**Windows (PowerShell):**
```powershell
cd C:\Users\mserb\Desktop\ai-bot
python bot.py
```

**Linux / macOS:**
```bash
cd /path/to/ai-bot
python3 bot.py
```

После запуска в консоли появится:
```
2026-09-20 03:00:00,000 - INFO - Бот ПроСвет запущен!
2026-09-20 03:00:00,123 - INFO - Start polling
2026-09-20 03:00:00,456 - INFO - Run polling for bot @prosvethakatonbot
2026-09-20 03:00:01,789 - INFO - Доступные модели: ['GigaChat:2.0.28.2', ...]
2026-09-20 03:00:01,790 - INFO - Выбрана модель: GigaChat:2.0.28.2
```

Бот готов к работе — открой Telegram и напиши ему сообщение.

Для остановки нажми `Ctrl+C` в консоли.

## Запуск через Docker

### 1. Установить Docker

**Windows:** скачать [Docker Desktop](https://docs.docker.com/desktop/install/windows-install/) и запустить.

**Linux (Ubuntu/Debian):**
```bash
apt update && apt install -y docker.io docker-compose
```

### 2. Сборка и запуск контейнера

В папке проекта выполни одну команду:

```bash
docker-compose up -d --build
```

Эта команда:
1. Прочитает `Dockerfile` и соберёт Docker-образ
2. Создаст и запустит контейнер `prosvet-bot`
3. Запустит бота в фоновом режиме (`-d`)
4. Включит автоперезапуск при сбое (`restart: unless-stopped`)

### 3. Проверить, что контейнер работает

```bash
docker ps
```

В списке должен быть контейнер `prosvet-bot` со статусом `Up`.

### 4. Посмотреть логи бота

```bash
docker logs -f prosvet-bot
```

`-f` — следить за логами в реальном времени. Нажми `Ctrl+C` чтобы выйти из просмотра логов (бот продолжит работать).

### 5. Остановить контейнер

```bash
docker-compose down
```

### 6. Пересобрать после изменения кода

```bash
docker-compose up -d --build
```

## Деплой на сервер

### Шаг 1. Купить VPS

Любой российский хостинг: [Timeweb](https://timeweb.cloud/), [Beget](https://beget.com/), [FirstVDS](https://firstvds.ru/).
Минимальные требования: 1 ядро, 1 ГБ ОЗУ, ~200 ₽/мес.

### Шаг 2. Подключиться по SSH

```bash
ssh root@IP_АДРЕС_СЕРВЕРА
```

### Шаг 3. Установить Docker

```bash
apt update && apt install -y docker.io docker-compose
```

### Шаг 4. Скопировать файлы на сервер

**Вариант A — через Git (рекомендуется):**
```bash
git clone https://github.com/ТВОЙ_ЛОГИН/ai-bot.git
cd ai-bot
```

**Вариант B — через SCP (с твоего компа):**
```powershell
scp -r C:\Users\mserb\Desktop\ai-bot root@IP_АДРЕС_СЕРВЕРА:/opt/ai-bot
```

### Шаг 5. Запустить бота на сервере

```bash
cd /opt/ai-bot
docker-compose up -d --build
```

### Шаг 6. Проверить

```bash
docker logs -f prosvet-bot
```

Бот работает 24/7. Комп можно выключать.

### Обновление бота на сервере

После изменений в коде:
```bash
cd /opt/ai-bot
git pull                          # если используется Git
docker-compose up -d --build      # пересобрать и перезапустить
```

## Переменные окружения

| Переменная | Описание | Где получить |
|---|---|---|
| `BOT_TOKEN` | Токен Telegram-бота | [@BotFather](https://t.me/BotFather) в Telegram |
| `GIGACHAT_CREDENTIALS` | Ключи API GigaChat | [developers.sber.ru](https://developers.sber.ru/) |

В текущей версии токены хранятся прямо в `bot.py`. Для продакшена рекомендуется вынести их в файл `.env`.

## Частые проблемы

### `404 No such model`

Бот не может найти модель GigaChat. В текущей версии бот автоматически выбирает доступную модель через `get_models()`. Если ошибка остаётся — проверь, что credentials от GigaChat вписаны правильно.

### `Cannot connect to host api.telegram.org`

Проблема с интернетом, а не с кодом. Проверь подключение и перезапусти бота:
```bash
docker-compose down
docker-compose up -d --build
```

### `Unauthorized` / `401`

Неверные credentials от GigaChat. Проверь, что скопировал их полностью, без лишних пробелов.

### `Conflict: terminated by other getUpdates`

Другой экземпляр бота уже запущен. Останови все копии:
```bash
docker-compose down
```
И запусти заново:
```bash
docker-compose up -d --build
```

## Команда проекта
КТВ

Бот создан для хакатона «ПроСвет».
