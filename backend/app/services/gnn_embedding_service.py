"""
GNN Embedding Ingestion Service
- Pull embeddings from URL (e.g., Kaggle file links)
- Upload embeddings via JSON payload
- Cache per schema_fingerprint in Redis
"""
from typing import Dict, Any, List
import redis
import requests
import json
import base64
import logging

logger = logging.getLogger(__name__)


class GNNEmbeddingService:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def _key(self, fingerprint: str, node_id: str) -> str:
        return f"gnn:{fingerprint}:node:{node_id}"

    def _meta_key(self, fingerprint: str) -> str:
        return f"gnn:{fingerprint}:meta"

    def upload_embeddings(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Upload embeddings via JSON payload.
        Expected format:
        {
            "schema_fingerprint": "<hash>",
            "dim": 512,
            "nodes": [ {"id": "table:orders", "vec": [..]}, ... ]
        }
        """
        fingerprint = payload.get("schema_fingerprint")
        dim = payload.get("dim")
        nodes: List[Dict[str, Any]] = payload.get("nodes", [])
        if not fingerprint or not dim or not nodes:
            raise ValueError("Invalid payload: require schema_fingerprint, dim, nodes")

        count = 0
        for node in nodes:
            nid = node.get("id")
            vec = node.get("vec")
            if nid is None or vec is None:
                continue
            # Store as JSON array; for large scale, consider binary packing
            self.redis.set(self._key(fingerprint, nid), json.dumps(vec))
            count += 1
        # Store meta
        meta = {"schema_fingerprint": fingerprint, "dim": dim, "count": count}
        self.redis.set(self._meta_key(fingerprint), json.dumps(meta))
        logger.info(f"Uploaded {count} embeddings for fingerprint={fingerprint}")
        return meta

    def pull_from_url(self, fingerprint: str, url: str) -> Dict[str, Any]:
        """Download JSON from URL and upload it using upload_embeddings.
        Supports direct HTTP(S) links from Kaggle files if accessible.
        """
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        # Validate fingerprint match
        if data.get("schema_fingerprint") != fingerprint:
            raise ValueError("schema_fingerprint mismatch between request and artifact")
        return self.upload_embeddings(data)

    def get_node_vector(self, fingerprint: str, node_id: str) -> List[float] | None:
        raw = self.redis.get(self._key(fingerprint, node_id))
        if not raw:
            return None
        return json.loads(raw)

    def get_meta(self, fingerprint: str) -> Dict[str, Any] | None:
        raw = self.redis.get(self._meta_key(fingerprint))
        return json.loads(raw) if raw else None
