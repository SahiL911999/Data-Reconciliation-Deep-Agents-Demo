"""
Production Reconciliation System - FINAL OPTIMIZED
Fixes:
1. Silences 'File Exists' errors by enforcing Python I/O.
2. Prevents 'String not found' errors.
3. Guarantees clean execution flow.
"""
import os
import sys
import pandas as pd
import numpy as np
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_experimental.tools import PythonAstREPLTool
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 1. THE DETERMINISTIC ENGINE
# ==========================================
def execute_reconciliation(norm_ledger_path: str, norm_bank_path: str) -> str:
    """
    The rigid math engine. Matches Absolute Values to handle sign mismatches.
    """
    print(f"⚙️ ENGINE: Reading files {norm_ledger_path} & {norm_bank_path}...")
    
    try:
        df_l = pd.read_csv(norm_ledger_path)
        df_b = pd.read_csv(norm_bank_path)
    except Exception as e:
        return f"ERROR: Could not read files. {e}"

    if df_l.empty or df_b.empty: return "ERROR: One of the normalized files is empty."

    # --- 1. SIGN NORMALIZATION ---
    # Create absolute value columns for matching
    df_l['abs_amt'] = df_l['std_amt'].abs()
    df_b['abs_amt'] = df_b['std_amt'].abs()
    
    matches = []
    matched_l = set()
    matched_b = set()

    print(f"   ... Matching {len(df_l)} Ledger rows against {len(df_b)} Bank rows...")

    # --- STRATEGY 1: EXACT MATCH (Absolute) ---
    for idx_l, row_l in df_l.iterrows():
        if idx_l in matched_l: continue
        
        candidates = df_b[~df_b.index.isin(matched_b)]
        exact = candidates[np.isclose(candidates['abs_amt'], row_l['abs_amt'], atol=0.01)]
        
        for idx_b, row_b in exact.iterrows():
            d_l = pd.to_datetime(row_l['std_date'])
            d_b = pd.to_datetime(row_b['std_date'])
            
            # 5 Day Tolerance
            if abs((d_b - d_l).days) <= 5:
                matches.append({
                    "Match_Quality": "Exact Match",
                    "Bank_Date": row_b['std_date'], "Bank_Desc": row_b['std_desc'], "Bank_Amt": row_b['std_amt'],
                    "Ledger_Date": row_l['std_date'], "Ledger_Desc": row_l['std_desc'], "Ledger_Amt": row_l['std_amt'],
                    "Difference": 0.0
                })
                matched_l.add(idx_l)
                matched_b.add(idx_b)
                break

    # --- STRATEGY 2: FEE MATCH (Stripe/PayPal) ---
    for idx_l, row_l in df_l.iterrows():
        if idx_l in matched_l: continue
        if row_l['abs_amt'] > 0: 
            candidates = df_b[~df_b.index.isin(matched_b)]
            # Check 96-99% match
            fee_candidates = candidates[
                (candidates['abs_amt'] < row_l['abs_amt']) & 
                (candidates['abs_amt'] > row_l['abs_amt'] * 0.96)
            ]
            for idx_b, row_b in fee_candidates.iterrows():
                d_l = pd.to_datetime(row_l['std_date'])
                d_b = pd.to_datetime(row_b['std_date'])
                if abs((d_b - d_l).days) <= 5:
                    matches.append({
                        "Match_Quality": "Partial Match (Fee)",
                        "Bank_Desc": row_b['std_desc'], "Ledger_Desc": row_l['std_desc'],
                        "Bank_Amt": row_b['std_amt'], "Ledger_Amt": row_l['std_amt'],
                        "Difference": round(row_b['abs_amt'] - row_l['abs_amt'], 2)
                    })
                    matched_l.add(idx_l)
                    matched_b.add(idx_b)
                    break

    # --- REPORT UNMATCHED ---
    for idx_b, row_b in df_b.iterrows():
        if idx_b not in matched_b:
            matches.append({"Match_Quality": "Unmatched Bank", "Bank_Date": row_b['std_date'], "Bank_Desc": row_b['std_desc'], "Bank_Amt": row_b['std_amt']})
            
    for idx_l, row_l in df_l.iterrows():
        if idx_l not in matched_l:
            matches.append({"Match_Quality": "Unmatched Ledger", "Ledger_Date": row_l['std_date'], "Ledger_Desc": row_l['std_desc'], "Ledger_Amt": row_l['std_amt']})

    output_path = "Reconciliation_Report.xlsx"
    pd.DataFrame(matches).to_excel(output_path, index=False)
    return f"SUCCESS: Report generated at {output_path} with {len(matches)} rows."

# ==========================================
# 2. TOOLS
# ==========================================
@tool
def inspect_file(filepath: str) -> str:
    """Reads first 5 rows."""
    try:
        if filepath.endswith('.csv'): df = pd.read_csv(filepath, nrows=5)
        else: df = pd.read_excel(filepath, nrows=5)
        return f"Columns: {list(df.columns)}\nPreview:\n{df.to_markdown()}"
    except Exception as e: return str(e)

# ==========================================
# 3. MAIN (Optimized Prompt)
# ==========================================
def main(query_str):
    print("🚀 System Online.")
    
    # SYSTEM PROMPT: ENFORCE PYTHON IO
    skills = """
    You are a Data Engineer Agent.
    
    YOUR JOB:
    1. Use the `python_interpreter` tool for EVERYTHING. 
    2. Inside the Python tool:
       a) Load the source files (bank & ledger) using pandas.
       b) Normalize them to columns [std_date, std_desc, std_amt].
       c) Save them as 'temp_norm_bank.csv' and 'temp_norm_ledger.csv' using `df.to_csv(index=False)`.
       d) Immediately call `execute_reconciliation('temp_norm_ledger.csv', 'temp_norm_bank.csv')`.

    FORBIDDEN:
    - DO NOT use the `write_file` or `edit_file` tools. They are clumsy. Use Python!
    - DO NOT write custom matching logic. Use the provided function.
    """

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    python_tool = PythonAstREPLTool(
        locals={"pd": pd, "np": np, "execute_reconciliation": execute_reconciliation},
        name="python_interpreter",
        description="Run Python. Use this to Load files, Save Normalized CSVs, and Run Reconciliation."
    )

    agent = create_deep_agent(
        model=llm,
        tools=[python_tool, inspect_file],
        backend=FilesystemBackend(),
        system_prompt=skills
    )

    print(f"📝 Task: {query_str}")
    print("-" * 60)
    
    try:
        for chunk in agent.stream({"messages": [("user", query_str)]}):
            if "agent" in chunk:
                print(f"🤖 AGENT: {chunk['agent']['messages'][0].content}")
            elif "tools" in chunk:
                t_msg = chunk['tools']['messages'][0]
                print(f"⚙️ TOOL: {t_msg.name}")
                if hasattr(t_msg, 'content'):
                     print(f"   ↳ {str(t_msg.content)[:300]}...")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        file_a = sys.argv[1]
        file_b = sys.argv[2]
        query = f"Reconcile '{file_a}' and '{file_b}'."
    else:
        query = "Reconcile 'bank_statement_real.csv' and 'ledger_export_real.csv'."

    main(query)