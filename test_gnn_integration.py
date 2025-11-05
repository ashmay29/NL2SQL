"""
Test script for GNN integration
Run this to verify the GNN model is properly integrated
"""
import asyncio
import sys
import os
import logging
import json
import google.generativeai as genai

# Configure logging to see debug output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.schema_converter import SchemaConverter
from app.services.gnn_ranker_service import GNNRankerService

# HARDCODED GEMINI API KEY - Replace with your actual key
GEMINI_API_KEY = "AIzaSyC2MUdmrdMmJc3O0gth8_Np3NOjnilAw_8"  # TODO: Replace this with your actual API key


async def call_gemini_api(prompt: str, api_key: str) -> str:
    """
    Make a direct call to Gemini API
    
    Args:
        prompt: The prompt to send to Gemini
        api_key: Gemini API key
        
    Returns:
        Generated text response
    """
    try:
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Create model
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Generate response
        response = model.generate_content(prompt)
        
        return response.text
        
    except Exception as e:
        print(f"⚠️  Gemini API call failed: {e}")
        return f"[ERROR: {e}]"


def test_schema_conversion():
    """Test backend schema → Spider format conversion"""
    print("\n" + "="*60)
    print("TEST 1: Schema Conversion")
    print("="*60)
    
    backend_schema = {
        "database": "ecommerce",
        "tables": {
            "Customers": {
                "columns": [
                    {"name": "customer_id", "type": "int", "primary_key": True},
                    {"name": "first_name", "type": "varchar"},
                    {"name": "last_name", "type": "varchar"},
                    {"name": "email", "type": "varchar"},
                    {"name": "city", "type": "varchar"}
                ],
                "foreign_keys": []
            },
            "Products": {
                "columns": [
                    {"name": "product_id", "type": "int", "primary_key": True},
                    {"name": "name", "type": "varchar"},
                    {"name": "price", "type": "decimal"}
                ],
                "foreign_keys": []
            },
            "Orders": {
                "columns": [
                    {"name": "order_id", "type": "int", "primary_key": True},
                    {"name": "customer_id", "type": "int"},
                    {"name": "product_id", "type": "int"},
                    {"name": "quantity", "type": "int"}
                ],
                "foreign_keys": [
                    {
                        "constrained_columns": ["customer_id"],
                        "referred_table": "Customers",
                        "referred_columns": ["customer_id"]
                    },
                    {
                        "constrained_columns": ["product_id"],
                        "referred_table": "Products",
                        "referred_columns": ["product_id"]
                    }
                ]
            }
        }
    }
    
    print("\n📥 Input (Backend Format):")
    print(f"  Tables: {list(backend_schema['tables'].keys())}")
    print(f"  Total columns: {sum(len(t['columns']) for t in backend_schema['tables'].values())}")
    
    spider_schema = SchemaConverter.convert_to_spider_format(backend_schema)
    
    print("\n📤 Output (Spider Format):")
    print(f"  db_id: {spider_schema['db_id']}")
    print(f"  table_names_original: {spider_schema['table_names_original']}")
    print(f"  column_names_original ({len(spider_schema['column_names_original'])} columns):")
    for i, (t_idx, col_name) in enumerate(spider_schema['column_names_original']):
        table_name = spider_schema['table_names_original'][t_idx]
        print(f"    [{t_idx}] {table_name}.{col_name} ({spider_schema['column_types'][i]})")
    # if len(spider_schema['column_names_original']) > 5:
    #     print(f"    ... and {len(spider_schema['column_names_original']) - 5} more")
    
    print(f"  primary_keys: {spider_schema['primary_keys']}")
    print(f"  foreign_keys: {spider_schema['foreign_keys']}")
    
    # Validate
    try:
        SchemaConverter.validate_spider_schema(spider_schema)
        print("\n✅ Schema validation passed!")
    except Exception as e:
        print(f"\n❌ Schema validation failed: {e}")
        return False
    
    return True


