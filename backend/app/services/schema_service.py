"""
Schema extraction and management service
Migrated and enhanced from SchemaVisualizer in nl_to_sql_llm.py
"""
import hashlib
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy import create_engine, inspect, text
import redis
import logging

logger = logging.getLogger(__name__)


class SchemaService:
    """Enhanced schema extraction with MySQL support and change detection"""
    
    def __init__(self, mysql_uri: str, redis_client: redis.Redis):
        self.mysql_uri = mysql_uri
        self.redis = redis_client
        self.engine = None
        self.inspector = None
        
        # Try to create engine and inspector, but don't fail if unavailable
        try:
            self.engine = create_engine(mysql_uri)
            self.inspector = inspect(self.engine)
            logger.info(f"✅ MySQL connection established: {mysql_uri.split('@')[-1]}")
        except Exception as e:
            logger.warning(f"⚠️  MySQL connection failed: {e}")
            logger.warning("Schema extraction will not be available until database is configured")
            logger.info("The API will start but /schema endpoints will return errors")
    
    def extract_schema(self, database: str) -> Dict[str, Any]:
        """Extract complete schema from MySQL INFORMATION_SCHEMA"""
        if not self.inspector:
            raise RuntimeError(
                "MySQL connection not available. Please configure MYSQL_URI in .env "
                "with a valid database connection string."
            )
        
        schema = {
            'database': database,
            'tables': {},
            'relationships': [],
            'version': None,
            'extracted_at': datetime.utcnow().isoformat()
        }
        
        try:
            # Get all tables
            tables = self.inspector.get_table_names(schema=database)
            
            for table in tables:
                # Get columns with full metadata
                columns = self.inspector.get_columns(table, schema=database)
                
                # Get primary keys
                pk_constraint = self.inspector.get_pk_constraint(table, schema=database)
                
                # Get foreign keys
                foreign_keys = self.inspector.get_foreign_keys(table, schema=database)
                
                # Get indexes
                indexes = self.inspector.get_indexes(table, schema=database)
                
                schema['tables'][table] = {
                    'columns': [
                        {
                            'name': col['name'],
                            'type': str(col['type']),
                            'nullable': col['nullable'],
                            'default': col.get('default'),
                            'autoincrement': col.get('autoincrement', False),
                            'primary_key': col['name'] in pk_constraint.get('constrained_columns', [])
                        }
                        for col in columns
                    ],
                    'primary_keys': pk_constraint.get('constrained_columns', []),
                    'foreign_keys': [
                        {
                            'constrained_columns': fk['constrained_columns'],
                            'referred_table': fk['referred_table'],
                            'referred_columns': fk['referred_columns'],
                            'name': fk.get('name')
                        }
                        for fk in foreign_keys
                    ],
                    'indexes': [
                        {
                            'name': idx['name'],
                            'columns': idx['column_names'],
                            'unique': idx['unique']
                        }
                        for idx in indexes
                    ]
                }
                
                # Build relationships
                for fk in foreign_keys:
                    schema['relationships'].append({
                        'from_table': table,
                        'from_columns': fk['constrained_columns'],
                        'to_table': fk['referred_table'],
                        'to_columns': fk['referred_columns'],
                        'type': 'foreign_key'
                    })
            
            # Compute schema fingerprint
            schema['version'] = self._compute_fingerprint(schema)
            
            logger.info(f"Extracted schema for {database}: {len(tables)} tables, fingerprint={schema['version']}")
            
        except Exception as e:
            logger.error(f"Schema extraction failed: {e}")
            raise
        
        return schema
    
    def _compute_fingerprint(self, schema: Dict) -> str:
        """Compute SHA256 hash of schema structure"""
        # Exclude timestamp and version from hash
        schema_copy = {
            'tables': schema['tables'],
            'relationships': schema['relationships']
        }
        schema_str = json.dumps(schema_copy, sort_keys=True)
        return hashlib.sha256(schema_str.encode()).hexdigest()[:16]
    
    def get_cached_schema(self, database: str) -> Optional[Dict]:
        """Retrieve cached schema from Redis"""
        cache_key = f"schema:{database}"
        try:
            cached = self.redis.get(cache_key)
            if cached:
                logger.info(f"✅ Cache hit for '{cache_key}'")
                return json.loads(cached)
            else:
                logger.info(f"⚠️  Cache miss for '{cache_key}'")
        except Exception as e:
            logger.warning(f"❌ Cache retrieval failed for '{cache_key}': {e}")
        return None
    
    def cache_schema(self, schema: Dict, ttl: int = 3600, database_id: Optional[str] = None):
        """Cache schema in Redis with TTL"""
        # Use provided database_id or fall back to schema['database']
        db_key = database_id if database_id else schema['database']
        cache_key = f"schema:{db_key}"
        try:
            schema_json = json.dumps(schema)
            self.redis.setex(cache_key, ttl, schema_json)
            logger.info(f"✅ Cached schema for '{db_key}' with key '{cache_key}' (TTL={ttl}s, size={len(schema_json)} bytes)")
            
            # Verify it was cached
            cached = self.redis.get(cache_key)
            if cached:
                logger.info(f"✅ Verified cache write for '{cache_key}'")
            else:
                logger.error(f"❌ Cache verification failed for '{cache_key}'")
        except Exception as e:
            logger.warning(f"⚠️  Cache storage failed for '{cache_key}': {e}")
    
    def detect_schema_changes(self, old_schema: Dict, new_schema: Dict) -> Dict:
        """Compute diff between two schema versions"""
        changes = {
            'added_tables': [],
            'removed_tables': [],
            'modified_tables': {},
            'added_relationships': [],
            'removed_relationships': []
        }
        
        old_tables = set(old_schema['tables'].keys())
        new_tables = set(new_schema['tables'].keys())
        
        changes['added_tables'] = list(new_tables - old_tables)
        changes['removed_tables'] = list(old_tables - new_tables)
        
        # Check modified tables
        for table in old_tables & new_tables:
            table_changes = self._diff_table(
                old_schema['tables'][table],
                new_schema['tables'][table]
            )
            if table_changes:
                changes['modified_tables'][table] = table_changes
        
        # Relationship changes
        old_rels = {self._rel_key(r) for r in old_schema['relationships']}
        new_rels = {self._rel_key(r) for r in new_schema['relationships']}
        
        changes['added_relationships'] = [
            r for r in new_schema['relationships'] 
            if self._rel_key(r) in (new_rels - old_rels)
        ]
        changes['removed_relationships'] = [
            r for r in old_schema['relationships'] 
            if self._rel_key(r) in (old_rels - new_rels)
        ]
        
        return changes
    
    def _diff_table(self, old_table: Dict, new_table: Dict) -> Optional[Dict]:
        """Diff two table definitions"""
        changes = {
            'added_columns': [],
            'removed_columns': [],
            'modified_columns': []
        }
        
        old_cols = {c['name']: c for c in old_table['columns']}
        new_cols = {c['name']: c for c in new_table['columns']}
        
        changes['added_columns'] = list(set(new_cols.keys()) - set(old_cols.keys()))
        changes['removed_columns'] = list(set(old_cols.keys()) - set(new_cols.keys()))
        
        for col_name in set(old_cols.keys()) & set(new_cols.keys()):
            if old_cols[col_name] != new_cols[col_name]:
                changes['modified_columns'].append({
                    'name': col_name,
                    'old': old_cols[col_name],
                    'new': new_cols[col_name]
                })
        
        return changes if any(changes.values()) else None
    
    def _rel_key(self, rel: Dict) -> str:
        """Generate unique key for relationship"""
        return f"{rel['from_table']}.{','.join(rel['from_columns'])}->{rel['to_table']}.{','.join(rel['to_columns'])}"
    
    def invalidate_dependent_caches(self, changes: Dict):
        """Invalidate caches affected by schema changes"""
        # Invalidate GNN embeddings for affected tables
        affected_tables = (
            changes['added_tables'] + 
            changes['removed_tables'] + 
            list(changes['modified_tables'].keys())
        )
        
        for table in affected_tables:
            try:
                self.redis.delete(f"gnn_embedding:{table}")
            except Exception as e:
                logger.warning(f"Cache invalidation failed for {table}: {e}")
        
        # Invalidate full schema embedding
        try:
            self.redis.delete("gnn_embedding:full_schema")
        except Exception as e:
            logger.warning(f"Full schema cache invalidation failed: {e}")
    
    def get_schema_text(self, schema: Dict) -> str:
        """Get schema as formatted text for LLM prompts"""
        text = f"DATABASE SCHEMA: {schema['database']}\n\n"
        
        for table_name, table_info in schema['tables'].items():
            text += f"Table: {table_name}\n"
            text += "Columns:\n"
            for col in table_info['columns']:
                pk = " (PRIMARY KEY)" if col['primary_key'] else ""
                nn = " NOT NULL" if not col['nullable'] else ""
                text += f"  - {col['name']}: {col['type']}{pk}{nn}\n"
            
            if table_info['foreign_keys']:
                text += "Foreign Keys:\n"
                for fk in table_info['foreign_keys']:
                    text += f"  - {','.join(fk['constrained_columns'])} → {fk['referred_table']}.{','.join(fk['referred_columns'])}\n"
            text += "\n"
        
        return text
