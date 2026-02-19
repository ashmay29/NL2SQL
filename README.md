# NL2SQL - Natural Language to SQL System

<p align="center">
  <strong>A Novel Hybrid Framework Combining Graph Neural Networks (GNN) and Large Language Models (LLM) for Intelligent Natural Language to SQL Conversion</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.109+-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-18.2+-61DAFB.svg" alt="React">
  <img src="https://img.shields.io/badge/PyTorch-2.2+-EE4C2C.svg" alt="PyTorch">
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED.svg" alt="Docker">
</p>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Novel Hybrid Framework](#novel-hybrid-framework)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Usage Examples](#usage-examples)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

NL2SQL is an advanced Natural Language to SQL conversion system that employs a **novel hybrid framework** combining **Graph Neural Networks (GNN)** for intelligent schema understanding with **Large Language Models (LLM)** for SQL generation. This dual-approach enables significantly improved accuracy, reduced token usage, and better handling of complex database schemas compared to traditional LLM-only approaches.

### The Problem

Traditional NL2SQL systems face several challenges:
- **Schema Overload**: Large database schemas overwhelm LLM context windows
- **Irrelevant Context**: LLMs receive all tables/columns, including irrelevant ones
- **Token Inefficiency**: Full schema representation wastes expensive API tokens
- **Limited Relationship Understanding**: Text-based prompts poorly capture database relationships

### Our Solution

The NL2SQL hybrid framework addresses these challenges through:
1. **GNN-Based Schema Pruning**: A Graph Attention Network (GAT) model understands database structure and identifies query-relevant schema elements
2. **Intelligent Schema Reduction**: Only relevant tables and columns are sent to the LLM
3. **Relationship-Aware Processing**: Foreign keys and table relationships are encoded in the graph structure
4. **RAG-Enhanced Learning**: Continuous improvement through user feedback and retrieval-augmented generation

---

## Novel Hybrid Framework

### How It Works

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        NL2SQL HYBRID PIPELINE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌──────────────────────┐     ┌────────────────────┐   │
│  │   Natural   │     │    GNN Schema        │     │    LLM + RAG       │   │
│  │  Language   │────▶│    Pruning Layer     │────▶│    SQL Generator   │   │
│  │   Query     │     │                      │     │                    │   │
│  └─────────────┘     │  ┌────────────────┐  │     │  ┌──────────────┐  │   │
│                      │  │ Graph Attention │  │     │  │   Gemini /   │  │   │
│  ┌─────────────┐     │  │   Network (GAT) │  │     │  │    Ollama    │  │   │
│  │  Database   │────▶│  │   3 Layers      │  │     │  └──────────────┘  │   │
│  │   Schema    │     │  │   4 Att. Heads  │  │     │         │          │   │
│  └─────────────┘     │  └────────────────┘  │     │         ▼          │   │
│                      │         │            │     │  ┌──────────────┐  │   │
│                      │         ▼            │     │  │ Intermediate │  │   │
│                      │  ┌────────────────┐  │     │  │ Repr. (IR)   │  │   │
│                      │  │  Top-K Nodes   │  │     │  └──────────────┘  │   │
│                      │  │  (Tables/Cols) │──┼────▶│         │          │   │
│                      │  └────────────────┘  │     │         ▼          │   │
│                      └──────────────────────┘     │  ┌──────────────┐  │   │
│                                                   │  │   MySQL SQL  │  │   │
│                                                   │  │   Compiler   │  │   │
│                                                   │  └──────────────┘  │   │
│                                                   └────────────────────┘   │
│                                                              │             │
│                                                              ▼             │
│                                                   ┌────────────────────┐   │
│                                                   │   Final SQL Query  │   │
│                                                   └────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### GNN Architecture Details

The GNN Schema Ranker uses a **3-layer Graph Attention Network (GAT)** architecture:

| Component | Specification |
|-----------|---------------|
| **Architecture** | 3-layer GAT with Question Injection at Input |
| **Attention Heads** | 4 per layer (concat=False) |
| **Node Features** | 5-dim sparse + 384-dim SentenceTransformer embeddings |
| **Question Embeddings** | 768-dim BERT embeddings |
| **Hidden Channels** | 256 |
| **Dropout** | [0.3, 0.3, 0.2] across layers |
| **Training Dataset** | Spider dataset format |
| **Loss Function** | BCEWithLogitsLoss |

### Schema Graph Structure

The database schema is converted to a graph with:
- **Global Node**: Root node connecting all tables
- **Table Nodes**: One per database table
- **Column Nodes**: One per column, linked to parent table
- **Edge Types**: 
  - Global ↔ Table (bidirectional)
  - Table ↔ Column (bidirectional)
  - Global ↔ Column (bidirectional)
  - Foreign Key relationships (bidirectional)

### Node Feature Engineering

Each node is encoded with:
1. **Sparse Features** (5-dim): `[is_global, is_table, is_column, is_pk, is_fk]`
2. **Dense Embeddings** (384-dim): SentenceTransformer encoding of node text
3. **Question Context** (768-dim): BERT encoding of the natural language query

Total input dimension: **389 (node) + 768 (question) = 1157**

### Benefits of the Hybrid Approach

| Metric | LLM-Only | Hybrid GNN+LLM |
|--------|----------|----------------|
| Token Usage | Full schema | ~60-80% reduction |
| Accuracy on Large Schemas | Degraded | Maintained |
| Relationship Understanding | Limited | Native graph encoding |
| Response Time | Longer prompts | Faster (smaller prompts) |
| API Costs | Higher | Significantly reduced |

---

## Key Features

### 🧠 Intelligent Schema Understanding
- GNN-based schema pruning identifies relevant tables and columns
- Understands foreign key relationships and table connections
- Automatic fallback for critical columns (dates for duration, numbers for aggregation)

### 🔄 Multi-Stage Pipeline
- **NL → IR**: Natural language to Intermediate Representation
- **IR → SQL**: Type-safe compilation to MySQL
- **Validation**: Automatic schema validation and error correction

### 📚 RAG-Enhanced Learning
- Vector storage of successful query-SQL pairs (Qdrant)
- Retrieval of similar past queries for improved accuracy
- User feedback integration for continuous improvement

### 💬 Conversational Context
- Multi-turn conversation support
- Reference resolution ("it", "those", etc.)
- Context-aware query interpretation

### 🛡️ Security Features
- Parameterized query generation
- SQL injection prevention
- Input validation and sanitization

### 📊 Data Ingestion
- CSV and Excel file upload support
- Automatic schema extraction
- Dynamic table creation

### 🔌 Multiple LLM Backends
- **Gemini**: Google's Gemini models (default)
- **Ollama**: Self-hosted local models (Mistral, etc.)
- Easy provider switching via configuration

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                            FRONTEND                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                React + TypeScript + TailwindCSS              │   │
│  │  • Dashboard • NL2SQL Playground • Schema Explorer           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ REST API
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                            BACKEND                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                      FastAPI Application                     │   │
│  │                                                              │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │   │
│  │  │   API v1     │  │   Services   │  │     Core         │   │   │
│  │  │  • nl2sql    │  │  • Pipeline  │  │  • Config        │   │   │
│  │  │  • feedback  │  │  • GNN       │  │  • Dependencies  │   │   │
│  │  │  • schema    │  │  • LLM       │  │  • Security      │   │   │
│  │  │  • data      │  │  • Embedding │  │                  │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│      MySQL       │   │     Qdrant       │   │      Redis       │
│   Target DB      │   │   Vector DB      │   │     Cache        │
│                  │   │  (RAG Storage)   │   │                  │
└──────────────────┘   └──────────────────┘   └──────────────────┘
```

### Core Services

| Service | Description |
|---------|-------------|
| **PipelineOrchestrator** | Coordinates the full NL2SQL pipeline execution |
| **GNNRankerService** | Runs GNN inference for schema pruning |
| **LLMService** | Interfaces with Gemini/Ollama for SQL generation |
| **SchemaService** | Extracts and caches database schemas |
| **FeedbackService** | Manages RAG feedback storage and retrieval |
| **ContextService** | Handles multi-turn conversation context |
| **IRCompiler** | Compiles Intermediate Representation to MySQL |
| **CorrectorService** | Validates and corrects generated SQL |

---

## Technology Stack

### Backend
| Technology | Purpose |
|------------|---------|
| **Python 3.11+** | Core language |
| **FastAPI** | REST API framework |
| **PyTorch 2.2** | Deep learning framework |
| **PyTorch Geometric** | GNN implementation |
| **SentenceTransformers** | Node embeddings |
| **Transformers (BERT)** | Question embeddings |
| **SQLAlchemy** | Database ORM |
| **Pydantic** | Data validation |

### Frontend
| Technology | Purpose |
|------------|---------|
| **React 18.2+** | UI framework |
| **TypeScript** | Type safety |
| **Vite** | Build tool |
| **TailwindCSS** | Styling |
| **React Query** | Data fetching |
| **Monaco Editor** | SQL/JSON editing |

### Infrastructure
| Technology | Purpose |
|------------|---------|
| **Docker Compose** | Container orchestration |
| **MySQL 8** | Target database |
| **PostgreSQL 15** | Application metadata |
| **Redis 7** | Caching |
| **Qdrant** | Vector database for RAG |

---

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Git
- (Optional) NVIDIA GPU for faster GNN inference

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/ashmay29/NL2SQL.git
   cd NL2SQL
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings (especially GEMINI_API_KEY)
   ```

3. **Start the system**
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

4. **Access the application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Qdrant Dashboard: http://localhost:6333/dashboard

### Manual Setup

If you prefer manual setup without Docker:

1. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   ```

3. **Start Services**
   ```bash
   # Terminal 1: Backend
   cd backend
   uvicorn app.main:app --reload --port 8000

   # Terminal 2: Frontend
   cd frontend
   npm run dev
   ```

---

## Configuration

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```bash
# Application
APP_ENV=development
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# Databases
MYSQL_URI=mysql+pymysql://root:password@mysql:3306/nl2sql_target
APP_DB_URI=postgresql://postgres:password@postgres:5432/nl2sql_app
REDIS_URI=redis://redis:6379/0
QDRANT_URL=http://qdrant:6333

# LLM Configuration
LLM_PROVIDER=gemini                    # gemini | ollama
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash
OLLAMA_ENDPOINT=http://localhost:11434
OLLAMA_MODEL=mistral:latest

# GNN Model
USE_LOCAL_GNN=true
GNN_MODEL_PATH=/app/models/gnn/best_model.pt
GNN_DEVICE=auto                        # auto | cuda | cpu
GNN_NODE_FEATURE_DIM=5
GNN_HIDDEN_CHANNELS=256

# Schema Processing
COMPACT_SCHEMA=true
MAX_COLUMNS_IN_PROMPT=8

# Embeddings
EMBEDDING_PROVIDER=enhanced            # mock | gnn | enhanced
EMBEDDING_DIM=512
```

### GNN Model Configuration

The GNN model weights should be placed at:
```
backend/models/gnn/best_model.pt
```

Model configuration is stored in:
```
backend/models/gnn/config.json
```

---

## API Reference

### Core Endpoints

#### POST `/api/v1/nl2sql`
Convert natural language query to SQL.

**Request:**
```json
{
  "query_text": "Show me all customers from New York",
  "database_id": "uploaded_data",
  "conversation_id": "session-123",
  "use_cache": true
}
```

**Response:**
```json
{
  "original_question": "Show me all customers from New York",
  "resolved_question": "Show me all customers from New York",
  "sql": "SELECT * FROM `customers` WHERE `city` = 'New York'",
  "params": {},
  "ir": { ... },
  "confidence": 0.95,
  "explanations": [],
  "execution_time": 1.23
}
```

#### POST `/api/v1/nl2ir`
Convert natural language to Intermediate Representation.

#### POST `/api/v1/ir2sql`
Compile Intermediate Representation to SQL.

#### POST `/api/v1/feedback/submit`
Submit user feedback for RAG enhancement.

#### POST `/api/v1/data/upload/csv`
Upload CSV/Excel files for querying.

#### GET `/api/v1/schema/{database_id}`
Get database schema information.

#### GET `/health`
System health check.

---

## Usage Examples

### Example 1: Basic Query
```
Input: "Show me all orders from last month"

GNN Analysis:
  #1 [TABLE] Orders           | Score: 0.92
  #2 [COLUMN] Orders.date     | Score: 0.88
  #3 [COLUMN] Orders.id       | Score: 0.75

Generated SQL:
SELECT *
FROM `Orders`
WHERE `date` >= DATE_SUB(NOW(), INTERVAL 1 MONTH)
```

### Example 2: Aggregation Query
```
Input: "What is the average order value per customer?"

GNN Analysis:
  #1 [TABLE] Orders           | Score: 0.91
  #2 [TABLE] Customers        | Score: 0.87
  #3 [COLUMN] Orders.total    | Score: 0.85
  #4 [COLUMN] Orders.customer_id | Score: 0.82

Generated SQL:
SELECT 
    c.`name`,
    AVG(o.`total`) AS avg_order_value
FROM `Orders` o
INNER JOIN `Customers` c ON o.`customer_id` = c.`id`
GROUP BY c.`id`, c.`name`
```

### Example 3: Complex Join Query
```
Input: "Find the top 5 products by revenue in the Electronics category"

GNN Analysis:
  #1 [TABLE] Products         | Score: 0.94
  #2 [TABLE] OrderItems       | Score: 0.89
  #3 [TABLE] Categories       | Score: 0.86
  #4 [COLUMN] Products.category_id | Score: 0.83

Generated SQL:
SELECT 
    p.`name`,
    SUM(oi.`quantity` * oi.`price`) AS revenue
FROM `Products` p
INNER JOIN `OrderItems` oi ON p.`id` = oi.`product_id`
INNER JOIN `Categories` c ON p.`category_id` = c.`id`
WHERE c.`name` = 'Electronics'
GROUP BY p.`id`, p.`name`
ORDER BY revenue DESC
LIMIT 5
```

---

## Project Structure

```
NL2SQL/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── nl2sql.py          # NL2SQL endpoints
│   │   │       ├── feedback.py        # Feedback endpoints
│   │   │       ├── schema.py          # Schema endpoints
│   │   │       ├── data_ingestion.py  # File upload endpoints
│   │   │       └── gnn.py             # GNN endpoints
│   │   ├── core/
│   │   │   ├── config.py              # Configuration
│   │   │   ├── dependencies.py        # Dependency injection
│   │   │   └── security.py            # Auth/security
│   │   ├── models/
│   │   │   └── schemas.py             # Pydantic models
│   │   ├── services/
│   │   │   ├── pipeline_orchestrator.py  # Main pipeline
│   │   │   ├── gnn_ranker_service.py     # GNN inference
│   │   │   ├── schema_converter.py       # Schema conversion
│   │   │   ├── llm_service.py            # LLM integration
│   │   │   ├── ir_models.py              # IR data models
│   │   │   ├── ir_compiler.py            # IR to SQL compiler
│   │   │   ├── feedback_service.py       # RAG feedback
│   │   │   ├── context_service.py        # Conversation context
│   │   │   ├── embedding_service.py      # Text embeddings
│   │   │   └── qdrant_service.py         # Vector DB
│   │   └── main.py                    # FastAPI app entry
│   ├── models/
│   │   └── gnn/
│   │       ├── best_model.pt          # Trained GNN weights
│   │       ├── config.json            # Model configuration
│   │       └── README.md              # Model documentation
│   ├── db/
│   │   └── mysql/                     # MySQL init scripts
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/                       # API client
│   │   ├── components/                # React components
│   │   ├── contexts/                  # React contexts
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx          # Home page
│   │   │   ├── NLSQLPlayground.tsx    # Main playground
│   │   │   └── SchemaExplorer.tsx     # Schema viewer
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── start.sh
├── .env.example
├── test_gnn_integration.py           # GNN integration tests
└── README.md
```

---

## Testing

### Run GNN Integration Tests
```bash
python test_gnn_integration.py
```

This tests:
1. Schema conversion (Backend → Spider format)
2. GNN Ranker service initialization and inference
3. Hybrid LLM+GNN pipeline integration

### Expected Output
```
🧪 GNN INTEGRATION TEST SUITE ==============================
============================================================
TEST 1: Schema Conversion
============================================================
✅ Schema validation passed!

============================================================
TEST 2: GNN Ranker Service
============================================================
✅ GNN Ranker test passed!

============================================================
TEST 3: Hybrid LLM+GNN Pipeline
============================================================
✅ Hybrid LLM+GNN pipeline test passed!

============================================================
TEST SUMMARY
============================================================
  Schema Conversion: ✅ PASSED
  GNN Ranker Service: ✅ PASSED
  Hybrid LLM+GNN Pipeline: ✅ PASSED

🎉 All tests passed! GNN integration is working correctly.
```

---

## Performance Optimizations

### Schema Pruning Benefits
- Typical schema reduction: 60-80% fewer tokens
- Faster LLM response times
- Lower API costs

### Caching Strategy
- **Redis**: Schema cache, query results
- **Qdrant**: Vector embeddings for RAG

### Intelligent Fallback
The system includes automatic fallback mechanisms:
1. FK-based table inclusion for JOINs
2. Date columns for duration queries
3. Numeric columns for aggregation queries

---

## Troubleshooting

### Common Issues

**GNN Model Not Found**
```
⚠️  Model file not found at backend/models/gnn/best_model.pt
```
Solution: Copy your trained model weights to the specified path.

**Gemini API Rate Limiting**
```
Gemini 429 Resource exhausted
```
Solution: The system includes automatic retry with exponential backoff. Consider upgrading API tier.

**Schema Extraction Failed**
```
No schema found for database 'your_db'
```
Solution: Upload a CSV file first, or ensure MySQL database is accessible.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Acknowledgments

- Spider Dataset for GNN training data format
- PyTorch Geometric for GNN implementation
- Google Gemini and Ollama for LLM backends
- Qdrant for vector similarity search

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Made with ❤️ for democratizing database access through natural language
</p>
