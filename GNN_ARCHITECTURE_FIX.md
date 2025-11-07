# GNN Architecture Fix - Matching Training Code Exactly

## Problem Summary

The backend GNN implementation had **multiple critical mismatches** with the training code:

1. **Input Dimension Mismatch**: Model expected 389 dims, checkpoint had 1157 dims
2. **Architecture Mismatch**: Used 2-layer GCN, training used 3-layer GAT
3. **Question Injection Point**: Injected after GNN, training injects at INPUT
4. **Embedding Models**: Used all-MiniLM for both, training uses all-MiniLM (nodes) + BERT (questions)
5. **Node Features**: Only sparse features, training uses sparse + SentenceTransformer embeddings

## Training Architecture (Actual from user's code)

```python
# From user's main.py and utils.py
class GATModel(nn.Module):
    def __init__(self):
        # Node features: 5 sparse + 384 SentenceTransformer = 389
        # Question: 768-dim BERT (bert-base-uncased)
        # TOTAL INPUT = 389 + 768 = 1157
        
        self.input_proj = nn.Linear(1157, 256)  # Project concatenated input
        
        # 3 GAT layers with 4 attention heads, concat=False
        self.conv1 = GATConv(256, 256, heads=4, concat=False)
        self.conv2 = GATConv(256, 256, heads=4, concat=False)
        self.conv3 = GATConv(256, 256, heads=4, concat=False)
        
        # Dropout schedule: [0.3, 0.3, 0.2]
        self.classifier = nn.Linear(256, 1)
    
    def forward(self, x, edge_index, question_emb, batch):
        # x: [N, 389] = 5 sparse + 384 node embedding
        # question_emb: [batch_size, 768]
        
        # 1. Inject question at INPUT (before GAT)
        q_expanded = question_emb[batch]  # [N, 768]
        combined = torch.cat([x, q_expanded], dim=1)  # [N, 1157]
        
        # 2. Input projection
        h = self.input_proj(combined).relu()  # [N, 256]
        
        # 3. GAT layers with dropout
        h = self.conv1(h, edge_index).relu()
        h = F.dropout(h, p=0.3, training=self.training)
        
        h = self.conv2(h, edge_index).relu()
        h = F.dropout(h, p=0.3, training=self.training)
        
        h = self.conv3(h, edge_index).relu()
        h = F.dropout(h, p=0.2, training=self.training)
        
        # 4. Classifier
        logits = self.classifier(h)  # [N, 1]
        return logits  # BCEWithLogitsLoss during training
```

### Node Feature Preparation (Training Code)

```python
def get_node_text_embedding(node_name, node_type, sentence_model):
    """From training code - creates 389-dim features per node"""
    # 5 sparse features: [is_global, is_table, is_column, is_pk, is_fk]
    sparse = [...]  # 5-dim
    
    # Node text (different for each type)
    if node_name == "global":
        text = "global"
    elif node_type == "column":
        text = f"{table}.{column} ({type})"  # e.g. "users.id (number)"
    else:  # table
        text = table_name  # e.g. "users"
    
    # Encode with SentenceTransformer
    node_emb = sentence_model.encode(text)  # 384-dim
    
    # Concatenate: [5 + 384] = 389
    return np.concatenate([sparse, node_emb])

def extract_bert_embeddings(question):
    """From training code - creates 768-dim question embeddings"""
    tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
    model = AutoModel.from_pretrained('bert-base-uncased')
    
    inputs = tokenizer(question, return_tensors='pt', padding=True)
    outputs = model(**inputs)
    
    # Mean pooling over sequence
    embeddings = outputs.last_hidden_state.mean(dim=1)  # [1, 768]
    return embeddings
```

## Backend Fixes Applied

### 1. Model Architecture (`gnn_ranker_service.py`)

**Changed:**
```python
# OLD: 2-layer GCN with question injection AFTER
class GNNRanker(torch.nn.Module):
    def __init__(self, node_in_channels, q_in_channels, hidden_channels):
        self.conv1 = GCNConv(node_in_channels, hidden_channels)
        self.conv2 = GCNConv(hidden_channels, hidden_channels)
        self.classifier = Linear(hidden_channels + q_in_channels, 1)
```

