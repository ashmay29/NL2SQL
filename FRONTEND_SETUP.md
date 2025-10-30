# Frontend Setup Guide - Apple-like UI

## What Was Built

An elegant, minimal Apple-inspired UI for testing Phase 1 & 2 endpoints:

### Pages
1. **Dashboard** - System health, schema stats, service status
2. **Schema Explorer** - View tables, columns, relationships, refresh schema
3. **NL → SQL Playground** - Test NL→IR, IR→SQL, and NL→SQL endpoints
4. **Embeddings Manager** - Upload GNN embeddings

### Design Features
- Apple-like aesthetic (SF Pro font, subtle shadows, smooth animations)
- Clean cards with hover effects
- Color palette: Apple blue (#007AFF), green, orange, red
- Monaco Editor for SQL/JSON display
- Real-time API integration with React Query

## Setup Instructions

### 1. Install Dependencies

```bash
cd frontend
npm install
```

This installs:
- React 18 + TypeScript
- TailwindCSS (styling)
- Framer Motion (animations)
- Lucide React (icons)
- React Router (navigation)
- React Query (API state)
- Monaco Editor (code display)

### 2. Start Development Server

```bash
npm run dev
```

Frontend will be available at:
- **Docker**: http://localhost:5173 (mapped from container port 3000)
- **Local**: http://localhost:5173

### 3. Verify Backend Connection

The UI expects backend at `http://localhost:8000`. This is set via:
- Docker: `VITE_API_BASE_URL` in `docker-compose.yml`
- Local: Default in `src/api/client.ts`

## Usage Guide

### Dashboard
- View system health (healthy/degraded/unhealthy)
- See schema version and table count
- Check Redis status
- View service health

### Schema Explorer
- Browse all tables with columns, types, constraints
- See primary keys, foreign keys, indexes
- View relationships between tables
- Refresh schema to detect changes

### NL → SQL Playground
- **Direct Mode**: Enter natural language → Get SQL instantly
- **Step-by-Step Mode**: See IR generation, then SQL compilation
- View confidence scores, ambiguities, clarifications
- Monaco editor displays SQL with syntax highlighting

Example queries:
- "top 5 customers by total spent"
- "orders count per month"
- "products with low stock"

### Embeddings Manager
- Upload GNN embeddings as JSON
- See current schema fingerprint
- Example payload provided
- Success/error feedback

## Troubleshooting

### TypeScript Errors (Module Not Found)
These are expected before `npm install`. Run:
```bash
cd frontend
npm install
```

### Port 5173 Already in Use
Change in `docker-compose.yml`:
```yaml
ports:
  - "3001:3000"  # Use 3001 instead
```

### Backend Connection Failed
1. Ensure backend is running: `docker-compose ps`
2. Check backend health: `curl http://localhost:8000/health`
3. Verify CORS in `backend/app/main.py` allows frontend origin

### Styling Not Applied
Ensure `index.css` is imported in `src/main.tsx`:
```typescript
import './index.css';
```

## File Structure

```
frontend/
├── src/
│   ├── api/
│   │   ├── client.ts          # Axios instance
│   │   ├── hooks.ts           # React Query hooks
│   │   └── types.ts           # TypeScript types
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Card.tsx
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Badge.tsx
│   │   │   └── Spinner.tsx
│   │   └── Layout.tsx         # Sidebar + main layout
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── SchemaExplorer.tsx
│   │   ├── NLSQLPlayground.tsx
│   │   └── EmbeddingsManager.tsx
│   ├── App.tsx                # Router + QueryClient
│   ├── main.tsx               # Entry point
│   └── index.css              # Tailwind imports
├── tailwind.config.js         # Apple color palette
├── postcss.config.js
└── package.json
```

## Next Steps (Phase 3 & 4)

When implementing Phase 3 (RAG) and Phase 4 (Engine enhancements):
- Add **Feedback** page for submitting corrections
- Add **History** page for query logs
- Enhance **Playground** with multi-turn conversations
- Add **Settings** page for LLM provider config

## Notes

- Lint errors about missing modules will resolve after `npm install`
- The UI is desktop-first but responsive
- All API calls use React Query for caching and error handling
- Monaco Editor lazy-loads for better performance
