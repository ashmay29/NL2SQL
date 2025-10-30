# NL2SQL System - Setup Guide

## Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)
- Ollama (for local LLM) - Optional but recommended

## Quick Start with Docker

1. **Clone and navigate to project**
   ```bash
   cd MajorNL2SQL
   ```

2. **Create environment file**
   ```bash
   cp backend/.env.example backend/.env
   ```
   
   Edit `backend/.env` and set:
   - `SECRET_KEY` and `JWT_SECRET_KEY` (generate random strings)
   - `GEMINI_API_KEY` (if using Gemini for feedback)
   - Other settings as needed

3. **Start all services**
   ```bash
   docker-compose up -d
   ```

4. **Check health**
   ```bash
   curl http://localhost:8000/health
   ```

5. **Access services**
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Frontend: http://localhost:3000
   - Qdrant: http://localhost:6333/dashboard

## Local Development (without Docker)

### Backend

1. **Install dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Setup databases**
   - MySQL 8.0+ running on localhost:3306
   - PostgreSQL 15+ running on localhost:5432
   - Redis running on localhost:6379
   - Qdrant running on localhost:6333

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

4. **Run backend**
   ```bash
   python -m uvicorn app.main:app --reload
   ```

### Frontend

1. **Install dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Run frontend**
   ```bash
   npm run dev
   ```

## Ollama Setup (Recommended for Local LLM)

1. **Install Ollama**
   - Windows: Download from https://ollama.ai/download
   - Run installer

2. **Pull Mistral model**
   ```bash
   ollama pull mistral
   ```

3. **Verify Ollama is running**
   ```bash
   curl http://localhost:11434/api/tags
   ```

4. **Update backend/.env**
   ```
   LLM_PROVIDER=ollama
   OLLAMA_ENDPOINT=http://localhost:11434
   OLLAMA_MODEL=mistral:latest
   ```

## Testing the Setup

1. **Health check**
   ```bash
   curl http://localhost:8000/health/detailed
   ```

2. **Get schema**
   ```bash
   curl http://localhost:8000/api/v1/schema?database=nl2sql_target
   ```

3. **View API docs**
   Open http://localhost:8000/docs in browser

## Project Structure

```
MajorNL2SQL/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API endpoints
│   │   ├── core/            # Config, security, dependencies
│   │   ├── models/          # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   └── main.py          # FastAPI app
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── FINAL_PROJECT_PLAN.md
```

## Next Steps

1. ✅ Backend API running
2. ✅ Schema service operational
3. ✅ Cache service with embeddings
4. ✅ LLM service configured
5. 🚧 Implement NL2SQL endpoints
6. 🚧 Add GNN embedding ingestion
7. 🚧 Build chat interface
8. 🚧 Add Monaco SQL editor

## Troubleshooting

### Backend won't start
- Check all environment variables in `.env`
- Ensure databases are running and accessible
- Check logs: `docker-compose logs backend`

### Ollama connection fails
- Ensure Ollama is running: `ollama list`
- Check endpoint: `curl http://localhost:11434/api/tags`
- Verify firewall settings

### Frontend can't reach backend
- Check CORS settings in `backend/app/main.py`
- Verify `VITE_API_BASE_URL` in frontend

### Database connection errors
- Check MySQL/PostgreSQL are running
- Verify credentials in `.env`
- Check network connectivity in Docker

## Support

For issues, refer to:
- `FINAL_PROJECT_PLAN.md` for architecture details
- API docs at `/docs` for endpoint specifications
- Logs: `docker-compose logs -f [service-name]`
