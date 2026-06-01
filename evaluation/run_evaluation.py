"""
NL2SQL Evaluation Script — Execution Accuracy & Token Reduction
===============================================================
Measures two core metrics for the research paper:

1. EXECUTION ACCURACY (EX): Does the generated SQL return the same result set
   as the gold SQL when executed against the database?

2. TOKEN REDUCTION: How many prompt tokens does GNN pruning save compared
   to sending the full schema to the LLM?

Usage:
    cd backend
    python -m evaluation.run_evaluation --mysql-uri "mysql+pymysql://root:password@localhost:3306/nl2sql_target"

    # With specific options:
    python -m evaluation.run_evaluation \
        --mysql-uri "mysql+pymysql://root:password@localhost:3306/nl2sql_target" \
        --top-k 15 \
        --output results.json \
        --skip-llm           # Token reduction only, no LLM calls
"""
import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple

import sqlalchemy
from sqlalchemy import create_engine, text

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.schema_converter import SchemaConverter
from app.services.gnn_ranker_service import GNNRankerService
from app.services.prompt_templates import build_compact_schema_text, build_ir_prompt

logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def count_tokens(text: str) -> int:
    """
    Approximate token count.  Uses whitespace + punctuation splitting as a
    cheap proxy (avoids tiktoken dependency). For research‐paper numbers you
    may swap in tiktoken or the Gemini tokenizer later.
    """
    import re
    tokens = re.findall(r"\w+|[^\w\s]", text, re.UNICODE)
    return len(tokens)


def normalize_result_set(rows: List[Dict]) -> Set[str]:
    """Normalize a result set for comparison — order-independent."""
    normalized = set()
    for row in rows:
        # Sort keys for deterministic tuple, cast values to str
        parts = tuple(str(row[k]) for k in sorted(row.keys()))
        normalized.add(parts)
    return normalized


def results_match(rows_a: List[Dict], rows_b: List[Dict]) -> bool:
    """
    Check execution accuracy: two result sets match if they contain the same
    rows (order-independent) with the same values.
    """
    if not rows_a and not rows_b:
        return True
    if not rows_a or not rows_b:
        return False
    # Column count must match
    if len(rows_a[0]) != len(rows_b[0]):
        return False
    return normalize_result_set(rows_a) == normalize_result_set(rows_b)


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class QueryResult:
    query_id: str
    nl_query: str
    difficulty: str
    category: str
    gold_sql: str
    generated_sql: Optional[str] = None
    # Execution accuracy
    gold_executed: bool = False
    gen_executed: bool = False
    execution_match: bool = False
    gold_row_count: int = 0
    gen_row_count: int = 0
    gold_error: Optional[str] = None
    gen_error: Optional[str] = None
    # Token reduction
    full_schema_tokens: int = 0
    pruned_schema_tokens: int = 0
    token_reduction_pct: float = 0.0
    compression_ratio: float = 0.0
    # GNN info
    gnn_nodes_returned: int = 0
    gnn_tables_selected: List[str] = field(default_factory=list)
    gnn_table_recall: float = 0.0
    tables_needed: List[str] = field(default_factory=list)
    # Timing
    gnn_time_ms: float = 0.0
    llm_time_ms: float = 0.0
    total_time_ms: float = 0.0


@dataclass
class EvalSummary:
    total_queries: int = 0
    # Execution accuracy
    execution_accuracy: float = 0.0
    ex_by_difficulty: Dict[str, float] = field(default_factory=dict)
    ex_by_category: Dict[str, float] = field(default_factory=dict)
    valid_sql_rate: float = 0.0
    # Token reduction
    avg_full_tokens: float = 0.0
    avg_pruned_tokens: float = 0.0
    avg_token_reduction_pct: float = 0.0
    avg_compression_ratio: float = 0.0
    # GNN
    avg_table_recall: float = 0.0
    avg_gnn_time_ms: float = 0.0
    # Timing
    avg_total_time_ms: float = 0.0


# ─── Schema extraction ────────────────────────────────────────────────────────

