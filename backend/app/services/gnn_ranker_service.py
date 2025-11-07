"""
GNN Ranker Service
Integrates the trained GNN model for schema node ranking
Based on GAT (Graph Attention Network) architecture with question injection
"""
from typing import Dict, Any, List, Optional, Tuple
import logging
import torch
import torch.nn.functional as F
from torch.nn import Linear
from torch_geometric.nn import GATConv
from torch_geometric.data import Data, Batch
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel
import numpy as np
import os

from app.services.schema_converter import SchemaConverter

logger = logging.getLogger(__name__)


class GNNRanker(torch.nn.Module):
    """
    GNN Ranker Model - 3-layer GAT with question injection at INPUT
    Architecture: GAT with Question Embedding Concatenation at Input Layer
    
    Matches EXACT training code from user's main.py/utils.py:
    - Question injected at INPUT: torch.cat([node_features, question_emb], dim=1)
    - Input projection: Linear(1157, hidden) where 1157 = 5 + 384*3 (node) + 768 (question)
    - 3 GAT layers with 4 attention heads (concat=False)
    - Dropout: [0.3, 0.3, 0.2]
    - Output: Linear(hidden, 1) → Logits (BCEWithLogitsLoss during training)
    """
    def __init__(self, node_in_channels: int, q_in_channels: int, hidden_channels: int):
        super().__init__()
        # Input projection: concatenated [node_features + question_emb]
        # node_in_channels = 5 + 384*3 = 1157 (sparse + rich node embeddings)
        # q_in_channels = 768 (BERT question embedding)
        # Total input = 1157 + 768 = 1925... WAIT, training code shows 1157 total!
        # Let me re-check: node features are 389 (5 + 384), question is 768
        # torch.cat([x, q_emb_expanded], dim=1) = [389 + 768] = 1157
        # So node_in_channels should be 389, not 1157!
        self.input_proj = Linear(node_in_channels + q_in_channels, hidden_channels)
        
        # 3 GAT layers with 4 attention heads, concat=False
        self.conv1 = GATConv(hidden_channels, hidden_channels, heads=4, concat=False)
        self.conv2 = GATConv(hidden_channels, hidden_channels, heads=4, concat=False)
        self.conv3 = GATConv(hidden_channels, hidden_channels, heads=4, concat=False)
        
        # Dropout rates for each layer
        self.dropout1 = 0.3
        self.dropout2 = 0.3
        self.dropout3 = 0.2
        
        # Output classifier
        self.classifier = Linear(hidden_channels, 1)

    def forward(self, x, edge_index, question_embedding, batch_index):
        """
        Forward pass matching training code
        
        Args:
            x: Node features [total_nodes, node_in_channels]
            edge_index: Graph edges [2, num_edges]
            question_embedding: Question embeddings [batch_size, q_in_channels]
            batch_index: Batch assignment for each node [total_nodes]
        
        Returns:
            node_scores: Logits [total_nodes, 1] (use sigmoid for inference)
        """
        # 1. Inject question embedding at INPUT (expand to all nodes)
        q_emb_expanded = question_embedding[batch_index]  # [total_nodes, q_in_channels]
        combined = torch.cat([x, q_emb_expanded], dim=1)  # [total_nodes, node_in + q_in]
        
        # 2. Input projection
        h = self.input_proj(combined).relu()
        
        # 3. GAT layers with dropout
        h = self.conv1(h, edge_index).relu()
        h = F.dropout(h, p=self.dropout1, training=self.training)
        
        h = self.conv2(h, edge_index).relu()
        h = F.dropout(h, p=self.dropout2, training=self.training)
        
        h = self.conv3(h, edge_index).relu()
        h = F.dropout(h, p=self.dropout3, training=self.training)
        
        # 4. Classifier (output logits)
        logits = self.classifier(h)
        
        # During inference, apply sigmoid to get probabilities
        if not self.training:
            return torch.sigmoid(logits).squeeze(-1)
        return logits.squeeze(-1)


