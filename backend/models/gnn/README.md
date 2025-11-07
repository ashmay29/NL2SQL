# GNN Model Weights

## Setup Instructions

1. **Copy your trained model weights here:**
   ```
   backend/models/gnn/best_model.pt
   ```

2. **Model Architecture:**
   - **Type:** GNNRanker (3-layer GAT with Question Injection)
   - **Graph Layers:** 3x GATConv with 4 attention heads each
   - **Node Features:** 5-dimensional [is_global, is_table, is_column, is_pk, is_fk]
   - **Query Embedding:** 384-dimensional (SentenceTransformer: all-MiniLM-L6-v2)
   - **Hidden Channels:** 256
   - **Attention Heads:** 4 per GAT layer (concat=False)
   - **Dropout:** [0.3, 0.3, 0.2] across layers
   - **Output:** Node relevance logits → Sigmoid scores (0-1)

3. **Expected File:**
   - Name: `best_model.pt` (or configure via `GNN_MODEL_PATH` in `.env`)
   - Format: PyTorch state_dict
   - Size: ~3-6 MB (larger than GCN due to attention mechanisms)

4. **Configuration (.env):**
   ```bash
   # Local GNN Model
   USE_LOCAL_GNN=true
   GNN_MODEL_PATH=/app/models/gnn/best_model.pt
   GNN_DEVICE=auto  # auto, cuda, or cpu
   GNN_NODE_FEATURE_DIM=5
   GNN_HIDDEN_CHANNELS=256
   ```

5. **Verify Installation:**
   ```bash
   # Check if model file exists
   ls -lh backend/models/gnn/best_model.pt
   
   # Test GNN loading (from backend directory)
   python -c "import torch; torch.load('models/gnn/best_model.pt'); print('Model loaded successfully!')"
   ```

## Model Training

If you need to train a new model:

1. Use the `utils.py` and training scripts from your desktop
2. Save the trained weights as `best_model.pt`
3. Copy to this directory
4. Restart the backend service

## Fallback Behavior

If the model file is not found:
- ⚠️ Warning will be logged
- System will use SentenceTransformer embeddings only
- No errors, degraded performance

## Docker Volume Mapping

When deploying with Docker, mount this directory:

```yaml
# docker-compose.yml
services:
  backend:
    volumes:
      - ./backend/models/gnn:/app/models/gnn:ro  # Read-only mount
```

This allows you to update the model without rebuilding the container.
