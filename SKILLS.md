# Data Normalization Protocol

## 1. Goal

Your SOLE purpose is to convert any input file into a **Normalized CSV** that matches our strict engine requirements.

## 2. Target Schema (Strict)

You must transform input data to contain EXACTLY these 3 columns:

- `std_date`: (YYYY-MM-DD) The transaction date.
- `std_desc`: (String) Narrative or description.
- `std_amt`: (Float) The signed amount.
  - **Negative (-):** Money leaving the account (Withdrawals, Debits, Expenses).
  - **Positive (+):** Money entering the account (Deposits, Credits, Income).

## 3. Transformation Rules

1. **Identify Columns:** Look at the file header.
   - If you see "Debit" (money out) and "Credit" (money in): `std_amt = Credit - Debit`.
   - If you see "Amount" and "Type": Convert based on type logic.
2. **Clean Data:**
   - Remove currency symbols ($ , £).
   - Parse dates into standard ISO format (YYYY-MM-DD).
3. **Save Output:**
   - Save the cleaned bank data as `temp_norm_bank.csv`.
   - Save the cleaned ledger data as `temp_norm_ledger.csv`.
   - ONLY once both exist, call `run_audit_matching`.
