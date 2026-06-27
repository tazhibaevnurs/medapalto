# Реализация — учёт товаров под комиссию (Django)

Веб-приложение на Django для учёта товаров, сданных под реализацию:
администратор заводит товары и выдаёт их продажникам, продажники видят
только свои товары (без права редактирования), фиксируются продажи,
оплаты, возвраты и долги, есть дашборд и журнал всех операций.

Это полноценный сервер с базой данных и нормальным хешированием
паролей (через стандартный `django.contrib.auth`) — в отличие от
прототипа-артефакта, это можно реально использовать как основу для
рабочего проекта.

## Бизнес-логика (на случай если будете менять код)

- У товара есть **базовая цена**. При выдаче продажнику администратор
  добавляет **надбавку** — это и есть цена для клиента.
- Когда продажник продаёт товар, он должен компании **базовую цену**
  за каждую проданную штуку, а **надбавку оставляет себе** — это его
  заработок (см. колонку «заработал» в дашборде и у продажников).
- Возврат уменьшает остаток у продажника и **автоматически возвращает
  товар на склад** (пересчёт остатков).
- Нельзя удалить товар, который всё ещё числится у продажника, и
  нельзя удалить выдачу, по которой уже были продажи, оплаты или
  возвраты — чтобы не потерять историю расчётов.
- Каждое действие пишется в журнал (`/logs/`).

## Клонирование с GitHub

```bash
git clone https://github.com/<ваш-username>/realizatsiya_django.git
cd realizatsiya_django
cp .env.example .env   # Windows: copy .env.example .env
# Отредактируйте .env при необходимости (для локального запуска можно оставить как есть)
```

## Установка и запуск локально

Понадобится Python 3.10+.

```bash
# 1. Перейти в папку проекта
cd realizatsiya_django

# 2. Создать и активировать виртуальное окружение
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Применить миграции (создаст файл db.sqlite3)
python manage.py migrate

# 5. Запустить сервер
python manage.py runserver
```

Откройте в браузере **http://127.0.0.1:8000/**

## Как начать пользоваться

1. На странице входа нажмите «Регистрация».
2. Выберите роль «Администратор» и введите код: `RP-2026-BOSS`
   (код задан в `config/settings.py`, переменная `ADMIN_REGISTRATION_CODE`
   — поменяйте на свой перед реальным использованием и никому, кроме
   доверенных людей, не сообщайте).
3. Заведите товары на вкладке «Товары».
4. На вкладке «Выдачи» выдавайте товары продажникам с нужной надбавкой.
5. Продажники регистрируются сами (роль «Продажник», без кода) по той
   же ссылке — после входа видят только свои товары, без возможности
   что-то менять.

Все данные хранятся в обычной базе SQLite — файл `db.sqlite3` появится
после первого `migrate`. Если хотите начать с чистого листа — просто
удалите этот файл и выполните `migrate` снова.

## Стандартная админка Django (бонус)

По адресу `/admin/` доступна обычная Django-админка со всеми моделями
(товары, выдачи, пользователи, журнал) — удобно для быстрой ручной
правки данных или отладки. Чтобы зайти туда, создайте суперпользователя:

```bash
python manage.py createsuperuser
```

## Запуск тестов

В проекте есть базовый набор unit-тестов Django (`consignment/tests.py`),
который можно запустить так:

```bash
python manage.py test
```

## Деплой на сервер через Docker

Проект упакован в Docker-контейнер (Gunicorn + WhiteNoise). База SQLite
хранится в Docker-volume `app_data`, данные не теряются при перезапуске.

### 1. Подготовка сервера (Ubuntu/Debian)

```bash
# Установка Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Перелогиньтесь в SSH, чтобы группа docker применилась

# Проверка
docker --version
docker compose version
```

### 2. Загрузка проекта на сервер

**Вариант A — через Git:**

```bash
ssh user@YOUR_SERVER_IP
sudo mkdir -p /opt/realizatsiya && sudo chown $USER:$USER /opt/realizatsiya
cd /opt/realizatsiya
git clone https://github.com/<ваш-username>/realizatsiya_django.git .
```

**Вариант B — копирование с локального ПК (Windows PowerShell):**

```powershell
scp -r "C:\Users\User\Desktop\realizatsiya_django\*" user@YOUR_SERVER_IP:/opt/realizatsiya/
```

На сервере должны оказаться: `Dockerfile`, `docker-compose.yml`, `docker/`, `config/`, `consignment/`, `static/`, `manage.py`, `requirements.txt`.

### 3. Настройка окружения на сервере

```bash
cd /opt/realizatsiya
cp .env.example .env
nano .env
```

Пример `.env` для production:

```env
DJANGO_SECRET_KEY=сгенерируйте-длинную-случайную-строку
ADMIN_REGISTRATION_CODE=ваш-секретный-код
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=YOUR_SERVER_IP,example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com
APP_PORT=80
```

Сгенерировать секретный ключ:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 4. Запуск

```bash
cd /opt/realizatsiya
docker compose up -d --build
docker compose ps
docker compose logs -f web
```

Приложение будет доступно по адресу `http://YOUR_SERVER_IP/` (порт 80).

Откройте порт в файрволе, если нужно:

```bash
sudo ufw allow 80/tcp
sudo ufw enable
```

### 5. Обновление после изменений в коде

```bash
cd /opt/realizatsiya
git pull                    # если деплой через Git
docker compose up -d --build
```

### 6. Полезные команды

```bash
# Остановить
docker compose down

# Перезапустить
docker compose restart web

# Создать суперпользователя для /admin/
docker compose exec web python manage.py createsuperuser

# Бэкап базы SQLite
docker compose exec web cat /data/db.sqlite3 > backup-$(date +%F).sqlite3
```

### HTTPS (рекомендуется)

Поставьте перед контейнером reverse-proxy (Caddy или Nginx) с SSL-сертификатом.
В `.env` укажите `DJANGO_CSRF_TRUSTED_ORIGINS=https://ваш-домен` и добавьте
домен в `DJANGO_ALLOWED_HOSTS`. Прокси должен передавать заголовок
`X-Forwarded-Proto: https`.

## Что стоит сделать перед реальным боевым запуском (не локально)

Это не относится к запуску «у себя на компьютере для проверки», но
важно, если решите развернуть проект на сервере и дать доступ другим
людям через интернет:

- Скопировать `.env.example` в `.env` и задать свои `DJANGO_SECRET_KEY` и
  `ADMIN_REGISTRATION_CODE`.
- Поставить `DJANGO_DEBUG=0` и указать `DJANGO_ALLOWED_HOSTS`.
- Настроить HTTPS через reverse-proxy (Caddy/Nginx).
- При большой нагрузке рассмотреть переход с SQLite на PostgreSQL.

## Структура проекта

```
realizatsiya_django/
├── Dockerfile
├── docker-compose.yml
├── docker/
│   └── entrypoint.sh        # migrate + collectstatic + gunicorn
├── manage.py
├── requirements.txt
├── config/                  # настройки и маршруты проекта
│   ├── settings.py
│   └── urls.py
├── consignment/             # основное приложение
│   ├── models.py            # User, Product, Issuance, LogEntry
│   ├── views.py             # вся бизнес-логика
│   ├── forms.py
│   ├── urls.py
│   ├── admin.py             # регистрация моделей в /admin/
│   └── templates/consignment/
│       ├── base.html
│       ├── auth.html
│       ├── dashboard.html
│       ├── products.html
│       ├── issuances.html
│       ├── sellers.html
│       ├── logs.html
│       └── seller_home.html
└── static/css/style.css     # оформление (крафт-бумага / накладная)
```
