# url-shortener

A FastAPI URL shortener.

## Structure

```
url-shortener/
├── app/
│   ├── __init__.py
│   ├── main.py          # app creation, startup, router wiring
│   ├── config.py        # settings from env
│   ├── database.py      # engine, session, Base, get_db dependency
│   ├── models.py        # SQLAlchemy tables
│   ├── schemas.py       # Pydantic request/response models
│   ├── codegen.py       # short-code generation
│   ├── services.py      # business logic (no HTTP knowledge)
│   └── routers/
│       ├── __init__.py
│       ├── links.py     # POST /links, GET /links/{code}/stats
│       └── redirect.py  # GET /{code}
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_links.py
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
└── README.md
```

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload
```

## Test

```bash
pytest
```
