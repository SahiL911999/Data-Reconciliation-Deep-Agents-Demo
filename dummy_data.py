import pandas as pd
import random
import uuid
from datetime import datetime, timedelta

# --- CONFIGURATION ---
START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2025, 1, 31)
OUTPUT_LEDGER = "ledger_export_real.csv"
OUTPUT_BANK = "bank_statement_real.csv"

# --- REALISM HELPERS ---

def get_business_day_lag(date_obj, min_lag=1, max_lag=4):
    """
    Simulates clearing delays. Transactions made on Friday often clear Monday/Tuesday.
    """
    lag = random.randint(min_lag, max_lag)
    cleared_date = date_obj + timedelta(days=lag)
    # Simple check: if Sunday (6) or Saturday (5), push to Monday
    if cleared_date.weekday() >= 5: 
        cleared_date += timedelta(days=(7 - cleared_date.weekday()))
    return cleared_date

def noise_injector(clean_name, trans_type="DEBIT"):
    """
    Turns 'Uber' into 'POS DEBIT UBER TECHNOLOGIES CA 4402'.
    Real bank statements are rarely clean.
    """
    garbage_ids = str(uuid.uuid4())[:6].upper()
    
    templates = [
        f"{clean_name.upper()}", 
        f"POS {trans_type} {clean_name.upper()} {garbage_ids}",
        f"{clean_name[:5].upper()}... INC", # Truncated
        f"ACH W/D {clean_name.upper()}",
        f"{clean_name.upper()} LONDON GB",
        f"CARD 4492 {clean_name.upper()}"
    ]
    return random.choice(templates)

# --- DATA GENERATION ---

ledger_rows = []
bank_rows = []

# 1. THE "STRIPE/PAYPAL" TRAP (Net vs Gross)
# Reality: You record $1000 sale in Ledger, but Bank receives $967.80 (fees deducted).
# Agent Challenge: Needs to recognize the match despite the amount difference.
sale_date = datetime(2025, 1, 10)
gross_amount = 1250.00
stripe_fee = (gross_amount * 0.029) + 0.30 # Standard 2.9% + 30c
net_deposit = round(gross_amount - stripe_fee, 2)

ledger_rows.append({
    "Date": sale_date, "Description": "Client Invoice #1001 (Stripe)", 
    "Debit": 0, "Credit": gross_amount, "Ref": "INV-1001"
})
# Note: In real accounting, the fee is a separate expense entry, 
# but often the bank line is just the net deposit.
bank_rows.append({
    "Date": get_business_day_lag(sale_date), 
    "Description": "STRIPE PAYOUT TRANSFER 8823", 
    "Amount": net_deposit # Positive for deposit
})

# 2. THE PAYROLL BATCH (Many-to-One)
# Reality: Ledger has 3 employees. Bank has 1 lump sum withdrawal from payroll provider.
# Agent Challenge: Summing multiple ledger lines to match one bank line.
pay_date = datetime(2025, 1, 15)
employees = [("Alice Salary", 4500), ("Bob Salary", 4200), ("Charlie Salary", 3800)]
total_payroll = sum([e[1] for e in employees])

for name, amt in employees:
    ledger_rows.append({
        "Date": pay_date, "Description": name, 
        "Debit": amt, "Credit": 0, "Ref": "PAYROLL-JAN"
    })

bank_rows.append({
    "Date": pay_date, # Payroll is usually same-day wire
    "Description": "GUSTO PAYROLL DRAW 44920", 
    "Amount": -total_payroll
})

# 3. THE "UNCLEARED CHECK" (Timing Difference)
# Reality: You mailed a check on Jan 28. It hasn't cleared by Jan 31.
# Agent Challenge: Should mark as "Unmatched - Outstanding Check" (Not an error).
check_date = datetime(2025, 1, 28)
ledger_rows.append({
    "Date": check_date, "Description": "Payment to Contractor (Check #404)", 
    "Debit": 1500.00, "Credit": 0, "Ref": "CHK-404"
})
# NO CORRESPONDING BANK ENTRY (Check is in the mail)

# 4. THE "FORGOTTEN SUBSCRIPTION" (Missing in Ledger)
# Reality: Marketing signed up for a tool and didn't tell Finance.
# Agent Challenge: Flag as "Unmatched Bank Transaction".
sub_date = datetime(2025, 1, 20)
bank_rows.append({
    "Date": sub_date, 
    "Description": "MIDJOURNEY SUBSCRIP CA", 
    "Amount": -30.00
})
# NO CORRESPONDING LEDGER ENTRY

# 5. STANDARD MESSY TRANSACTIONS (The Noise)
vendors = ["Slack", "Google Cloud", "Delta Airlines", "WeWork", "Uber"]

for _ in range(15):
    vendor = random.choice(vendors)
    amt = round(random.uniform(50, 800), 2)
    t_date = datetime(2025, 1, random.randint(1, 25))
    
    # Ledger is clean
    ledger_rows.append({
        "Date": t_date, 
        "Description": f"{vendor} Expense", 
        "Debit": amt, "Credit": 0, "Ref": str(uuid.uuid4())[:8]
    })
    
    # Bank is noisy and delayed
    bank_rows.append({
        "Date": get_business_day_lag(t_date),
        "Description": noise_injector(vendor),
        "Amount": -amt
    })

# --- DATAFRAME CONSTRUCTION ---
df_ledger = pd.DataFrame(ledger_rows)
df_bank = pd.DataFrame(bank_rows)

# Final Polish
# 1. Sort by date
df_ledger = df_ledger.sort_values(by="Date")
df_bank = df_bank.sort_values(by="Date")

# 2. Format Dates to String (Standard CSV format)
df_ledger["Date"] = df_ledger["Date"].dt.strftime("%Y-%m-%d")
df_bank["Date"] = df_bank["Date"].dt.strftime("%Y-%m-%d")

# 3. Save
df_ledger.to_csv(OUTPUT_LEDGER, index=False)
df_bank.to_csv(OUTPUT_BANK, index=False)

print("Realistic Data Generated Successfully.")
print("Scenario Includes:")
print("1. 'Stripe Trap': Net Deposit in Bank vs Gross Sale in Ledger.")
print("2. 'Payroll Batch': 3 Ledger entries vs 1 Bank withdrawal.")
print("3. 'Outstanding Check': Ledger entry with NO bank match (Check in transit).")
print("4. 'Ghost Subscription': Bank charge with NO ledger entry.")