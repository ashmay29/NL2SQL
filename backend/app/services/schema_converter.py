"""
Schema Converter
Converts backend schema format to Spider format for GNN model
"""
from typing import Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)


class SchemaConverter:
    """
    Converts NL2SQL backend schema format to Spider dataset format
    required by the GNN Ranker model.
    
    Backend Format:
    {
        "database": "ecommerce",
        "tables": {
            "Customers": {
                "columns": [
                    {"name": "customer_id", "type": "int", "primary_key": True},
                    {"name": "first_name", "type": "varchar"}
                ],
                "foreign_keys": [...]
            }
        }
    }
    
    Spider Format:
    {
        "db_id": "ecommerce",
        "table_names_original": ["Customers", "Products"],
        "column_names_original": [[0, "customer_id"], [0, "first_name"], ...],
        "column_types": ["number", "text", ...],
        "primary_keys": [0, 5],
        "foreign_keys": [[9, 0]]
    }
    """
    
    # SQL type to Spider type mapping
    TYPE_MAPPING = {
        # Numeric types
        'int': 'number',
        'integer': 'number',
        'bigint': 'number',
        'smallint': 'number',
        'tinyint': 'number',
        'mediumint': 'number',
        'decimal': 'number',
        'numeric': 'number',
        'float': 'number',
        'double': 'number',
        'real': 'number',
        
        # Text types
        'char': 'text',
        'varchar': 'text',
        'text': 'text',
        'tinytext': 'text',
        'mediumtext': 'text',
        'longtext': 'text',
        'string': 'text',
        
        # Date/Time types
        'date': 'time',
        'datetime': 'time',
        'timestamp': 'time',
        'time': 'time',
        'year': 'time',
        
        # Boolean
        'boolean': 'boolean',
        'bool': 'boolean',
        
        # Binary
        'blob': 'others',
        'binary': 'others',
        'varbinary': 'others',
    }
    
    @classmethod
    def convert_to_spider_format(cls, backend_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert backend schema to Spider format for GNN model
        
        Spider format structure:
        - column_names_original: [[table_idx, col_name], ...] 
          where table_idx is the index in table_names_original
        - column indices start from 0
        - primary_keys: list of column indices
        - foreign_keys: [[source_col_idx, target_col_idx], ...]
        
        Args:
            backend_schema: Schema in backend format
            
        Returns:
            Schema in Spider format compatible with GNN model
        """
        try:
            db_id = backend_schema.get('database', 'unknown')
            tables = backend_schema.get('tables', {})
            
            # Initialize Spider format components
            table_names_original = []
            column_names_original = []
            column_types = []
            primary_keys = []
            foreign_keys = []
            
            # Map (table_name, column_name) to global column index
            column_position_map = {}
            global_column_idx = 0
            
            # Sort tables by name for consistent ordering
            sorted_tables = sorted(tables.items())
            
            # First pass: Build tables and columns
            for table_idx, (table_name, table_info) in enumerate(sorted_tables):
                table_names_original.append(table_name)
                
                columns = table_info.get('columns', [])
                
                for col in columns:
                    col_name = col['name']
                    col_type = col.get('type', 'text').lower()
                    
                    # Store mapping: (table_name, col_name) -> global column index
                    column_position_map[(table_name, col_name)] = global_column_idx
                    
                    # Add column in Spider format: [table_idx, column_name]
                    # table_idx refers to the position in table_names_original
                    column_names_original.append([table_idx, col_name])
                    
                    # Map SQL type to Spider type
                    spider_type = cls._map_type(col_type)
                    column_types.append(spider_type)
                    
                    # Check if primary key
                    if col.get('primary_key', False):
                        primary_keys.append(global_column_idx)
                    
                    global_column_idx += 1
            
            # Second pass: Build foreign keys
            for table_name, table_info in sorted_tables:
                fks = table_info.get('foreign_keys', [])
                
                for fk in fks:
                    constrained_cols = fk.get('constrained_columns', [])
                    referred_table = fk.get('referred_table', '')
                    referred_cols = fk.get('referred_columns', [])
                    
                    # Map each foreign key relationship
                    for const_col, ref_col in zip(constrained_cols, referred_cols):
                        # Get global column indices
                        source_idx = column_position_map.get((table_name, const_col))
                        target_idx = column_position_map.get((referred_table, ref_col))
                        
                        if source_idx is not None and target_idx is not None:
                            # Spider format: [source_column_idx, target_column_idx]
                            foreign_keys.append([source_idx, target_idx])
                        else:
                            logger.warning(
                                f"Could not map foreign key: {table_name}.{const_col} -> "
                                f"{referred_table}.{ref_col}"
                            )
            
            spider_schema = {
                "db_id": db_id,
                "table_names_original": table_names_original,
                "column_names_original": column_names_original,
                "column_types": column_types,
                "primary_keys": primary_keys,
                "foreign_keys": foreign_keys
            }
            
            logger.debug(
                f"Converted schema: {len(table_names_original)} tables, "
                f"{len(column_names_original)} columns, "
                f"{len(primary_keys)} PKs, {len(foreign_keys)} FKs"
            )
            
            return spider_schema
            
        except Exception as e:
            logger.error(f"Failed to convert schema to Spider format: {e}")
            raise
    
    @classmethod
    def _map_type(cls, sql_type: str) -> str:
        """
        Map SQL data type to Spider type category
        
        Args:
            sql_type: SQL type name (e.g., 'varchar', 'int')
            
        Returns:
            Spider type ('number', 'text', 'time', 'boolean', 'others')
        """
        # Extract base type (remove size specifications like varchar(255))
        base_type = sql_type.split('(')[0].strip().lower()
        
        # Look up in mapping
        spider_type = cls.TYPE_MAPPING.get(base_type, 'text')
        
        return spider_type
    
    @classmethod
    def validate_spider_schema(cls, spider_schema: Dict[str, Any]) -> bool:
        """
        Validate that the converted schema has the correct Spider format
        
        Args:
            spider_schema: Schema in Spider format
            
        Returns:
            True if valid, raises ValueError otherwise
        """
        required_keys = [
            'db_id',
            'table_names_original',
            'column_names_original',
            'column_types',
            'primary_keys',
            'foreign_keys'
        ]
        
        for key in required_keys:
            if key not in spider_schema:
                raise ValueError(f"Missing required key in Spider schema: {key}")
        
        # Validate column_names_original format
        for col in spider_schema['column_names_original']:
            if not isinstance(col, list) or len(col) != 2:
                raise ValueError(
                    f"Invalid column format: {col}. Expected [table_idx, column_name]"
                )
            if not isinstance(col[0], int) or not isinstance(col[1], str):
                raise ValueError(
                    f"Invalid column format: {col}. Expected [int, str]"
                )
        
        # Validate foreign keys format
        for fk in spider_schema['foreign_keys']:
            if not isinstance(fk, list) or len(fk) != 2:
                raise ValueError(
                    f"Invalid foreign key format: {fk}. Expected [source_idx, target_idx]"
                )
        
        logger.debug("Spider schema validation passed")
        return True