def extract_schema_from_db(engine: sqlalchemy.engine.Engine, db_name: str) -> Dict[str, Any]:
    """Extract schema in the backend format the pipeline expects."""
    inspector = sqlalchemy.inspect(engine)
    tables_dict = {}

    for table_name in inspector.get_table_names():
        columns = []
        pk_cols = set()
        try:
            pk_constraint = inspector.get_pk_constraint(table_name)
            pk_cols = set(pk_constraint.get("constrained_columns", []))
        except Exception:
            pass

        for col in inspector.get_columns(table_name):
            columns.append({
                "name": col["name"],
                "type": str(col["type"]),
                "primary_key": col["name"] in pk_cols,
                "nullable": col.get("nullable", True),
            })

        fks = []
        for fk in inspector.get_foreign_keys(table_name):
            fks.append({
                "constrained_columns": fk["constrained_columns"],
                "referred_table": fk["referred_table"],
                "referred_columns": fk["referred_columns"],
            })

        tables_dict[table_name] = {"columns": columns, "foreign_keys": fks}

    return {"database": db_name, "tables": tables_dict}


# ─── Core evaluation ──────────────────────────────────────────────────────────

def execute_sql_safely(engine: sqlalchemy.engine.Engine, sql: str) -> Tuple[bool, List[Dict], Optional[str]]:
    """Execute SQL and return (success, rows, error)."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = [dict(row._mapping) for row in result.fetchall()]
            return True, rows, None
    except Exception as e:
        return False, [], str(e)


async def evaluate_token_reduction(
    schema: Dict[str, Any],
    gnn_ranker: GNNRankerService,
    query: str,
    top_k: int,
    tables_needed: List[str],
) -> Dict[str, Any]:
    """Compute token reduction metrics for a single query."""
    # Full schema text (no GNN pruning)
    full_schema_text = build_compact_schema_text(schema, max_columns_per_table=100, gnn_top_nodes=None)
    full_tokens = count_tokens(full_schema_text)

    # GNN-pruned schema
    t0 = time.perf_counter()
    gnn_nodes = await gnn_ranker.score_schema_nodes(query=query, backend_schema=schema, top_k=top_k)
    gnn_time_ms = (time.perf_counter() - t0) * 1000

    pruned_schema_text = build_compact_schema_text(schema, gnn_top_nodes=gnn_nodes)
    pruned_tokens = count_tokens(pruned_schema_text)

    # Table recall
    gnn_tables = set()
    for node in gnn_nodes:
        nid = node.get("node_id", "")
        if nid.startswith("table:"):
            gnn_tables.add(nid.replace("table:", "").lower())
        elif nid.startswith("column:"):
            parts = nid.replace("column:", "").split(".")
            if parts:
                gnn_tables.add(parts[0].lower())
    needed = set(t.lower() for t in tables_needed)
    recall = len(gnn_tables & needed) / len(needed) if needed else 1.0

    reduction_pct = ((full_tokens - pruned_tokens) / full_tokens * 100) if full_tokens else 0
    compression = full_tokens / pruned_tokens if pruned_tokens else 0

    return {
        "full_schema_text": full_schema_text,
        "pruned_schema_text": pruned_schema_text,
        "full_tokens": full_tokens,
        "pruned_tokens": pruned_tokens,
        "reduction_pct": round(reduction_pct, 2),
        "compression_ratio": round(compression, 2),
        "gnn_nodes": gnn_nodes,
        "gnn_tables": sorted(gnn_tables),
        "table_recall": round(recall, 4),
        "gnn_time_ms": round(gnn_time_ms, 2),
    }


async def generate_sql_via_llm(
    pruned_schema_text: str,
    query: str,
    llm_service,
) -> Tuple[Optional[str], float]:
    """Call LLM (via project's LLMService) to generate SQL. Returns (sql, latency_ms)."""
    prompt = build_ir_prompt(pruned_schema_text, query)

    t0 = time.perf_counter()
    ir_text = llm_service.generate(prompt, temperature=0.01, max_tokens=2048)
    latency = (time.perf_counter() - t0) * 1000

    ir_text = ir_text.strip()

    # Try to parse IR JSON and compile to SQL
    try:
        # Strip markdown fences if present
        if ir_text.startswith("```"):
            lines = ir_text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            ir_text = "\n".join(lines)

        import re
        json_match = re.search(r'\{.*\}', ir_text, re.DOTALL)
        if json_match:
            ir_json = json.loads(json_match.group())
        else:
            return None, latency

        # Compile IR → SQL using the project's own compiler
        from app.services.ir_models import QueryIR
        from app.services.ir_compiler import IRToMySQLCompiler

        # Sanitize IR (reuse pipeline logic)
        from app.services.pipeline_orchestrator import PipelineOrchestrator
        orch = PipelineOrchestrator.__new__(PipelineOrchestrator)
        orch._sanitize_ir_json(ir_json)

        ir_obj = QueryIR(**ir_json)
        compiler = IRToMySQLCompiler()
        sql, params = compiler.compile(ir_obj)
        return sql, latency

    except Exception as e:
        logger.warning(f"IR compilation failed, trying raw SQL extraction: {e}")
        # Fallback: try to extract raw SQL from response
        sql_match = re.search(r'(SELECT\s.+?)(?:;|\Z)', ir_text, re.DOTALL | re.IGNORECASE)
        if sql_match:
            return sql_match.group(1).strip(), latency
        return None, latency


# ─── Main evaluation loop ────────────────────────────────────────────────────

async def run_evaluation(
    mysql_uri: str,
    benchmark_path: str,
    model_path: str,
    top_k: int = 15,
    skip_llm: bool = False,
    llm_provider: str = "huggingface",
    gemini_api_key: Optional[str] = None,
    gemini_model: str = "gemini-2.5-flash",
    hf_api_key: Optional[str] = None,
    hf_model: str = "Qwen/Qwen2.5-Coder-32B-Instruct",
    output_path: Optional[str] = None,
    top_k_values: Optional[List[int]] = None,
):
    engine = create_engine(mysql_uri)
    db_name = mysql_uri.rsplit("/", 1)[-1].split("?")[0]

    print("=" * 70)
    print("  NL2SQL EVALUATION — Execution Accuracy & Token Reduction")
    print("=" * 70)

    # 1. Load benchmark
    with open(benchmark_path) as f:
        benchmark = json.load(f)
    print(f"\n  Benchmark:  {len(benchmark)} queries loaded")

    # 2. Extract live schema
    print(f"  Database:   {db_name}")
    schema = extract_schema_from_db(engine, db_name)
    table_count = len(schema["tables"])
    col_count = sum(len(t["columns"]) for t in schema["tables"].values())
    print(f"  Schema:     {table_count} tables, {col_count} columns")

    # 3. Initialize GNN ranker
    print(f"  GNN model:  {model_path}")
    gnn_ranker = GNNRankerService(
        model_path=model_path,
        device="cpu",
        use_rich_node_embeddings=True,
    )
    print(f"  Top-K:      {top_k}")
    print(f"  LLM calls:  {'ENABLED (' + llm_provider + ')' if not skip_llm else 'SKIPPED'}")
    print("=" * 70)

    # 4. Initialize LLM service (if needed)
    llm_service = None
    if not skip_llm:
        from app.services.llm_service import LLMService
        llm_service = LLMService(
            provider=llm_provider,
            gemini_api_key=gemini_api_key,
            gemini_model=gemini_model,
            hf_api_key=hf_api_key,
            hf_model=hf_model,
        )

    # ── Top-K sensitivity analysis ────────────────────────────────────────
    if top_k_values:
        print("\n\n" + "=" * 70)
        print("  TOP-K SENSITIVITY ANALYSIS")
        print("=" * 70)

        for k in top_k_values:
            recalls = []
            reductions = []
            for q in benchmark:
                tr = await evaluate_token_reduction(
                    schema, gnn_ranker, q["nl_query"], k, q["tables_needed"]
                )
                recalls.append(tr["table_recall"])
                reductions.append(tr["reduction_pct"])
            avg_recall = sum(recalls) / len(recalls) * 100
            avg_reduction = sum(reductions) / len(reductions)
            perfect_recall = sum(1 for r in recalls if r == 1.0) / len(recalls) * 100
            print(
                f"  K={k:3d}  |  Table Recall: {avg_recall:5.1f}%  "
                f"|  Perfect Recall: {perfect_recall:5.1f}%  "
                f"|  Token Reduction: {avg_reduction:5.1f}%"
            )
        print("=" * 70)

    # ── Per-query evaluation ──────────────────────────────────────────────
    results: List[QueryResult] = []

    for i, q in enumerate(benchmark, 1):
        qr = QueryResult(
            query_id=q["id"],
            nl_query=q["nl_query"],
            difficulty=q["difficulty"],
            category=q["category"],
            gold_sql=q["gold_sql"],
            tables_needed=q["tables_needed"],
        )

        print(f"\n[{i}/{len(benchmark)}] {q['id']} ({q['difficulty']}) — {q['nl_query'][:60]}")

        # ── Token reduction ───────────────────────────────────────────────
        tr = await evaluate_token_reduction(
            schema, gnn_ranker, q["nl_query"], top_k, q["tables_needed"]
        )
        qr.full_schema_tokens = tr["full_tokens"]
        qr.pruned_schema_tokens = tr["pruned_tokens"]
        qr.token_reduction_pct = tr["reduction_pct"]
        qr.compression_ratio = tr["compression_ratio"]
        qr.gnn_nodes_returned = len(tr["gnn_nodes"])
        qr.gnn_tables_selected = tr["gnn_tables"]
        qr.gnn_table_recall = tr["table_recall"]
        qr.gnn_time_ms = tr["gnn_time_ms"]

        print(f"   Tokens: {tr['full_tokens']} → {tr['pruned_tokens']}  "
              f"(−{tr['reduction_pct']}%)  Compression: {tr['compression_ratio']}x  "
              f"Table recall: {tr['table_recall']*100:.0f}%")

        # ── Execution accuracy ────────────────────────────────────────────
        # Execute gold SQL
        ok, gold_rows, err = execute_sql_safely(engine, q["gold_sql"])
        qr.gold_executed = ok
        qr.gold_row_count = len(gold_rows)
        qr.gold_error = err
        if err:
            print(f"   ⚠ Gold SQL error: {err[:80]}")

        if not skip_llm and llm_service:
            gen_sql, llm_ms = await generate_sql_via_llm(
                tr["pruned_schema_text"], q["nl_query"], llm_service
            )
            qr.generated_sql = gen_sql
            qr.llm_time_ms = llm_ms
            qr.total_time_ms = tr["gnn_time_ms"] + llm_ms

            if gen_sql:
                ok2, gen_rows, err2 = execute_sql_safely(engine, gen_sql)
                qr.gen_executed = ok2
                qr.gen_row_count = len(gen_rows)
                qr.gen_error = err2
                if ok and ok2:
                    qr.execution_match = results_match(gold_rows, gen_rows)
                status = "✓" if qr.execution_match else "✗"
                print(f"   SQL: {gen_sql[:80]}...")
                print(f"   Exec match: {status}  "
                      f"(gold: {qr.gold_row_count} rows, gen: {qr.gen_row_count} rows)  "
                      f"LLM: {llm_ms:.0f}ms")
            else:
                print("   ✗ LLM failed to generate SQL")

        results.append(qr)

    # ── Summary ───────────────────────────────────────────────────────────
    summary = compute_summary(results, skip_llm)
    print_summary(summary, results, skip_llm)

    # ── Save results ──────────────────────────────────────────────────────
    out_path = output_path or os.path.join(os.path.dirname(__file__), "eval_results.json")
    output = {
        "summary": asdict(summary),
        "results": [asdict(r) for r in results],
    }
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nResults saved to {out_path}")


def compute_summary(results: List[QueryResult], skip_llm: bool) -> EvalSummary:
    s = EvalSummary(total_queries=len(results))

    # Token reduction (always computed)
    s.avg_full_tokens = sum(r.full_schema_tokens for r in results) / len(results)
    s.avg_pruned_tokens = sum(r.pruned_schema_tokens for r in results) / len(results)
    s.avg_token_reduction_pct = sum(r.token_reduction_pct for r in results) / len(results)
    s.avg_compression_ratio = sum(r.compression_ratio for r in results) / len(results)
    s.avg_table_recall = sum(r.gnn_table_recall for r in results) / len(results)
    s.avg_gnn_time_ms = sum(r.gnn_time_ms for r in results) / len(results)

    if not skip_llm:
        # Execution accuracy
        attempted = [r for r in results if r.generated_sql is not None]
        if attempted:
            s.execution_accuracy = sum(1 for r in attempted if r.execution_match) / len(attempted)
            s.valid_sql_rate = sum(1 for r in attempted if r.gen_executed) / len(attempted)
        s.avg_total_time_ms = sum(r.total_time_ms for r in results) / len(results)

        # By difficulty
        for diff in ("easy", "medium", "hard", "extra_hard"):
            subset = [r for r in attempted if r.difficulty == diff]
            if subset:
                s.ex_by_difficulty[diff] = sum(1 for r in subset if r.execution_match) / len(subset)

        # By category
        cats = set(r.category for r in attempted)
        for cat in sorted(cats):
            subset = [r for r in attempted if r.category == cat]
            if subset:
                s.ex_by_category[cat] = sum(1 for r in subset if r.execution_match) / len(subset)

    return s


def print_summary(summary: EvalSummary, results: List[QueryResult], skip_llm: bool):
    print("\n\n" + "=" * 70)
    print("  EVALUATION RESULTS SUMMARY")
    print("=" * 70)

    print(f"\n  Total queries evaluated: {summary.total_queries}")

    # ── Token Reduction ───────────────────────────────────────────────────
    print("\n  ── TOKEN REDUCTION ──────────────────────────────────────────")
    print(f"  Avg full schema tokens:   {summary.avg_full_tokens:.0f}")
    print(f"  Avg pruned schema tokens: {summary.avg_pruned_tokens:.0f}")
    print(f"  Avg token reduction:      {summary.avg_token_reduction_pct:.1f}%")
    print(f"  Avg compression ratio:    {summary.avg_compression_ratio:.2f}x")
    print(f"  Avg GNN table recall:     {summary.avg_table_recall*100:.1f}%")
    print(f"  Avg GNN inference time:   {summary.avg_gnn_time_ms:.1f} ms")

    if not skip_llm:
        # ── Execution Accuracy ────────────────────────────────────────────
        print("\n  ── EXECUTION ACCURACY ───────────────────────────────────────")
        print(f"  Overall EX:           {summary.execution_accuracy*100:.1f}%")
        print(f"  Valid SQL rate:       {summary.valid_sql_rate*100:.1f}%")
        print(f"  Avg total latency:    {summary.avg_total_time_ms:.0f} ms")

        if summary.ex_by_difficulty:
            print("\n  By Difficulty:")
            for diff, acc in summary.ex_by_difficulty.items():
                count = sum(1 for r in results if r.difficulty == diff)
                print(f"    {diff:12s}  {acc*100:5.1f}%  ({count} queries)")

        if summary.ex_by_category:
            print("\n  By Category:")
            for cat, acc in summary.ex_by_category.items():
                count = sum(1 for r in results if r.category == cat)
                print(f"    {cat:28s}  {acc*100:5.1f}%  ({count} queries)")

    print("\n" + "=" * 70)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="NL2SQL Evaluation: Execution Accuracy & Token Reduction")
    parser.add_argument("--mysql-uri", required=True, help="SQLAlchemy MySQL URI")
    parser.add_argument("--benchmark", default=None, help="Path to benchmark JSON (default: evaluation/benchmark_queries.json)")
    parser.add_argument("--model-path", default=None, help="Path to GNN model (default: backend/models/gnn/best_model.pt)")
    parser.add_argument("--top-k", type=int, default=15, help="Top-K for GNN pruning (default: 15)")
    parser.add_argument("--top-k-sweep", nargs="*", type=int, default=None, help="Run Top-K sensitivity analysis with these values (e.g. --top-k-sweep 5 10 15 20 30 50)")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM calls (token reduction only)")
    parser.add_argument("--provider", default="huggingface", choices=["gemini", "huggingface"], help="LLM provider")
    parser.add_argument("--gemini-key", default=None, help="Gemini API key (or set GEMINI_API_KEY env var)")
    parser.add_argument("--gemini-model", default="gemini-2.5-flash", help="Gemini model name")
    parser.add_argument("--hf-key", default=None, help="HuggingFace API key (or set HF_API_KEY env var)")
    parser.add_argument("--hf-model", default="Qwen/Qwen2.5-Coder-32B-Instruct", help="HuggingFace model name")
    parser.add_argument("--output", default=None, help="Output JSON path")
    args = parser.parse_args()

    root = os.path.dirname(os.path.dirname(__file__))  # NL2SQL root
    benchmark_path = args.benchmark or os.path.join(root, "evaluation", "benchmark_queries.json")
    model_path = args.model_path or os.path.join(root, "backend", "models", "gnn", "best_model.pt")
    gemini_key = args.gemini_key or os.environ.get("GEMINI_API_KEY")
    hf_key = args.hf_key or os.environ.get("HF_API_KEY")

    if not args.skip_llm:
        if args.provider == "gemini" and not gemini_key:
            print("WARNING: No Gemini API key provided. Running in --skip-llm mode.")
            args.skip_llm = True
        elif args.provider == "huggingface" and not hf_key:
            print("WARNING: No HuggingFace API key provided. Running in --skip-llm mode.")
            args.skip_llm = True

    asyncio.run(run_evaluation(
        mysql_uri=args.mysql_uri,
        benchmark_path=benchmark_path,
        model_path=model_path,
        top_k=args.top_k,
        skip_llm=args.skip_llm,
        llm_provider=args.provider,
        gemini_api_key=gemini_key,
        gemini_model=args.gemini_model,
        hf_api_key=hf_key,
        hf_model=args.hf_model,
        output_path=args.output,
        top_k_values=args.top_k_sweep,
    ))


if __name__ == "__main__":
    main()
