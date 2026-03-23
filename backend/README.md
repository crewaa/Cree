## Getting Started Backend

```bash
cd backend

python3 -m venv .venv

source .venv/bin/activate

python --version
pip --version

pip install -e .

```

### Replace DATABASE_URL with your local db url
```bash
.env

DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/crewaa_db

```