**To:**
```python
# NEW: 3-layer GAT with question injection at INPUT
class GNNRanker(torch.nn.Module):
    def __init__(self, node_in_channels, q_in_channels, hidden_channels):
        # Input projection: node (389) + question (768) = 1157
        self.input_proj = Linear(node_in_channels + q_in_channels, hidden_channels)
        
        # 3 GAT layers with 4 heads, concat=False
        self.conv1 = GATConv(hidden_channels, hidden_channels, heads=4, concat=False)
        self.conv2 = GATConv(hidden_channels, hidden_channels, heads=4, concat=False)
        self.conv3 = GATConv(hidden_channels, hidden_channels, heads=4, concat=False)
        
        # Dropout schedule
        self.dropout1 = 0.3
        self.dropout2 = 0.3
        self.dropout3 = 0.2
        
        self.classifier = Linear(hidden_channels, 1)
    
    def forward(self, x, edge_index, question_embedding, batch_index):
        # 1. Inject question at INPUT
        q_emb_expanded = question_embedding[batch_index]
        combined = torch.cat([x, q_emb_expanded], dim=1)  # [N, 1157]
        
        # 2. Input projection
        h = self.input_proj(combined).relu()
        
        # 3. GAT layers with dropout
        h = self.conv1(h, edge_index).relu()
        h = F.dropout(h, p=self.dropout1, training=self.training)
        
        h = self.conv2(h, edge_index).relu()
        h = F.dropout(h, p=self.dropout2, training=self.training)
        
        h = self.conv3(h, edge_index).relu()
        h = F.dropout(h, p=self.dropout3, training=self.training)
        
        # 4. Classifier
        logits = self.classifier(h)
        
        # Apply sigmoid for inference
        if not self.training:
            return torch.sigmoid(logits).squeeze(-1)
        return logits.squeeze(-1)
```

### 2. Embedding Models

**Changed:**
```python
# OLD: SentenceTransformer for both nodes and questions (384-dim)
self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
```

**To:**
```python
# NEW: SentenceTransformer for nodes (384-dim) + BERT for questions (768-dim)
# Node embeddings
self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')

# Question embeddings (BERT)
from transformers import AutoTokenizer, AutoModel
self.bert_tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
self.bert_model = AutoModel.from_pretrained('bert-base-uncased')
```

### 3. Node Feature Preprocessing

**Changed:**
```python
# OLD: Only 5-dim sparse features OR 3x384 embeddings (incorrect)
node_features = [is_global, is_table, is_column, is_pk, is_fk]  # 5-dim
# OR
combined = sparse + table_emb + col_name_emb + col_type_emb  # 1157-dim (wrong!)
```

**To:**
```python
# NEW: Sparse + single SentenceTransformer embedding = 389-dim
def _add_node_embeddings(...):
    """
    For each node:
    - 5-dim sparse: [is_global, is_table, is_column, is_pk, is_fk]
    - 384-dim text embedding from SentenceTransformer
    - Total: 389-dim
    
    Node text format:
    - Global: "global"
    - Table: "table_name"
    - Column: "table_name.column_name (column_type)"
    """
    node_texts = []
    for node_name, col_type in zip(node_names, col_types):
        if node_name == "global":
            text = "global"
        elif '.' in node_name:
            text = f"{node_name} ({col_type})" if col_type else node_name
        else:
            text = node_name
        node_texts.append(text)
    
    # Batch encode all nodes
    node_embeddings = self.sentence_model.encode(node_texts)  # [N, 384]
    
    # Concatenate sparse + dense
    enriched = [
        torch.cat([sparse_tensor, node_emb])  # [5 + 384] = 389
        for sparse, node_emb in zip(sparse_features, node_embeddings)
    ]
    return torch.stack(enriched)
```

### 4. Question Embedding

**Changed:**
```python
# OLD: SentenceTransformer (384-dim)
def _get_query_embedding(self, query: str):
    embedding = self.sentence_model.encode(query)  # [384]
    return embedding.unsqueeze(0)  # [1, 384]
```

