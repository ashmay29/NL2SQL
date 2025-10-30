# Quick Reference Guide

## 🚀 Quick Start

```bash
# 1. Setup environment
cp backend/.env.example backend/.env
# Edit backend/.env with your credentials

# 2. Start all services
docker-compose up -d

# 3. Check status
curl http://localhost:8000/health
```

## 📍 Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Backend API | http://localhost:8000 | Main API |
| API Docs (Swagger) | http://localhost:8000/docs | Interactive API docs |
| API Docs (ReDoc) | http://localhost:8000/redoc | Alternative API docs |
| Frontend | http://localhost:3000 | Web UI |
| MySQL | localhost:3306 | Target database |
| PostgreSQL | localhost:5432 | App metadata |
| Redis | localhost:6379 | Cache |
| Qdrant | http://localhost:6333 | Vector DB |
| Qdrant Dashboard | http://localhost:6333/dashboard | Vector DB UI |

## 🔧 Common Commands

### Docker
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Restart a service
docker-compose restart backend

# Rebuild after code changes
docker-compose up -d --build backend
```

### Backend Development
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run locally (without Docker)
python -m uvicorn app.main:app --reload

# Run tests (when implemented)
pytest

# Format code
black app/
```

### Frontend Development
```bash
cd frontend

# Install dependencies
npm install

# Run locally
npm run dev

# Build for production
npm run build
```

## 🔑 Environment Variables

### Required
- `SECRET_KEY` - Random string for app security
- `JWT_SECRET_KEY` - Random string for JWT signing
- `MYSQL_URI` - MySQL connection string
- `APP_DB_URI` - PostgreSQL connection string
- `REDIS_URI` - Redis connection string

### Optional but Recommended
- `GEMINI_API_KEY` - For Gemini fallback/feedback
- `OLLAMA_ENDPOINT` - Ollama server URL (default: http://localhost:11434)
- `KAGGLE_USERNAME` - For GNN embedding ingestion
- `KAGGLE_KEY` - Kaggle API key

## 📡 API Endpoints

### Health
```bash
# Basic health
curl http://localhost:8000/health

# Detailed health
curl http://localhost:8000/health/detailed
```

### Schema
```bash
# Get schema
curl http://localhost:8000/api/v1/schema?database=nl2sql_target

# Refresh schema
curl -X POST http://localhost:8000/api/v1/schema/refresh?database=nl2sql_target

# Get schema graph
curl http://localhost:8000/api/v1/schema/graph?database=nl2sql_target
```

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check logs
docker-compose logs backend

# Common issues:
# 1. Missing .env file → cp backend/.env.example backend/.env
# 2. Database not ready → Wait 10-20 seconds after docker-compose up
# 3. Port conflict → Change port in docker-compose.yml
```

### Ollama not working
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Pull model if missing
ollama pull mistral

# Check model list
ollama list
```

### Database connection errors
```bash
# Check if MySQL is running
docker-compose ps mysql

# Connect to MySQL
docker exec -it nl2sql_mysql mysql -uroot -ppassword

# Check databases
docker exec -it nl2sql_mysql mysql -uroot -ppassword -e "SHOW DATABASES;"
```

### Frontend can't reach backend
```bash
# Check CORS settings in backend/app/main.py
# Check VITE_API_BASE_URL in frontend

# Test backend directly
curl http://localhost:8000/health
```

## 📂 Project Structure

```
MajorNL2SQL/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API endpoints
│   │   │   ├── health.py    # Health checks
│   │   │   └── schema.py    # Schema management
│   │   ├── core/            # Core functionality
│   │   │   ├── config.py    # Settings
│   │   │   ├── security.py  # Auth/JWT
│   │   │   └── dependencies.py  # DI
│   │   ├── models/
│   │   │   └── schemas.py   # Pydantic models
│   │   ├── services/        # Business logic
│   │   │   ├── schema_service.py
│   │   │   ├── cache_service.py
│   │   │   └── llm_service.py
│   │   └── main.py          # FastAPI app
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── FINAL_PROJECT_PLAN.md
├── IMPLEMENTATION_STATUS.md
├── SETUP.md
└── QUICK_REFERENCE.md (this file)
```

## 🎯 Next Development Tasks

1. **Populate Sample Database**
   - Create seed data SQL script
   - Migrate DatabaseSetup from nl_to_sql_llm.py

2. **Implement IR Layer**
   - Create IR Pydantic models
   - Build IR validator
   - Build IR→MySQL compiler

3. **Add NL2SQL Endpoints**
   - POST /nl2ir
   - POST /ir2sql
   - POST /nl2sql

4. **Test Ollama Integration**
   - Generate simple IR from NL
   - Validate JSON output

## 📚 Documentation Links

- **Architecture**: See `FINAL_PROJECT_PLAN.md`
- **Setup Guide**: See `SETUP.md`
- **Implementation Status**: See `IMPLEMENTATION_STATUS.md`
- **API Docs**: http://localhost:8000/docs (when running)

## 💡 Tips

- Use `docker-compose logs -f` to watch logs in real-time
- API docs at `/docs` are interactive - you can test endpoints
- Redis CLI: `docker exec -it nl2sql_redis redis-cli`
- MySQL CLI: `docker exec -it nl2sql_mysql mysql -uroot -ppassword`
- Check service health before debugging: `curl http://localhost:8000/health/detailed`

## 🔐 Security Notes

- Change default passwords in `.env` for production
- Never commit `.env` file to git
- Use strong random strings for SECRET_KEY and JWT_SECRET_KEY
- Configure CORS properly for production (don't use `allow_origins=["*"]`)
- Enable HTTPS in production
- Implement rate limiting for production
