# 1. Imports
import json
import torch
import re
import torch.nn.functional as F
from torch.optim import Adam
from torch.nn import Linear, Sigmoid
from torch_geometric.data import Data, Batch
from torch_geometric.loader import DataLoader
from torch_geometric.nn import GCNConv
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# --- 2. Configuration ---
# All shared constants
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
CODE_LLM_NAME = "codellama/CodeLlama-7b-Instruct-hf"
NODE_FEATURE_DIM = 5
GNN_HIDDEN_CHANNELS = 256
BATCH_SIZE = 8
LEARNING_RATE = 0.001
GNN_MODEL_PATH = "gnn_ranker.pth" # Path to save/load the trained GNN

# --- 3. GNN Model Class ---
class GNNRanker(torch.nn.Module):
    """The GNNRanker model definition."""
    def __init__(self, node_in_channels, q_in_channels, hidden_channels):
        super().__init__()
        self.conv1 = GCNConv(node_in_channels, hidden_channels)
        self.conv2 = GCNConv(hidden_channels, hidden_channels)
        self.classifier = Linear(hidden_channels + q_in_channels, 1)
        self.sigmoid = Sigmoid()

    def forward(self, x, edge_index, question_embedding, batch_index):
        h = self.conv1(x, edge_index).relu()
        h = F.dropout(h, p=0.5, training=self.training)
        h = self.conv2(h, edge_index).relu()
        q_emb_expanded = question_embedding[batch_index]
        combined_features = torch.cat([h, q_emb_expanded], dim=1)
        node_scores = self.classifier(combined_features)
        return self.sigmoid(node_scores)

# --- 4. Model Loading Functions ---

def get_embedding_model(model_name, device):
    """Loads the SentenceTransformer embedding model."""
    print(f"Loading embedding model: {model_name}...")
    model = SentenceTransformer(
        model_name, 
        device=device,
        trust_remote_code=True # Fix for latest transformers
    )
    print(f"Model {model_name} loaded.")
    return model

