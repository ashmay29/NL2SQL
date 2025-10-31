"""
Data Ingestion Service
Handles multiple data formats: CSV, Excel, Database Tables
Extracts schema and prepares data for GNN embedding generation
"""
from typing import Dict, Any, List, Optional, BinaryIO
from enum import Enum
import pandas as pd
import hashlib
import json
import logging
from datetime import datetime
from sqlalchemy import create_engine, inspect, MetaData, Table
from io import BytesIO

logger = logging.getLogger(__name__)


class DataSourceType(str, Enum):
    """Supported data source types"""
    CSV = "csv"
    EXCEL = "excel"
    DATABASE_TABLE = "database_table"
    PARQUET = "parquet"
    JSON = "json"


class DataIngestionService:
    """
    Service for ingesting data from multiple formats and extracting schema.
    Prepares data for GNN embedding generation.
    """
    
    def __init__(self, mysql_uri: Optional[str] = None):
        self.mysql_uri = mysql_uri
        self.engine = create_engine(mysql_uri) if mysql_uri else None
        logger.info("DataIngestionService initialized")
    
    def ingest_csv(
        self,
        file: BinaryIO,
        table_name: str,
        delimiter: str = ",",
        encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """
        Ingest CSV file and extract schema
        
        Args:
            file: File-like object containing CSV data
            table_name: Name to assign to this table
            delimiter: CSV delimiter
            encoding: File encoding
            
        Returns:
            Schema dictionary with metadata
        """
        try:
            # Read CSV into DataFrame
            df = pd.read_csv(file, delimiter=delimiter, encoding=encoding)
            
            # Extract schema from DataFrame
            schema = self._extract_schema_from_dataframe(df, table_name, DataSourceType.CSV)
            
            # Add sample data for context
            schema['sample_rows'] = df.head(5).to_dict('records')
            schema['row_count'] = len(df)
            
            logger.info(f"Ingested CSV: {table_name}, {len(df)} rows, {len(df.columns)} columns")
            return schema
            
        except Exception as e:
            logger.error(f"Failed to ingest CSV: {e}")
            raise
    
    def ingest_excel(
        self,
        file: BinaryIO,
        sheet_name: Optional[str] = None,
        table_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest Excel file and extract schema
        
        Args:
            file: File-like object containing Excel data
            sheet_name: Specific sheet to read (None = first sheet)
            table_name: Name to assign (defaults to sheet name)
            
        Returns:
            Schema dictionary with metadata
        """
        try:
            # Read Excel into DataFrame
            df = pd.read_excel(file, sheet_name=sheet_name or 0)
            
            # Determine table name
            if not table_name:
                if isinstance(sheet_name, str):
                    table_name = sheet_name
                else:
                    table_name = "sheet_0"
            
            # Extract schema
            schema = self._extract_schema_from_dataframe(df, table_name, DataSourceType.EXCEL)
            
            # Add sample data
            schema['sample_rows'] = df.head(5).to_dict('records')
            schema['row_count'] = len(df)
            
            logger.info(f"Ingested Excel: {table_name}, {len(df)} rows, {len(df.columns)} columns")
            return schema
            
        except Exception as e:
            logger.error(f"Failed to ingest Excel: {e}")
            raise
    
    def ingest_database_table(
        self,
        database: str,
        table_name: str,
        sample_size: int = 1000
    ) -> Dict[str, Any]:
        """
        Ingest database table and extract schema
        
        Args:
            database: Database name
            table_name: Table name
            sample_size: Number of rows to sample for statistics
            
        Returns:
            Schema dictionary with metadata
        """
        if not self.engine:
            raise ValueError("MySQL URI not configured for database ingestion")
        
        try:
            # Get table metadata using SQLAlchemy inspector
            inspector = inspect(self.engine)
            
            # Get columns
            columns = inspector.get_columns(table_name, schema=database)
            
            # Get primary keys
            pk_constraint = inspector.get_pk_constraint(table_name, schema=database)
            
            # Get foreign keys
            foreign_keys = inspector.get_foreign_keys(table_name, schema=database)
            
            # Get indexes
            indexes = inspector.get_indexes(table_name, schema=database)
            
            # Sample data for statistics
            query = f"SELECT * FROM {database}.{table_name} LIMIT {sample_size}"
            df = pd.read_sql(query, self.engine)
            
            # Build schema
            schema = {
                'table_name': table_name,
                'database': database,
                'source_type': DataSourceType.DATABASE_TABLE.value,
                'columns': [
                    {
                        'name': col['name'],
                        'type': str(col['type']),
                        'nullable': col['nullable'],
                        'default': col.get('default'),
                        'autoincrement': col.get('autoincrement', False),
                        'primary_key': col['name'] in pk_constraint.get('constrained_columns', []),
                        # Add statistics from sample
                        'statistics': self._compute_column_statistics(df[col['name']])
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
                ],
                'sample_rows': df.head(5).to_dict('records'),
                'row_count': len(df),
                'extracted_at': datetime.utcnow().isoformat()
            }
            
            # Compute fingerprint
            schema['fingerprint'] = self._compute_fingerprint(schema)
            
            logger.info(f"Ingested database table: {database}.{table_name}")
            return schema
            
        except Exception as e:
            logger.error(f"Failed to ingest database table: {e}")
            raise
    
    def ingest_parquet(
        self,
        file: BinaryIO,
        table_name: str
    ) -> Dict[str, Any]:
        """Ingest Parquet file and extract schema"""
        try:
            df = pd.read_parquet(file)
            schema = self._extract_schema_from_dataframe(df, table_name, DataSourceType.PARQUET)
            schema['sample_rows'] = df.head(5).to_dict('records')
            schema['row_count'] = len(df)
            
            logger.info(f"Ingested Parquet: {table_name}, {len(df)} rows")
            return schema
            
        except Exception as e:
            logger.error(f"Failed to ingest Parquet: {e}")
            raise
    
    def ingest_json(
        self,
        file: BinaryIO,
        table_name: str,
        orient: str = "records"
    ) -> Dict[str, Any]:
        """Ingest JSON file and extract schema"""
        try:
            df = pd.read_json(file, orient=orient)
            schema = self._extract_schema_from_dataframe(df, table_name, DataSourceType.JSON)
            schema['sample_rows'] = df.head(5).to_dict('records')
            schema['row_count'] = len(df)
            
            logger.info(f"Ingested JSON: {table_name}, {len(df)} rows")
            return schema
            
        except Exception as e:
            logger.error(f"Failed to ingest JSON: {e}")
            raise
    
    def _extract_schema_from_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        source_type: DataSourceType
    ) -> Dict[str, Any]:
        """
        Extract schema from pandas DataFrame
        
        Args:
            df: DataFrame to analyze
            table_name: Name for the table
            source_type: Type of data source
            
        Returns:
            Schema dictionary
        """
        columns = []
        
        for col_name in df.columns:
            col_data = df[col_name]
            
            # Infer SQL type from pandas dtype
            sql_type = self._pandas_to_sql_type(col_data.dtype)
            
            # Check nullability
            nullable = col_data.isna().any()
            
            # Compute statistics
            statistics = self._compute_column_statistics(col_data)
            
            columns.append({
                'name': col_name,
                'type': sql_type,
                'nullable': bool(nullable),
                'primary_key': False,  # Cannot infer from flat file
                'statistics': statistics
            })
        
        schema = {
            'table_name': table_name,
            'source_type': source_type.value,
            'columns': columns,
            'primary_keys': [],
            'foreign_keys': [],
            'indexes': [],
            'extracted_at': datetime.utcnow().isoformat()
        }
        
        # Compute fingerprint
        schema['fingerprint'] = self._compute_fingerprint(schema)
        
        return schema
    
    def _pandas_to_sql_type(self, dtype) -> str:
        """Map pandas dtype to SQL type"""
        dtype_str = str(dtype)
        
        if 'int' in dtype_str:
            return 'INTEGER'
        elif 'float' in dtype_str:
            return 'FLOAT'
        elif 'bool' in dtype_str:
            return 'BOOLEAN'
        elif 'datetime' in dtype_str:
            return 'DATETIME'
        elif 'date' in dtype_str:
            return 'DATE'
        else:
            return 'VARCHAR(255)'
    
    def _compute_column_statistics(self, series: pd.Series) -> Dict[str, Any]:
        """Compute statistics for a column"""
        stats = {
            'null_count': int(series.isna().sum()),
            'null_percentage': float(series.isna().sum() / len(series) * 100) if len(series) > 0 else 0,
            'unique_count': int(series.nunique()),
            'cardinality': 'high' if series.nunique() > len(series) * 0.9 else 'low'
        }
        
        # Numeric statistics
        if pd.api.types.is_numeric_dtype(series):
            stats.update({
                'min': float(series.min()) if not series.isna().all() else None,
                'max': float(series.max()) if not series.isna().all() else None,
                'mean': float(series.mean()) if not series.isna().all() else None,
                'median': float(series.median()) if not series.isna().all() else None
            })
        
        # String statistics
        elif pd.api.types.is_string_dtype(series):
            non_null = series.dropna()
            if len(non_null) > 0:
                stats.update({
                    'avg_length': float(non_null.str.len().mean()),
                    'max_length': int(non_null.str.len().max())
                })
        
        return stats
    
    def _compute_fingerprint(self, schema: Dict) -> str:
        """Compute SHA256 hash of schema structure"""
        # Create stable representation
        schema_copy = {
            'table_name': schema.get('table_name'),
            'columns': [
                {
                    'name': col['name'],
                    'type': col['type'],
                    'nullable': col['nullable']
                }
                for col in schema.get('columns', [])
            ]
        }
        
        schema_str = json.dumps(schema_copy, sort_keys=True)
        return hashlib.sha256(schema_str.encode()).hexdigest()[:16]
    
    def merge_schemas(self, schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple schemas into a unified database schema
        Useful when ingesting multiple CSV/Excel files as tables
        
        Args:
            schemas: List of individual table schemas
            
        Returns:
            Unified database schema
        """
        merged = {
            'database': 'ingested_data',
            'tables': {},
            'relationships': [],
            'extracted_at': datetime.utcnow().isoformat()
        }
        
        for schema in schemas:
            table_name = schema['table_name']
            merged['tables'][table_name] = schema
        
        # Compute overall fingerprint
        merged['fingerprint'] = self._compute_fingerprint(merged)
        
        logger.info(f"Merged {len(schemas)} schemas into unified database")
        return merged