**To:**
```python
# NEW: BERT with mean pooling (768-dim)
def _get_query_embedding(self, query: str):
    # Tokenize
    inputs = self.bert_tokenizer(
        query,
        return_tensors='pt',
        padding=True,
        truncation=True,
        max_length=512
    ).to(self.device)
    
    # Get BERT outputs
    with torch.no_grad():
        outputs = self.bert_model(**inputs)
    
    # Mean pooling over sequence
    embeddings = outputs.last_hidden_state.mean(dim=1)  # [1, 768]
    return embeddings
```

### 5. Dependencies (`requirements.txt`)

**Added:**
```
transformers==4.37.2
```

## Dimension Flow Verification

### Training Code
1. **Node Features**: 5 sparse + 384 SentenceTransformer = **389 dims**
2. **Question Embedding**: 768 BERT = **768 dims**
3. **Concatenated Input**: 389 + 768 = **1157 dims**
4. **Input Projection**: Linear(1157, 256)
5. **Checkpoint**: `input_proj.weight` has shape `[256, 1157]` ✅

### Backend (After Fix)
1. **Node Features**: 5 sparse + 384 SentenceTransformer = **389 dims**
2. **Question Embedding**: 768 BERT = **768 dims**
3. **Concatenated Input**: 389 + 768 = **1157 dims**
4. **Input Projection**: Linear(1157, 256)
5. **Model expects**: `input_proj.weight` shape `[256, 1157]` ✅

**Dimensions now match exactly!**

## Testing

### Test the Fixed Model

```python
# Test script
import sys
sys.path.append('d:/IDE/code/projects/personal/NL2SQL/backend')

from app.services.gnn_ranker_service import GNNRankerService

# Initialize service
service = GNNRankerService(
    model_path="c:/Users/seque/OneDrive/Desktop/best_model.pt",
    device='cpu',
    use_rich_node_embeddings=True
)

# Check model info
info = service.get_model_info()
print("Model Info:")
for k, v in info.items():
    print(f"  {k}: {v}")

# Expected output:
# architecture: 3-layer GAT (4 heads, concat=False) with question injection at input
# total_input_dim: 389 (node) + 768 (question) = 1157
# status: loaded
```

### Verify Checkpoint Loading

The model should now load **without dimension mismatch errors**:
```
✅ GNN weights loaded successfully
✅ No missing/unexpected keys (or only non-critical ones)
```

### Run Inference

```python
# Test schema scoring
backend_schema = {
    "db_id": "test_db",
    "tables": [...],
    "columns": [...]
}

results = await service.score_schema_nodes(
    query="Show me all users",
    backend_schema=backend_schema,
    top_k=10
)

print(f"Top {len(results)} relevant nodes:")
for r in results:
    print(f"  {r['rank']}. {r['node_name']} ({r['node_type']}) - score: {r['score']:.3f}")
```

## Summary of Changes

| Component | Before | After |
|-----------|--------|-------|
| **Model Type** | 2-layer GCN | 3-layer GAT (4 heads) |
| **Question Injection** | After GNN layers | At input (concatenated) |
| **Node Features** | 5-dim sparse OR 1157-dim (wrong) | 389-dim (5 sparse + 384 dense) |
| **Question Embedding** | 384-dim SentenceTransformer | 768-dim BERT |
| **Total Input** | 389 OR 1157 (mismatched) | 1157 (node 389 + question 768) |
| **Dropout** | 0.5 uniform | [0.3, 0.3, 0.2] per layer |
| **Node Text Format** | Generic | Specific per node type |
| **Dependencies** | sentence-transformers only | + transformers (BERT) |

## Next Steps

1. ✅ **Architecture Fixed** - Model now matches training exactly
2. ✅ **Embeddings Fixed** - Using correct models (SentenceTransformer + BERT)
3. ✅ **Dimensions Fixed** - 1157-dim input matches checkpoint
4. 🔄 **Test Loading** - Verify checkpoint loads without errors
5. 🔄 **Test Inference** - Run on sample schema and query
6. 🔄 **Integration Test** - Test with full NL2SQL pipeline

## Files Modified

1. `backend/app/services/gnn_ranker_service.py` - Complete rewrite to match training
2. `backend/requirements.txt` - Added transformers library
3. `GNN_ARCHITECTURE_FIX.md` - This documentation

---

**Status**: ✅ Ready for testing

The backend GNN implementation now **exactly matches** the training code architecture, embedding models, and dimension flow. The checkpoint should load successfully and inference should work correctly.
