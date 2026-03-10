import torch

# Import all our helper functions and classes from utils.py
from utils import (
    get_embedding_model,
    load_causal_llm,
    text_to_sql,
    GNNRanker,
    EMBEDDING_MODEL_NAME,
    EMBEDDING_DIM,
    NODE_FEATURE_DIM,
    GNN_HIDDEN_CHANNELS,
    CODE_LLM_NAME,
    GNN_MODEL_PATH
)

# --- DEFINE A NEW, UNSEEN DATABASE SCHEMA ---
# This is a mock schema for an "eCommerce" store.
# It has the *exact same format* as the tables.json from Spider.
NEW_DB_SCHEMA = {
    "db_id": "ecommerce_store",
    "table_names_original": [
        "Customers",
        "Products",
        "Orders"
    ],
    "column_names_original": [
        [0, "customer_id"], # Col idx 0
        [0, "first_name"],  # Col idx 1
        [0, "last_name"],   # Col idx 2
        [0, "email"],       # Col idx 3
        [0, "city"],        # Col idx 4
        [1, "product_id"],  # Col idx 5
        [1, "name"],        # Col idx 6
        [1, "price"],       # Col idx 7
        [2, "order_id"],    # Col idx 8
        [2, "customer_id"], # Col idx 9 (FK)
        [2, "product_id"],  # Col idx 10 (FK)
        [2, "quantity"]     # Col idx 11
    ],
    "column_types": [
        "number",
        "text",
        "text",
        "text",
        "text",
        "number",
        "text",
        "number",
        "number",
        "number",
        "number",
        "number"
    ],
    "primary_keys": [0, 5, 8], # customer_id, product_id, order_id
    "foreign_keys": [
        [9, 0],  # Orders.customer_id -> Customers.customer_id
        [10, 5]  # Orders.product_id -> Products.product_id
    ]
}

def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device for inference: {device}")
    
    # --- 1. Load all PRE-TRAINED models ---
    
    # Load the Embedding model
    embed_model = get_embedding_model(EMBEDDING_MODEL_NAME, device)
    
    # Load the SQL-generating LLM
    sql_generator = load_causal_llm(CODE_LLM_NAME)
    
    # Load the GNN Ranker architecture
    gnn_model = GNNRanker(
        node_in_channels=NODE_FEATURE_DIM,
        q_in_channels=EMBEDDING_DIM,
        hidden_channels=GNN_HIDDEN_CHANNELS
    )
    
    # --- LOAD THE SAVED WEIGHTS ---
    try:
        gnn_model.load_state_dict(torch.load(GNN_MODEL_PATH, map_location=device))
        print(f"Successfully loaded trained GNN weights from {GNN_MODEL_PATH}")
    except FileNotFoundError:
        print(f"Error: Could not find GNN model file at {GNN_MODEL_PATH}")
        print("Please run train.py first to create this file.")
        return
    except Exception as e:
        print(f"Error loading GNN model weights: {e}")
        return
        
    gnn_model.to(device)
    gnn_model.eval() # Set model to evaluation mode (very important!)

    # --- 2. Run Inference on a New, Unseen Query ---
    
    print("\n--- Running Inference on New eCommerce Database ---")
    
    # This is the new, unseen user question
    new_question = "Find the first and last names of customers who bought 'Super-Widget'"
    
    # The `text_to_sql` function handles everything:
    # 1. Creates the new graph from NEW_DB_SCHEMA
    # 2. Runs the GNN
    # 3. Creates the prompt
    # 4. Runs the LLM
    generated_sql = text_to_sql(
        question=new_question,
        db_schema=NEW_DB_SCHEMA,
        gnn_model=gnn_model,
        embed_model=embed_model,
        sql_generator=sql_generator,
        device=device
    )
    
    print("\n--- Final Generated SQL (for New DB) ---")
    print(generated_sql)

    # --- Example 2 ---
    new_question_2 = "How many customers are from New York?"
    
    print("\n--- Running Inference Example 2 ---")
    generated_sql_2 = text_to_sql(
        question=new_question_2,
        db_schema=NEW_DB_SCHEMA,
        gnn_model=gnn_model,
        embed_model=embed_model,
        sql_generator=sql_generator,
        device=device
    )
    
    print("\n--- Final Generated SQL (Example 2) ---")
    print(generated_sql_2)

if __name__ == "__main__":
    main()
