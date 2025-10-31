"""
GNN Inference Service
External service integration for Graph Neural Network model inference
Handles communication with external GNN model server and embedding generation
"""
from typing import Dict, Any, List, Optional
import logging
import httpx
import json
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class GNNInferenceService:
    """
    Service for communicating with external GNN model server.
    The GNN model processes schema graphs and generates embeddings.
    
    Architecture:
    1. Schema → Graph representation (nodes: tables/columns, edges: relationships)
    2. Graph + Query → GNN model inference
    3. GNN outputs → Node embeddings (512-dim vectors)
    4. Embeddings cached in Redis for fast retrieval
    """
    
    def __init__(
        self,
        gnn_endpoint: Optional[str] = None,
        timeout: int = 30,
        use_mock: bool = True
    ):
        """
        Initialize GNN inference service
        
        Args:
            gnn_endpoint: URL of external GNN model server (e.g., http://gnn-server:8080)
            timeout: Request timeout in seconds
            use_mock: If True, use mock embeddings as fallback
        """
        self.gnn_endpoint = gnn_endpoint
        self.timeout = timeout
        self.use_mock = use_mock
        self.client = httpx.AsyncClient(timeout=timeout) if gnn_endpoint else None
        
        if gnn_endpoint:
            logger.info(f"GNNInferenceService initialized with endpoint: {gnn_endpoint}")
        else:
            logger.info("GNNInferenceService initialized in mock mode (no endpoint configured)")
    
    async def generate_schema_embeddings(
        self,
        schema: Dict[str, Any],
        force_regenerate: bool = False
    ) -> Dict[str, List[float]]:
        """
        Generate embeddings for all nodes in a schema using GNN model
        
        Args:
            schema: Schema dictionary with tables, columns, relationships
            force_regenerate: If True, bypass cache and regenerate
            
        Returns:
            Dictionary mapping node_id → embedding vector
            Example: {
                "table:customers": [0.1, 0.2, ...],
                "column:customers.id": [0.3, 0.4, ...],
                ...
            }
        """
        try:
            if not self.client or self.use_mock:
                logger.debug("Using mock GNN embeddings")
                return await self._generate_mock_embeddings(schema)
            
            # Build graph representation from schema
            graph = self._schema_to_graph(schema)
            
            # Call external GNN service
            payload = {
                "graph": graph,
                "schema_fingerprint": schema.get('fingerprint', schema.get('version')),
                "force_regenerate": force_regenerate
            }
            
            response = await self.client.post(
                f"{self.gnn_endpoint}/infer/schema",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            embeddings = result.get('embeddings', {})
            
            logger.info(f"Generated {len(embeddings)} GNN embeddings for schema")
            return embeddings
            
        except httpx.HTTPError as e:
            logger.error(f"GNN service HTTP error: {e}")
            if self.use_mock:
                logger.warning("Falling back to mock embeddings")
                return await self._generate_mock_embeddings(schema)
            raise
        
        except Exception as e:
            logger.error(f"Failed to generate GNN embeddings: {e}")
            if self.use_mock:
                logger.warning("Falling back to mock embeddings")
                return await self._generate_mock_embeddings(schema)
            raise
    
    async def generate_query_embedding(
        self,
        query_text: str,
        schema: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[float]:
        """
        Generate embedding for a natural language query using GNN
        
        Args:
            query_text: Natural language query
            schema: Schema context for the query
            context: Optional conversation context
            
        Returns:
            Query embedding vector (512-dim)
        """
        try:
            if not self.client or self.use_mock:
                logger.debug("Using mock query embedding")
                return await self._generate_mock_query_embedding(query_text)
            
            # Build graph with query context
            graph = self._schema_to_graph(schema)
            
            payload = {
                "query": query_text,
                "graph": graph,
                "context": context or {}
            }
            
            response = await self.client.post(
                f"{self.gnn_endpoint}/infer/query",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            embedding = result.get('embedding', [])
            
            logger.debug(f"Generated GNN query embedding (dim={len(embedding)})")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            if self.use_mock:
                logger.warning("Falling back to mock query embedding")
                return await self._generate_mock_query_embedding(query_text)
            raise
    
    async def get_relevant_schema_nodes(
        self,
        query_embedding: List[float],
        schema_embeddings: Dict[str, List[float]],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find most relevant schema nodes for a query using cosine similarity
        
        Args:
            query_embedding: Query embedding vector
            schema_embeddings: All schema node embeddings
            top_k: Number of top nodes to return
            
        Returns:
            List of relevant nodes with similarity scores
        """
        try:
            if not self.client or self.use_mock:
                return self._mock_relevant_nodes(schema_embeddings, top_k)
            
            payload = {
                "query_embedding": query_embedding,
                "schema_embeddings": schema_embeddings,
                "top_k": top_k
            }
            
            response = await self.client.post(
                f"{self.gnn_endpoint}/similarity/top_k",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get('nodes', [])
            
        except Exception as e:
            logger.error(f"Failed to get relevant nodes: {e}")
            if self.use_mock:
                return self._mock_relevant_nodes(schema_embeddings, top_k)
            raise
    
    def _schema_to_graph(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert schema dictionary to graph representation for GNN
        
        Graph structure:
        {
            "nodes": [
                {"id": "table:customers", "type": "table", "properties": {...}},
                {"id": "column:customers.id", "type": "column", "properties": {...}},
                ...
            ],
            "edges": [
                {"source": "table:customers", "target": "column:customers.id", "type": "has_column"},
                {"source": "column:orders.customer_id", "target": "column:customers.id", "type": "foreign_key"},
                ...
            ]
        }
        """
        nodes = []
        edges = []
        
        tables = schema.get('tables', {})
        
        for table_name, table_info in tables.items():
            # Add table node
            table_node_id = f"table:{table_name}"
            nodes.append({
                "id": table_node_id,
                "type": "table",
                "properties": {
                    "name": table_name,
                    "row_count": table_info.get('row_count', 0)
                }
            })
            
            # Add column nodes
            for col in table_info.get('columns', []):
                col_node_id = f"column:{table_name}.{col['name']}"
                nodes.append({
                    "id": col_node_id,
                    "type": "column",
                    "properties": {
                        "name": col['name'],
                        "data_type": col['type'],
                        "nullable": col.get('nullable', True),
                        "primary_key": col.get('primary_key', False),
                        "statistics": col.get('statistics', {})
                    }
                })
                
                # Add edge: table → column
                edges.append({
                    "source": table_node_id,
                    "target": col_node_id,
                    "type": "has_column"
                })
            
            # Add foreign key edges
            for fk in table_info.get('foreign_keys', []):
                for src_col, tgt_col in zip(fk['constrained_columns'], fk['referred_columns']):
                    src_node = f"column:{table_name}.{src_col}"
                    tgt_node = f"column:{fk['referred_table']}.{tgt_col}"
                    edges.append({
                        "source": src_node,
                        "target": tgt_node,
                        "type": "foreign_key"
                    })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "fingerprint": schema.get('fingerprint', schema.get('version')),
                "database": schema.get('database', 'unknown')
            }
        }
    
    async def _generate_mock_embeddings(self, schema: Dict[str, Any]) -> Dict[str, List[float]]:
        """Generate mock embeddings using simple hashing (fallback)"""
        import hashlib
        import numpy as np
        
        embeddings = {}
        tables = schema.get('tables', {})
        
        for table_name, table_info in tables.items():
            # Table embedding
            table_id = f"table:{table_name}"
            embeddings[table_id] = self._hash_to_vector(table_id, 512)
            
            # Column embeddings
            for col in table_info.get('columns', []):
                col_id = f"column:{table_name}.{col['name']}"
                embeddings[col_id] = self._hash_to_vector(col_id, 512)
        
        logger.debug(f"Generated {len(embeddings)} mock embeddings")
        return embeddings
    
    async def _generate_mock_query_embedding(self, query_text: str) -> List[float]:
        """Generate mock query embedding"""
        return self._hash_to_vector(query_text, 512)
    
    def _hash_to_vector(self, text: str, dim: int) -> List[float]:
        """Convert text to deterministic vector using hash"""
        import hashlib
        import numpy as np
        
        # Use hash as seed for reproducibility
        hash_val = int(hashlib.sha256(text.encode()).hexdigest(), 16)
        np.random.seed(hash_val % (2**32))
        
        # Generate normalized random vector
        vec = np.random.randn(dim)
        vec = vec / np.linalg.norm(vec)
        
        return vec.tolist()
    
    def _mock_relevant_nodes(
        self,
        schema_embeddings: Dict[str, List[float]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Return mock relevant nodes (simple random selection)"""
        import random
        
        node_ids = list(schema_embeddings.keys())
        selected = random.sample(node_ids, min(top_k, len(node_ids)))
        
        return [
            {
                "node_id": node_id,
                "similarity": random.uniform(0.6, 0.95),
                "embedding": schema_embeddings[node_id]
            }
            for node_id in selected
        ]
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if GNN service is available"""
        if not self.client:
            return {
                "status": "mock",
                "message": "GNN endpoint not configured, using mock mode"
            }
        
        try:
            response = await self.client.get(f"{self.gnn_endpoint}/health")
            response.raise_for_status()
            
            return {
                "status": "healthy",
                "endpoint": self.gnn_endpoint,
                "details": response.json()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "endpoint": self.gnn_endpoint,
                "error": str(e)
            }
    
    async def close(self):
        """Close HTTP client"""
        if self.client:
            await self.client.aclose()