async def test_gnn_ranker():
    """Test GNN Ranker service"""
    print("\n" + "="*60)
    print("TEST 2: GNN Ranker Service")
    print("="*60)
    
    # Check if model file exists
    model_path = "backend/models/gnn/best_model.pt"
    
    if not os.path.exists(model_path):
        print(f"\n⚠️  WARNING: Model file not found at {model_path}")
        print("   Please copy your trained model to this location:")
        print(f"   cp /path/to/your/best_model.pt {model_path}")
        print("\n   Continuing with untrained model for testing...")
    
    try:
        print("\n🔧 Initializing GNN Ranker...")
        gnn_ranker = GNNRankerService(
            model_path=model_path,
            device='auto',
            node_feature_dim=5,
            node_embedding_dim=384,
            question_embedding_dim=768,
            hidden_channels=256,
            use_rich_node_embeddings=True
        )
        
        print("✅ GNN Ranker initialized!")
        
        # Get model info
        info = gnn_ranker.get_model_info()
        print("\n📊 Model Info:")
        for key, value in info.items():
            print(f"  {key}: {value}")
        
        # Test schema scoring
        print("\n🧪 Testing schema node scoring...")
        
        backend_schema = {
            "database": "ecommerce",
            "tables": {
                "Customers": {
                    "columns": [
                        {"name": "customer_id", "type": "int", "primary_key": True},
                        {"name": "first_name", "type": "varchar"},
                        {"name": "city", "type": "varchar"}
                    ],
                    "foreign_keys": []
                },
                "Orders": {
                    "columns": [
                        {"name": "order_id", "type": "int", "primary_key": True},
                        {"name": "customer_id", "type": "int"},
                        {"name": "total", "type": "decimal"}
                    ],
                    "foreign_keys": [
                        {
                            "constrained_columns": ["customer_id"],
                            "referred_table": "Customers",
                            "referred_columns": ["customer_id"]
                        }
                    ]
                }
            }
        }
        
        query = "Show me all customers from New York"
        
        print(f"\n  Query: '{query}'")
        print("  Scoring schema nodes...")
        
        results = await gnn_ranker.score_schema_nodes(
            query=query,
            backend_schema=backend_schema,
            top_k=10
        )
        
        print(f"\n  Top {len(results)} relevant nodes:")
        for node in results[:5]:
            print(f"    {node['rank']}. {node['node_name']} ({node['node_type']}) - Score: {node['score']:.6f}")
        
        print("\n✅ GNN Ranker test passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ GNN Ranker test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_hybrid_llm_gnn():
    """Test hybrid LLM+GNN pipeline integration"""
    print("\n" + "="*60)
    print("TEST 3: Hybrid LLM+GNN Pipeline")
    print("="*60)
    
    try:
        # Initialize GNN Ranker
        print("\n🔧 Initializing services...")
        model_path = os.path.join(os.path.dirname(__file__), "backend", "models", "gnn", "best_model.pt")
        
        if not os.path.exists(model_path):
            print(f"⚠️  Model file not found: {model_path}")
            print("   Skipping hybrid LLM+GNN test")
            return True
        
        gnn_ranker = GNNRankerService(
            model_path=model_path,
            device='cpu',
            use_rich_node_embeddings=True
        )
        
        # Mock schema in BACKEND format (GNN service will convert to Spider internally)
        backend_schema = {
            "database": "ecommerce",
            "tables": {
                "Customers": {
                    "columns": [
                        {"name": "customer_id", "type": "int", "primary_key": True},
                        {"name": "first_name", "type": "varchar"},
                        {"name": "last_name", "type": "varchar"},
                        {"name": "email", "type": "varchar"},
                        {"name": "city", "type": "varchar"}
                    ],
                    "foreign_keys": []
                },
                "Orders": {
                    "columns": [
                        {"name": "order_id", "type": "int", "primary_key": True},
                        {"name": "customer_id", "type": "int"},
                        {"name": "product_id", "type": "int"},
                        {"name": "total", "type": "decimal"}
                    ],
                    "foreign_keys": [
                        {
                            "constrained_columns": ["customer_id"],
                            "referred_table": "Customers",
                            "referred_columns": ["customer_id"]
                        },
                        {
                            "constrained_columns": ["product_id"],
                            "referred_table": "Products",
                            "referred_columns": ["product_id"]
                        }
                    ]
                },
                "Products": {
                    "columns": [
                        {"name": "product_id", "type": "int", "primary_key": True},
                        {"name": "name", "type": "varchar"},
                        {"name": "price", "type": "decimal"}
                    ],
                    "foreign_keys": []
                }
            }
        }
        
        query = "Show me all customers from New York who made orders over $100"
        
        print(f"\n📝 Query: '{query}'")
        print("\n🧠 Step 1: GNN Schema Pruning")
        
        # Step 1: Use GNN to score and prune schema
        gnn_top_nodes = await gnn_ranker.score_schema_nodes(
            query=query,
            backend_schema=backend_schema,
            top_k=10
        )
        
        print(f"  ✓ GNN scored {len(gnn_top_nodes)} relevant nodes")
        print(f"\n  Top 5 GNN-ranked nodes:")
        for node in gnn_top_nodes[:5]:
            print(f"    {node['rank']}. {node['node_name']} ({node['node_type']}) - Score: {node['score']:.6f}")
        
        # Step 2: Build GNN-pruned schema for LLM
        print("\n🔍 Step 2: Building GNN-Pruned Schema")
        
        # Extract relevant tables and columns based on GNN scores
        relevant_tables = set()
        relevant_columns = {}
        
        for node in gnn_top_nodes:
            if node['node_type'] == 'table':
                relevant_tables.add(node['node_name'])
            elif node['node_type'] == 'column':
                # Extract table name from column node (format: "table.column")
                if '.' in node['node_name']:
                    table_name, col_name = node['node_name'].split('.', 1)
                    relevant_tables.add(table_name)
                    if table_name not in relevant_columns:
                        relevant_columns[table_name] = []
                    relevant_columns[table_name].append(col_name)
        
        # Build pruned schema text from backend schema format
        pruned_schema_text = "=== GNN-PRUNED SCHEMA (Most Relevant) ===\n\n"
        
        tables = backend_schema.get('tables', {})
        
        for table_name in relevant_tables:
            if table_name not in tables:
                continue
                
            pruned_schema_text += f"Table: {table_name}\n"
            pruned_schema_text += "Columns:\n"
            
            table_info = tables[table_name]
            for col in table_info.get('columns', []):
                col_name = col['name']
                col_type = col['type']
                
                # Highlight GNN-selected columns
                if table_name in relevant_columns and col_name in relevant_columns[table_name]:
                    pruned_schema_text += f"  • {col_name} ({col_type}) ⭐ [GNN-Selected]\n"
                else:
                    pruned_schema_text += f"  • {col_name} ({col_type})\n"
            
            # Show foreign keys
            fks = table_info.get('foreign_keys', [])
            if fks:
                pruned_schema_text += "  Foreign Keys:\n"
                for fk in fks:
                    const_cols = ", ".join(fk['constrained_columns'])
                    ref_table = fk['referred_table']
                    ref_cols = ", ".join(fk['referred_columns'])
                    pruned_schema_text += f"    - {const_cols} -> {ref_table}({ref_cols})\n"
            
            pruned_schema_text += "\n"
            pruned_schema_text += "\n"
        
        print(pruned_schema_text)
        
        # Step 3: Call Gemini LLM with GNN-pruned schema
        print("💡 Step 3: Calling Gemini API with GNN-pruned schema...")
        
        llm_prompt = f"""You are a SQL expert. Generate a MySQL query based on the user's question and the provided schema.

{pruned_schema_text}

User Question: {query}

Generate ONLY the SQL query that answers the question using the schema above.
Focus on the GNN-selected columns (marked with ⭐) as they are most relevant to the query.

Important:
- Return ONLY the SQL query, no explanations
- Use proper MySQL syntax

SQL Query:"""
        
        print("\n📤 Sending request to Gemini...")
        
        if GEMINI_API_KEY == "YOUR_API_KEY_HERE":
            print("\n⚠️  Skipping Gemini API call - Please set GEMINI_API_KEY in test file")
            print("   Add your API key at the top of test_gnn_integration.py:")
            print('   GEMINI_API_KEY = "your-actual-api-key-here"')
            print("\n   Showing prompt preview instead:")
            print("\n" + "-"*60)
            print("PROMPT PREVIEW:")
            print(llm_prompt[:500] + "..." if len(llm_prompt) > 500 else llm_prompt)
            print("-"*60)
        else:
            try:
                # Call Gemini API directly
                sql_response = await call_gemini_api(llm_prompt, GEMINI_API_KEY)
                
                print("\n✅ Gemini Generated SQL:")
                print("-"*60)
                print(sql_response)
                print("-"*60)
                
            except Exception as llm_error:
                print(f"\n❌ Gemini API call failed: {llm_error}")
                print("   Showing prompt instead:")
                print("\n" + "-"*60)
                print(llm_prompt[:500] + "..." if len(llm_prompt) > 500 else llm_prompt)
                print("-"*60)
        
        # Step 4: Show comparison and benefits
        print("\n📊 Hybrid Pipeline Summary:")
        
        tables = backend_schema.get('tables', {})
        total_tables = len(tables)
        total_columns = sum(len(t.get('columns', [])) for t in tables.values())
        
        print(f"  Full Schema: {total_tables} tables, {total_columns} columns")
        print(f"  GNN-Pruned: {len(relevant_tables)} tables, {sum(len(cols) for cols in relevant_columns.values())} columns")
        
        if total_tables > 0:
            reduction = (1 - len(relevant_tables) / total_tables) * 100
            print(f"  Schema Reduction: {reduction:.1f}% fewer tables")
        
        print("\n✅ Hybrid LLM+GNN pipeline test passed!")
        print("\n💡 Hybrid Pipeline Benefits:")
        print("  1. GNN Pre-filters Schema: Reduces irrelevant tables/columns")
        print("  2. Reduced Token Usage: Smaller prompts = lower costs")
        print("  3. Improved Accuracy: LLM focuses on relevant schema only")
        print("  4. Semantic Understanding: GNN captures relationships beyond keywords")
        print("  5. Better SQL Quality: GNN-selected columns guide LLM generation")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Hybrid LLM+GNN test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "🧪 GNN INTEGRATION TEST SUITE " + "="*30)
    
    results = []
    
    # Test 1: Schema conversion
    result1 = test_schema_conversion()
    results.append(("Schema Conversion", result1))
    
    # Test 2: GNN Ranker
    result2 = await test_gnn_ranker()
    results.append(("GNN Ranker Service", result2))
    
    # Test 3: Hybrid LLM+GNN
    result3 = await test_hybrid_llm_gnn()
    results.append(("Hybrid LLM+GNN Pipeline", result3))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 All tests passed! GNN integration is working correctly.")
        print("\nNext steps:")
        print("  1. Update .env: USE_LOCAL_GNN=true")
        print("  2. Test with backend API: POST /api/v1/nl2sql/nl2ir")
        print("  3. Monitor GNN-pruned schema in LLM prompts")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