class GNNRankerService:
    """
    Service for GNN-based schema node ranking
    
    Workflow:
    1. Backend schema → Spider format (via SchemaConverter)
    2. Spider schema → PyG graph (nodes + edges)
    3. Query text → SentenceTransformer embedding
    4. Graph + Query → GNN forward pass → Node scores
    5. Return top-K relevant nodes
    """
    
    def __init__(
        self,
        model_path: str,
        device: str = 'auto',
        node_feature_dim: int = 5,
        node_embedding_dim: int = 384,
        question_embedding_dim: int = 768,
        hidden_channels: int = 256,
        use_rich_node_embeddings: bool = True
    ):
        """
        Initialize GNN Ranker Service
        
        Args:
            model_path: Path to trained model weights (best_model.pt)
            device: 'cuda', 'cpu', or 'auto' (auto-detect)
            node_feature_dim: Sparse node feature dimension (5 for: global, table, column, is_pk, is_fk)
            node_embedding_dim: SentenceTransformer embedding dimension for nodes (384)
            question_embedding_dim: BERT embedding dimension for questions (768)
            hidden_channels: GNN hidden layer dimension (256)
            use_rich_node_embeddings: If True, use SentenceTransformer embeddings for nodes (389 total)
        """
        # Device selection
        if device == 'auto':
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        self.use_rich_node_embeddings = use_rich_node_embeddings
        self.node_embedding_dim = node_embedding_dim
        self.question_embedding_dim = question_embedding_dim
        logger.info(f"GNN Ranker using device: {self.device}")
        
        # Initialize SentenceTransformer for NODE embeddings (384-dim)
        logger.info("Loading SentenceTransformer model for node embeddings...")
        self.sentence_model = SentenceTransformer(
            'sentence-transformers/all-MiniLM-L6-v2',
            device=str(self.device)
        )
        
        # Initialize BERT for QUESTION embeddings (768-dim) - matching training code
        logger.info("Loading BERT model for question embeddings...")
        self.bert_tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
        self.bert_model = AutoModel.from_pretrained('bert-base-uncased').to(self.device)
        self.bert_model.eval()
        
        # Calculate actual node input dimension
        if use_rich_node_embeddings:
            # node_in = 5 (sparse) + 384 (SentenceTransformer) = 389
            actual_node_in = node_feature_dim + node_embedding_dim
        else:
            actual_node_in = node_feature_dim
        
        # Initialize GNN model
        # Total input to model = node_in (389) + question_in (768) = 1157
        logger.info("Initializing GNN Ranker model...")
        logger.info(f"  Node input dim: {actual_node_in} (5 sparse + {node_embedding_dim} dense)")
        logger.info(f"  Question input dim: {question_embedding_dim} (BERT)")
        logger.info(f"  Total concatenated input: {actual_node_in + question_embedding_dim}")
        
        self.model = GNNRanker(
            node_in_channels=actual_node_in,
            q_in_channels=question_embedding_dim,
            hidden_channels=hidden_channels
        )
        
        # Load trained weights (support checkpoints saved as dict bundles)
        if os.path.exists(model_path):
            logger.info(f"Loading GNN weights from {model_path}")
            try:
                checkpoint = torch.load(model_path, map_location=self.device)

                # Extract actual state_dict if checkpoint is a training bundle
                if isinstance(checkpoint, dict):
                    if 'model_state_dict' in checkpoint:
                        state_dict = checkpoint['model_state_dict']
                    elif 'state_dict' in checkpoint:
                        state_dict = checkpoint['state_dict']
                    else:
                        # Could be a raw state dict or nested; assume raw then try to detect
                        state_dict = checkpoint
                else:
                    state_dict = checkpoint

                # Helper: strip 'module.' prefix from DataParallel checkpoints
                def _strip_module_prefix(sd: Dict[str, Any]) -> Dict[str, Any]:
                    stripped = {}
                    for k, v in sd.items():
                        nk = k[len('module.'):] if k.startswith('module.') else k
                        stripped[nk] = v
                    return stripped

                # If the loaded dict contains non-tensor values, try to find nested model_state_dict
                if isinstance(state_dict, dict):
                    sample_vals = list(state_dict.values())[:5]
                    if sample_vals and not any(hasattr(v, 'size') for v in sample_vals):
                        # search for nested dict that looks like a state_dict
                        for k, v in state_dict.items():
                            if isinstance(v, dict) and any(hasattr(x, 'size') for x in list(v.values())[:5]):
                                state_dict = v
                                break

                    # Strip possible 'module.' prefixes
                    state_dict = _strip_module_prefix(state_dict)

                # Finally load the model weights
                # Use strict=False to handle dimension mismatches gracefully
                missing_keys, unexpected_keys = self.model.load_state_dict(state_dict, strict=False)
                
                # Log detailed information about loading
                logger.info(f"Checkpoint keys loaded: {len(state_dict)}")
                logger.info(f"Sample checkpoint keys: {list(state_dict.keys())[:5]}")
                
                if missing_keys:
                    logger.warning(f"⚠️  Missing {len(missing_keys)} keys in checkpoint (will use random init):")
                    logger.warning(f"    {missing_keys[:5]}")
                    if len(missing_keys) > 5:
                        logger.warning(f"    ... and {len(missing_keys) - 5} more")
                if unexpected_keys:
                    logger.warning(f"⚠️  Unexpected {len(unexpected_keys)} keys in checkpoint (ignored):")
                    logger.warning(f"    {unexpected_keys[:5]}")
                    if len(unexpected_keys) > 5:
                        logger.warning(f"    ... and {len(unexpected_keys) - 5} more")
                
                if not missing_keys and not unexpected_keys:
                    logger.info("✅ All weights loaded successfully with exact match!")
                else:
                    logger.warning("⚠️  Weight loading had mismatches - model may not perform correctly")
                    
            except Exception as e:
                logger.error(f"Failed to load GNN weights: {e}")
                raise
        else:
            logger.warning(f"⚠️  Model file not found at {model_path}. Using UNTRAINED model.")
            logger.warning(f"    The model will output random scores!")
        
        self.model.to(self.device)
        self.model.eval()  # Set to evaluation mode
        
        logger.info("GNN Ranker Service initialized successfully")
    
    async def score_schema_nodes(
        self,
        query: str,
        backend_schema: Dict[str, Any],
        top_k: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Score schema nodes by relevance to query using GNN
        
        Args:
            query: Natural language query
            backend_schema: Schema in backend format
            top_k: Number of top nodes to return
            
        Returns:
            List of dicts with node info and scores:
            [
                {
                    "node_id": "table:customers",
                    "node_name": "Customers",
                    "node_type": "table",
                    "score": 0.92,
                    "rank": 1
                },
                ...
            ]
        """
        try:
            # Step 1: Convert backend schema to Spider format
            logger.info(f"Converting backend schema to Spider format...")
            spider_schema = SchemaConverter.convert_to_spider_format(backend_schema)
            SchemaConverter.validate_spider_schema(spider_schema)
            logger.info(f"Schema converted: {len(spider_schema['table_names_original'])} tables, {len(spider_schema['column_names_original'])} columns")
            
            # Step 2: Create PyG graph from Spider schema
            logger.info(f"Creating PyG graph from schema...")
            graph = self._create_schema_graph(spider_schema)
            logger.info(f"Graph created: {graph.x.shape[0]} nodes, {graph.edge_index.shape[1]} edges")
            logger.info(f"Node feature dimension: {graph.x.shape[1]} (expected: {5 + self.node_embedding_dim} = 389)")
            logger.info(f"Sample node names: {graph.node_names[:5]}")
            
            # Step 3: Get query embedding
            logger.info(f"Encoding query: '{query}'")
            query_embedding = self._get_query_embedding(query)
            logger.info(f"Query embedding shape: {query_embedding.shape} (expected: [1, 768])")
            
            # Step 4: Run GNN inference
            logger.info(f"Running GNN inference...")
            with torch.no_grad():
                # Create single-item batch
                batch_data = Batch.from_data_list([Data(
                    x=graph.x.clone(),
                    edge_index=graph.edge_index.clone(),
                    question_embedding=query_embedding.cpu()
                )]).to(self.device)
                
                logger.info(f"Batch data shapes:")
                logger.info(f"  x: {batch_data.x.shape}")
                logger.info(f"  edge_index: {batch_data.edge_index.shape}")
                logger.info(f"  question_embedding: {batch_data.question_embedding.shape}")
                logger.info(f"  batch: {batch_data.batch.shape}")
                
                # Forward pass
                scores = self.model(
                    x=batch_data.x,
                    edge_index=batch_data.edge_index,
                    question_embedding=batch_data.question_embedding,
                    batch_index=batch_data.batch
                ).squeeze().cpu()
                
                logger.info(f"GNN output scores shape: {scores.shape}")
                logger.info(f"Scores: min={scores.min():.7f}, max={scores.max():.7f}, mean={scores.mean():.7f}")
            
            # Step 5: Format results
            results = self._format_top_k_results(
                graph=graph,
                scores=scores,
                spider_schema=spider_schema,
                top_k=top_k
            )
            
            logger.info(f"GNN scored {len(results)} relevant nodes for query: '{query[:50]}...'")
            return results
            
        except Exception as e:
            logger.error(f"GNN scoring failed: {e}", exc_info=True)
            raise
    
    def _create_schema_graph(self, spider_schema: Dict[str, Any]) -> Data:
        """
        Convert Spider schema to PyG graph
        Based on create_schema_graph() from utils.py
        
        Node features:
        - Without rich embeddings: 5-dim [is_global, is_table, is_column, is_pk, is_fk]
        - With rich embeddings: 1157-dim [5 sparse + 384*3 dense (table+col_name+col_type embeddings)]
        """
        edges_src = []
        edges_dst = []
        node_features = []
        node_names = []
        col_types = []
        
        col_to_node_idx = {}
        table_to_node_idx = {}
        current_node_idx = 0
        
        # 1. Add global node
        node_features.append([1.0, 0.0, 0.0, 0.0, 0.0])
        node_names.append("global")
        col_types.append(None)
        global_node_idx = current_node_idx
        current_node_idx += 1
        
        pk_col_indices = set(spider_schema.get('primary_keys', []))
        fk_pairs = spider_schema.get('foreign_keys', [])
        fk_col_indices = set(fk[0] for fk in fk_pairs)
        
        # 2. Add table nodes
        table_names = spider_schema['table_names_original']
        for t_idx, t_name in enumerate(table_names):
            table_node_idx = current_node_idx
            table_to_node_idx[t_idx] = table_node_idx
            node_features.append([0.0, 1.0, 0.0, 0.0, 0.0])
            node_names.append(t_name)
            col_types.append(None)
            # Bidirectional edges: global <-> table
            edges_src.extend([global_node_idx, table_node_idx])
            edges_dst.extend([table_node_idx, global_node_idx])
            current_node_idx += 1
        
        # 3. Add column nodes
        column_data = spider_schema['column_names_original']
        column_type_data = spider_schema['column_types']
        
        for c_idx, (t_idx, c_name) in enumerate(column_data):
            current_col_key = (t_idx, c_idx)
            if c_name == '*':
                col_to_node_idx[current_col_key] = -1
                continue
            
            col_node_idx = current_node_idx
            col_to_node_idx[current_col_key] = col_node_idx
            table_node_idx = table_to_node_idx[t_idx]
            
            is_pk = 1.0 if c_idx in pk_col_indices else 0.0
            is_fk = 1.0 if c_idx in fk_col_indices else 0.0
            
            node_features.append([0.0, 0.0, 1.0, is_pk, is_fk])
            node_names.append(f"{table_names[t_idx]}.{c_name}")
            col_types.append(column_type_data[c_idx])
            
            # Edges: table <-> column
            edges_src.extend([table_node_idx, col_node_idx])
            edges_dst.extend([col_node_idx, table_node_idx])
            # Edges: global <-> column
            edges_src.extend([global_node_idx, col_node_idx])
            edges_dst.extend([col_node_idx, global_node_idx])
            current_node_idx += 1
        
        # 4. Add foreign key edges
        original_c_idx_to_key = {k[1]: k for k, v in col_to_node_idx.items() if v != -1}
        for (c_idx_1, c_idx_2) in fk_pairs:
            key1 = original_c_idx_to_key.get(c_idx_1)
            key2 = original_c_idx_to_key.get(c_idx_2)
            if key1 is None or key2 is None:
                continue
            node_1 = col_to_node_idx.get(key1)
            node_2 = col_to_node_idx.get(key2)
            if node_1 is not None and node_2 is not None:
                # Bidirectional FK edges
                edges_src.extend([node_1, node_2])
                edges_dst.extend([node_2, node_1])
        
        # 5. Enrich with text embeddings if enabled
        if self.use_rich_node_embeddings:
            logger.debug(f"Adding rich embeddings to {len(node_features)} nodes...")
            enriched_features = self._add_node_embeddings(
                sparse_features=node_features,
                node_names=node_names,
                col_types=col_types,
                table_names=table_names
            )
            x = enriched_features
        else:
            x = torch.tensor(node_features, dtype=torch.float)
        
        # Create PyG Data object
        edge_index = torch.tensor([edges_src, edges_dst], dtype=torch.long)
        
        graph = Data(x=x, edge_index=edge_index)
        graph.node_names = node_names
        graph.col_types = col_types
        graph.db_id = spider_schema['db_id']
        
        return graph
    
    def _add_node_embeddings(
        self,
        sparse_features: List[List[float]],
        node_names: List[str],
        col_types: List[Optional[str]],
        table_names: List[str]
    ) -> torch.Tensor:
        """
        Add rich text embeddings to sparse node features
        Matches training code's get_node_text_embedding() function
        
        For each node, concatenate:
        - 5-dim sparse features [is_global, is_table, is_column, is_pk, is_fk]
        - 384-dim SentenceTransformer embedding of node text
        Total: 5 + 384 = 389 dimensions
        
        Node text format (matching training code):
        - Global node: "global"
        - Table node: table_name
        - Column node: "table_name.column_name (column_type)"
        """
        enriched = []
        
        # Prepare texts for batch encoding
        node_texts = []
        for node_name, col_type in zip(node_names, col_types):
            if node_name == "global":
                text = "global"
            elif '.' in node_name:
                # Column node: "table.column (type)"
                if col_type:
                    text = f"{node_name} ({col_type})"
                else:
                    text = node_name
            else:
                # Table node: just table name
                text = node_name
            node_texts.append(text)
        
        # Batch encode all node texts
        logger.debug(f"Encoding {len(node_texts)} node texts with SentenceTransformer...")
        node_embeddings = self.sentence_model.encode(
            node_texts,
            convert_to_tensor=True,
            device=str(self.device),
            show_progress_bar=False
        )  # Shape: [num_nodes, 384]
        
        # Concatenate sparse features with embeddings
        for sparse, node_emb in zip(sparse_features, node_embeddings):
            sparse_tensor = torch.tensor(sparse, dtype=torch.float, device=self.device)
            combined = torch.cat([sparse_tensor, node_emb])  # [5 + 384] = 389
            enriched.append(combined)
        
        return torch.stack(enriched)
    
    def _get_query_embedding(self, query: str) -> torch.Tensor:
        """
        Get query embedding using BERT (bert-base-uncased)
        Matches training code's extract_bert_embeddings() function
        
        Returns: [1, 768] tensor
        """
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
        
        # Mean pooling over sequence (matching training code)
        # outputs.last_hidden_state shape: [1, seq_len, 768]
        # Mean over sequence dimension
        embeddings = outputs.last_hidden_state.mean(dim=1)  # [1, 768]
        
        return embeddings
    
    def _format_top_k_results(
        self,
        graph: Data,
        scores: torch.Tensor,
        spider_schema: Dict[str, Any],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Format GNN scores into structured results
        Returns top-K nodes regardless of score threshold
        """
        # Get top-K indices
        scores_np = scores.numpy()
        top_k = min(top_k, len(scores_np))
        top_indices = np.argsort(scores_np)[-top_k:][::-1]  # Descending order
        
        # Debug: Log score distribution
        logger.info(f"Score distribution: min={scores_np.min():.7f}, max={scores_np.max():.7f}, mean={scores_np.mean():.7f}")
        if len(scores_np) > 0:
            top_scores = sorted(scores_np, reverse=True)[:10] if len(scores_np) >= 10 else sorted(scores_np, reverse=True)
            logger.info(f"Top {len(top_scores)} scores: {top_scores}")
        
        results = []
        table_names = spider_schema['table_names_original']
        
        for rank, idx in enumerate(top_indices, start=1):
            node_name = graph.node_names[idx]
            score = float(scores_np[idx])
            
            # Debug: Log all top-K nodes before filtering
            logger.debug(f"  Rank {rank}: {node_name} = {score:.7f}")
            
            # Skip only the global node (always keep top-K nodes regardless of score)
            if node_name == "global":
                logger.debug(f"    Skipped (global node)")
                continue
            
            # Determine node type and create node_id
            if '.' in node_name:
                # Column node
                table_name, col_name = node_name.split('.', 1)
                node_type = "column"
                node_id = f"column:{table_name}.{col_name}"
            else:
                # Table node
                node_type = "table"
                node_id = f"table:{node_name}"
            
            results.append({
                "node_id": node_id,
                "node_name": node_name,
                "node_type": node_type,
                "score": score,
                "rank": len(results) + 1,  # Re-number after filtering global
                "col_type": graph.col_types[idx] if node_type == "column" else None
            })
        
        return results
        
        return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        return {
            "device": str(self.device),
            "model_type": "GNNRanker",
            "architecture": "3-layer GAT (4 heads, concat=False) with question injection at input",
            "node_embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "question_embedding_model": "bert-base-uncased",
            "node_embedding_dim": self.node_embedding_dim,
            "question_embedding_dim": self.question_embedding_dim,
            "node_feature_dim": 5,
            "total_input_dim": f"{5 + self.node_embedding_dim} (node) + {self.question_embedding_dim} (question) = {5 + self.node_embedding_dim + self.question_embedding_dim}",
            "hidden_channels": 256,
            "dropout": "[0.3, 0.3, 0.2]",
            "attention_heads": 4,
            "gat_layers": 3,
            "status": "loaded" if hasattr(self, 'model') else "not_loaded"
        }
