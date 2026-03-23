## System Requirement

```bash
node = v24.12.0 
tsc  = 5.9.3      
pnpm = 10.26.2

Python = 3.12.3
pip = 24.0
```

## Getting Started Frontend

First, run the development server:

```bash
git clone https://github.com/crewaa/crewaa.git

cd frontend

pnpm install

pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.


## Getting Started Backend

```bash
cd backend

python3 -m venv .venv

source .venv/bin/activate

python --version
pip --version

pip install -e .

uvicorn app.main:app --reload

uvicorn appp.main:app --host 0.0.0.0 --port 8001

```

### Replace DATABASE_URL with your local db url
```bash
.env

DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/crewaa_db

```


curl -X POST http://127.0.0.1:8000/instagram/scrape/1
