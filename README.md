# 🤖 AI Research Agent

> Async AI-powered research API — submit a topic, get a structured report. Built with FastAPI, LangGraph, PostgreSQL, and Google Gemini.

> Асинхронный ИИ-агент для исследований — отправьте тему, получите структурированный отчёт. Создан на FastAPI, LangGraph, PostgreSQL и Google Gemini.

[![CI Pipeline](https://github.com/VachMalkhasyan/ai-research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/VachMalkhasyan/ai-research-agent/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-async-green)
![LangGraph](https://img.shields.io/badge/LangGraph-agent-purple)
![Docker](https://img.shields.io/badge/Docker-compose-blue)

---

## 📋 Table of Contents / Содержание

- [English](#english)
  - [What it does](#what-it-does)
  - [Architecture](#architecture)
  - [Tech Stack & Decisions](#tech-stack--decisions)
  - [Project Structure](#project-structure)
  - [How to Run](#how-to-run)
  - [API Reference](#api-reference)
- [Русский](#русский)
  - [Что это делает](#что-это-делает)
  - [Архитектура](#архитектура)
  - [Стек и решения](#стек-и-решения)
  - [Структура проекта](#структура-проекта)
  - [Запуск](#запуск)
  - [API](#api)

---

# English

## What it does

The AI Research Agent accepts a research topic via a REST API and returns a structured, AI-generated report — without making the client wait. The API responds immediately with a `task_id`, while the agent works in the background. The client polls for the result when ready.

**Example flow:**
1. `POST /research` → `{"prompt": "Compare PostgreSQL and MongoDB"}`
2. API returns instantly → `{"task_id": "abc-123", "status": "pending"}`
3. Agent researches + writes report in background (10–30 seconds)
4. `GET /research/abc-123` → `{"status": "done", "result": "## Full Report..."}`

---

## Architecture

```
┌─────────────┐     POST /research      ┌──────────────────────────────┐
│             │ ──────────────────────► │         FastAPI App           │
│   Client    │                         │                              │
│             │ ◄────────────────────── │  1. Save task (status=pending)│
│             │   202 + task_id (fast)  │  2. Return task_id           │
│             │                         │  3. Kick off BackgroundTask  │
└─────────────┘                         └──────────────┬───────────────┘
       │                                               │
       │  GET /research/{task_id}                      ▼
       │ ──────────────────────►        ┌──────────────────────────────┐
       │                                │       LangGraph Agent         │
       │ ◄────────────────────────────  │                              │
       │   {status, result}             │  ResearcherNode              │
                                        │       ↓                      │
                                        │  WriterNode                  │
                                        └──────────────┬───────────────┘
                                                       │
                                                       ▼
                                        ┌──────────────────────────────┐
                                        │        PostgreSQL            │
                                        │  research_tasks table        │
                                        │  id | prompt | status | result│
                                        └──────────────────────────────┘
```

### Why this architecture?

**The core problem:** LLM calls take 10–30 seconds. A synchronous API would leave the client hanging — timeouts, bad UX, blocked server resources.

**The solution:** Async task pattern.
- The API layer is completely decoupled from the AI layer
- `BackgroundTasks` handles long-running work without blocking the event loop
- PostgreSQL persists task state — if the server restarts, no data is lost
- The client polls at their own pace — no WebSocket complexity needed for v1

---

## Tech Stack & Decisions

| Technology | Why chosen | Trade-off |
|-----------|-----------|-----------|
| **FastAPI** | Native async support, automatic OpenAPI docs, Pydantic validation | Smaller ecosystem than Django |
| **LangGraph** | Explicit agent graph — each node has one job, easy to extend | More verbose than a single LLM call |
| **PostgreSQL** | ACID compliance, reliable state persistence for task lifecycle | Overkill for simple KV storage, but enables future Human-in-the-Loop |
| **SQLAlchemy async** | Non-blocking DB queries — DB calls don't block the event loop | More setup than sync ORMs |
| **Google Gemini** | Free tier available, competitive quality | OpenAI can be swapped in by changing one line |
| **Docker Compose** | One command to run the full stack — reproducible everywhere | Adds Docker as a dependency |

### Key architectural decision — BackgroundTasks vs Celery

For v1, FastAPI's built-in `BackgroundTasks` is used instead of Celery + Redis. 

**Why:** Celery adds significant infrastructure complexity (broker, worker processes, separate deployment). For a research tool where tasks are fire-and-forget and don't need retries or scheduling, `BackgroundTasks` is the right level of complexity.

**When to upgrade to Celery:** If task volume grows, retries are needed, or tasks need to be distributed across multiple workers.

---

## Project Structure

```
ai-research-agent/
├── app/
│   ├── main.py          # API layer — endpoints, request/response schemas
│   ├── agent.py         # AI layer — LangGraph graph, Researcher + Writer nodes
│   ├── database.py      # DB connection, async engine, session factory
│   └── models.py        # SQLAlchemy table definitions
├── .github/
│   └── workflows/
│       └── ci.yml       # CI pipeline — lint, security scan, docker build
├── Dockerfile           # Multi-stage build — slim production image
├── docker-compose.yml   # Local infrastructure — app + PostgreSQL
├── pyproject.toml       # Ruff linter config
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
└── README.md
```

---

## How to Run

### Prerequisites
- Docker + Docker Compose
- Google Gemini API key (free at [aistudio.google.com](https://aistudio.google.com))

### Steps

**1. Clone the repo**
```bash
git clone https://github.com/VachMalkhasyan/ai-research-agent.git
cd ai-research-agent
```

**2. Set up environment**
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

**3. Start the stack**
```bash
docker-compose up --build
```

**4. API is live at** `http://localhost:8000`

**5. Interactive docs at** `http://localhost:8000/docs` (auto-generated by FastAPI)

---

## API Reference

### `POST /research`
Start a new research task.

**Request:**
```json
{
  "prompt": "Compare PostgreSQL and MongoDB"
}
```

**Response `202 Accepted`:**
```json
{
  "task_id": "71cc428e-df5d-4be5-a080-27c0aa4c06a2",
  "status": "pending"
}
```

---

### `GET /research/{task_id}`
Poll for task status and result.

**Response (in progress):**
```json
{
  "task_id": "71cc428e-df5d-4be5-a080-27c0aa4c06a2",
  "status": "processing",
  "prompt": "Compare PostgreSQL and MongoDB",
  "result": null
}
```

**Response (complete):**
```json
{
  "task_id": "71cc428e-df5d-4be5-a080-27c0aa4c06a2",
  "status": "done",
  "prompt": "Compare PostgreSQL and MongoDB",
  "result": "## Report: PostgreSQL vs MongoDB\n\n..."
}
```

---

## CI/CD Pipeline

Every push to `main` triggers 3 automated jobs:

| Job | Tool | What it checks |
|-----|------|---------------|
| **Code Quality** | Ruff | PEP8 compliance, import order, formatting |
| **Security Scan** | Bandit | Hardcoded secrets, unsafe functions, injection risks |
| **Docker Build** | Buildx | Dockerfile builds successfully, image is valid |

Jobs 1 and 2 run in parallel. Job 3 only runs if both pass.

---

---

# Русский

## Что это делает

AI Research Agent принимает тему исследования через REST API и возвращает структурированный отчёт, сгенерированный ИИ — без ожидания со стороны клиента. API отвечает мгновенно с `task_id`, пока агент работает в фоне. Клиент запрашивает результат когда готов.

**Пример работы:**
1. `POST /research` → `{"prompt": "Сравни PostgreSQL и MongoDB"}`
2. API отвечает мгновенно → `{"task_id": "abc-123", "status": "pending"}`
3. Агент исследует и пишет отчёт в фоне (10–30 секунд)
4. `GET /research/abc-123` → `{"status": "done", "result": "## Полный отчёт..."}`

---

## Архитектура

```
┌─────────────┐     POST /research      ┌──────────────────────────────┐
│             │ ──────────────────────► │         FastAPI App           │
│   Клиент    │                         │                              │
│             │ ◄────────────────────── │  1. Сохранить задачу (pending)│
│             │   202 + task_id (быстро)│  2. Вернуть task_id          │
│             │                         │  3. Запустить BackgroundTask  │
└─────────────┘                         └──────────────┬───────────────┘
       │                                               │
       │  GET /research/{task_id}                      ▼
       │ ──────────────────────►        ┌──────────────────────────────┐
       │                                │       LangGraph Агент        │
       │ ◄────────────────────────────  │                              │
       │   {status, result}             │  ResearcherNode              │
                                        │       ↓                      │
                                        │  WriterNode                  │
                                        └──────────────┬───────────────┘
                                                       │
                                                       ▼
                                        ┌──────────────────────────────┐
                                        │        PostgreSQL            │
                                        │  таблица research_tasks      │
                                        │  id | prompt | status | result│
                                        └──────────────────────────────┘
```

### Почему такая архитектура?

**Проблема:** LLM-вызовы занимают 10–30 секунд. Синхронный API заставлял бы клиента ждать — таймауты, плохой UX, блокировка серверных ресурсов.

**Решение:** Асинхронный паттерн задач.
- API-слой полностью отвязан от AI-слоя
- `BackgroundTasks` выполняет долгие операции без блокировки event loop
- PostgreSQL сохраняет состояние задач — при перезапуске сервера данные не теряются
- Клиент опрашивает API в своём темпе — без сложности WebSocket на первой версии

---

## Стек и решения

| Технология | Почему выбрана | Trade-off |
|-----------|---------------|-----------|
| **FastAPI** | Нативная async-поддержка, автодокументация OpenAPI, валидация Pydantic | Экосистема меньше, чем у Django |
| **LangGraph** | Явный граф агента — каждый узел делает одно, легко расширять | Многословнее, чем один LLM-вызов |
| **PostgreSQL** | ACID-транзакции, надёжное хранение состояния жизненного цикла задач | Избыточен для простого KV, но открывает путь к Human-in-the-Loop |
| **SQLAlchemy async** | Неблокирующие запросы к БД | Больше настройки, чем у синхронных ORM |
| **Google Gemini** | Бесплатный тариф, конкурентное качество | OpenAI подключается заменой одной строки |
| **Docker Compose** | Весь стек одной командой — воспроизводимо везде | Добавляет Docker как зависимость |

### Ключевое архитектурное решение — BackgroundTasks vs Celery

В первой версии используется встроенный `BackgroundTasks` FastAPI вместо Celery + Redis.

**Почему:** Celery добавляет значительную инфраструктурную сложность (брокер, воркеры, отдельный деплой). Для инструмента исследований, где задачи выполняются без повторов и расписания, `BackgroundTasks` — правильный уровень сложности.

**Когда переходить на Celery:** Если вырастет объём задач, понадобятся повторы или распределение задач по нескольким воркерам.

---

## Структура проекта

```
ai-research-agent/
├── app/
│   ├── main.py          # API-слой — эндпоинты, схемы запросов/ответов
│   ├── agent.py         # AI-слой — граф LangGraph, узлы Researcher + Writer
│   ├── database.py      # Подключение к БД, async engine, фабрика сессий
│   └── models.py        # Определения таблиц SQLAlchemy
├── .github/
│   └── workflows/
│       └── ci.yml       # CI-пайплайн — линтинг, безопасность, сборка Docker
├── Dockerfile           # Многоэтапная сборка — компактный production-образ
├── docker-compose.yml   # Локальная инфраструктура — app + PostgreSQL
├── pyproject.toml       # Конфиг линтера Ruff
├── requirements.txt     # Python-зависимости
├── .env.example         # Шаблон переменных окружения
└── README.md
```

---

## Запуск

### Требования
- Docker + Docker Compose
- API-ключ Google Gemini (бесплатно на [aistudio.google.com](https://aistudio.google.com))

### Шаги

**1. Клонировать репозиторий**
```bash
git clone https://github.com/VachMalkhasyan/ai-research-agent.git
cd ai-research-agent
```

**2. Настроить окружение**
```bash
cp .env.example .env
# Отредактировать .env и добавить GEMINI_API_KEY
```

**3. Запустить стек**
```bash
docker-compose up --build
```

**4. API доступен по адресу** `http://localhost:8000`

**5. Интерактивная документация** `http://localhost:8000/docs` (автогенерация FastAPI)

---

## API

### `POST /research`
Запустить новую задачу исследования.

**Запрос:**
```json
{
  "prompt": "Сравни PostgreSQL и MongoDB"
}
```

**Ответ `202 Accepted`:**
```json
{
  "task_id": "71cc428e-df5d-4be5-a080-27c0aa4c06a2",
  "status": "pending"
}
```

---

### `GET /research/{task_id}`
Запросить статус и результат задачи.

**Ответ (в процессе):**
```json
{
  "task_id": "71cc428e-df5d-4be5-a080-27c0aa4c06a2",
  "status": "processing",
  "prompt": "Сравни PostgreSQL и MongoDB",
  "result": null
}
```

**Ответ (готово):**
```json
{
  "task_id": "71cc428e-df5d-4be5-a080-27c0aa4c06a2",
  "status": "done",
  "prompt": "Сравни PostgreSQL и MongoDB",
  "result": "## Отчёт: PostgreSQL vs MongoDB\n\n..."
}
```

---

## CI/CD Пайплайн

Каждый push в `main` запускает 3 автоматических задания:

| Задание | Инструмент | Что проверяет |
|---------|-----------|---------------|
| **Code Quality** | Ruff | PEP8, порядок импортов, форматирование |
| **Security Scan** | Bandit | Захардкоженные секреты, небезопасные функции |
| **Docker Build** | Buildx | Dockerfile собирается, образ валиден |

Задания 1 и 2 выполняются параллельно. Задание 3 запускается только если оба прошли.