def load_causal_llm(model_id):
    """Loads the 4-bit quantized Causal LLM for SQL generation."""
    print(f"Loading 4-bit quantized model: {model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(
        model_id, 
        trust_remote_code=True
    )
    model_llm = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        device_map="auto",
        load_in_4bit=True,
        trust_remote_code=True
    )
    
    sql_generator = pipeline(
        "text-generation", 
        model=model_llm, 
        tokenizer=tokenizer,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    print("SQL Generation pipeline ready.")
    return sql_generator

# --- 5. Core Helper Functions ---

def get_text_embedding(text, model, device):
    """Gets a [1, EMBEDDING_DIM] embedding for a text string."""
    # Note: SentenceTransformer model should already be on the correct device
    embedding = model.encode(text, convert_to_tensor=True)
    return embedding.unsqueeze(0).to(device) # Shape: [1, 384]

def create_schema_graph(schema_info):
    """
    Converts a database schema (as a dict) into a PyG graph object.
    This works for *any* schema dict, seen or unseen.
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

    pk_col_indices = set(schema_info.get('primary_keys', []))
    fk_pairs = schema_info.get('foreign_keys', [])
    fk_col_indices = set(fk[0] for fk in fk_pairs)
    
    # 2. Add table nodes
    table_names = schema_info['table_names_original']
    for t_idx, t_name in enumerate(table_names):
        table_node_idx = current_node_idx
        table_to_node_idx[t_idx] = table_node_idx
        node_features.append([0.0, 1.0, 0.0, 0.0, 0.0])
        node_names.append(t_name)
        col_types.append(None)
        edges_src.extend([global_node_idx, table_node_idx])
        edges_dst.extend([table_node_idx, global_node_idx])
        current_node_idx += 1
        
    # 3. Add column nodes
    column_data = schema_info['column_names_original']
    column_type_data = schema_info['column_types']
    
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
        
        edges_src.extend([table_node_idx, col_node_idx])
        edges_dst.extend([col_node_idx, table_node_idx])
        edges_src.extend([global_node_idx, col_node_idx])
        edges_dst.extend([col_node_idx, global_node_idx])
        current_node_idx += 1

    # 4. Add foreign key edges
    original_c_idx_to_key = { k[1]: k for k, v in col_to_node_idx.items() if v != -1 }
    for (c_idx_1, c_idx_2) in fk_pairs:
        key1 = original_c_idx_to_key.get(c_idx_1)
        key2 = original_c_idx_to_key.get(c_idx_2)
        if key1 is None or key2 is None: continue
        node_1 = col_to_node_idx.get(key1)
        node_2 = col_to_node_idx.get(key2)
        if node_1 is not None and node_2 is not None:
            edges_src.extend([node_1, node_2])
            edges_dst.extend([node_2, node_1])

    edge_index = torch.tensor([edges_src, edges_dst], dtype=torch.long)
    x = torch.tensor(node_features, dtype=torch.float)
    
    graph = Data(x=x, edge_index=edge_index)
    graph.node_names = node_names
    graph.col_types = col_types 
    graph.db_id = schema_info['db_id']
    return graph

def get_labels_for_graph(graph, sql_query):
    """Creates training labels via string matching. (Used only by train.py)"""
    labels = torch.zeros(graph.num_nodes, 1)
    sql_query_lower = sql_query.lower()
    for i, full_name in enumerate(graph.node_names):
        name_lower = full_name.lower()
        if name_lower == "global" or "*" in name_lower: continue
        if '.' in name_lower: 
            table, col = name_lower.split('.')
            if re.search(r'\b' + re.escape(col) + r'\b', sql_query_lower):
                 labels[i] = 1.0
        else:
            if re.search(r'\b' + re.escape(name_lower) + r'\b', sql_query_lower):
                 labels[i] = 1.0
    return labels

def create_llm_prompt(question, graph, gnn_scores, top_k=10):
    """Uses GNN scores to build a pruned prompt for the LLM."""
    _, top_indices = torch.topk(gnn_scores, min(top_k, len(gnn_scores)))
    pruned_tables = set()
    
    for idx in top_indices.tolist():
        node_name = graph.node_names[idx]
        if node_name == "global" or "*" in node_name: continue
        if '.' in node_name: 
            table, col = node_name.split('.')
            pruned_tables.add(table)
        else: 
            pruned_tables.add(node_name)

    schema_str = ""
    table_defs = {table: [] for table in pruned_tables}
    
    for idx, node_name in enumerate(graph.node_names):
        if '.' in node_name:
            table, col = node_name.split('.')
            if table in pruned_tables:
                col_type = graph.col_types[idx]
                table_defs[table].append(f"{col} {col_type.upper()}")
                
    for table, cols in table_defs.items():
        if not cols: continue
        cols_str = ", ".join(cols)
        schema_str += f"CREATE TABLE {table} ({cols_str});\n"

    prompt = f"""### Instructions:
Your task is to convert a question into a SQL query, given a database schema.
Adhere to these rules:
- **Use ONLY the given tables and columns** in the schema.
- **Do not use any table or column that is not mentioned in the schema.**

### Input:
Schema:
{schema_str}

Question:
{question}

### Response:
```sql
"""
    return prompt

# --- 6. Core Inference Pipeline Function ---

def text_to_sql(question, db_schema, gnn_model, embed_model, sql_generator, device):
    """
    This is the FULL INFERENCE PIPELINE.
    It takes a new question and a new schema (dict) and returns SQL.
    """
    
    # 1. Create a graph from the *new* schema
    graph = create_schema_graph(db_schema)
    
    # 2. Get Question Embedding
    q_embedding = get_text_embedding(question, embed_model, device)
    
    # 3. Run GNN Ranker (in eval mode)
    gnn_model.eval()
    with torch.no_grad():
        # Create a single-item batch for the new graph
        single_item_batch = Batch.from_data_list([Data(
            x=graph.x.clone(), 
            edge_index=graph.edge_index.clone(),
            question_embedding=q_embedding.cpu()
        )]).to(device)
        
        scores = gnn_model(
            x=single_item_batch.x,
            edge_index=single_item_batch.edge_index,
            question_embedding=single_item_batch.question_embedding,
            batch_index=single_item_batch.batch
        ).squeeze().cpu()
    
    # 4. Create the prompt
    prompt = create_llm_prompt(question, graph, scores, top_k=15)
    
    print("--- Generated Prompt for LLM ---")
    print(prompt)
    
    # 5. Generate SQL
    response = sql_generator(
        prompt, 
        max_new_tokens=150, 
        num_return_sequences=1, 
        temperature=0.0,
        do_sample=False
    )
    
    generated_text = response[0]['generated_text']
    
    # 6. Extract SQL
    try:
        sql_query = generated_text.split("```sql")[1].split("```")[0].strip()
        return sql_query
    except IndexError:
        print("\n--- LLM PARSING FAILED ---")
        print("Raw response from LLM:")
        print(generated_text)
        return "Error: Could not parse SQL from LLM response."
    except Exception as e:
        print(f"An unexpected error occurred during SQL parsing: {e}")
        print(f"Full response: {generated_text}")
        return "Error: Could not parse SQL."
