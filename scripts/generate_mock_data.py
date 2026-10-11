"""
Generate mock datasets for the Loan Risk Reporting Automation portfolio project.

Creates two CSV files that mimic two Snowflake source tables:

    data/raw/loan_portfolio_risk.csv           -> LOAN_DATA.LOAN_PORTFOLIO_RISK.LOAN_RISK_MONITORING
    data/raw/customer_responsible_contact.csv  -> LOAN_DATA.CUSTOMER_RESPONSIBLE_CONTACT.CUSTOMER_RESPONSIBLE

All companies, people, e-mails and phone numbers are fictional. E-mail addresses use
the reserved `.example` top-level domain so they can never reach a real inbox.

The data is intentionally "messy" in the ways real source data usually is
(inconsistent casing, stray whitespace, duplicate loads, reassigned customer
responsibles, mixed phone formats, missing matches) so the cleaning steps in the
notebook have real problems to solve.

Usage:
    python scripts/generate_mock_data.py
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

SEED = 42
N_CUSTOMERS = 800
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

random.seed(SEED)
np.random.seed(SEED)

# --------------------------------------------------------------------------------------
# Reference data
# --------------------------------------------------------------------------------------
COUNTRIES = {
    "Norway": {"iso": "NO", "currency": "NOK", "locale": "no_NO", "dial": "47",
               "suffix": ["AS", "AS", "AS", "ASA"], "weight": 0.32},
    "Sweden": {"iso": "SE", "currency": "SEK", "locale": "sv_SE", "dial": "46",
               "suffix": ["AB", "AB", "AB", "HB"], "weight": 0.28},
    "Denmark": {"iso": "DK", "currency": "DKK", "locale": "da_DK", "dial": "45",
                "suffix": ["A/S", "ApS", "ApS", "A/S"], "weight": 0.20},
    "Finland": {"iso": "FI", "currency": "EUR", "locale": "fi_FI", "dial": "358",
                "suffix": ["Oy", "Oy", "Oyj", "Oy"], "weight": 0.20},
}

BRANCHES = {
    "Norway": [("NO01", "Oslo Sentrum"), ("NO02", "Bergen"), ("NO03", "Trondheim"), ("NO04", "Stavanger")],
    "Sweden": [("SE01", "Stockholm City"), ("SE02", "Göteborg"), ("SE03", "Malmö")],
    "Denmark": [("DK01", "København"), ("DK02", "Aarhus"), ("DK03", "Odense")],
    "Finland": [("FI01", "Helsinki"), ("FI02", "Tampere"), ("FI03", "Turku")],
}

LOAN_TYPES = {
    "Term Loan": 0.30,
    "Revolving Credit Facility": 0.18,
    "Overdraft Facility": 0.14,
    "Commercial Real Estate Loan": 0.16,
    "Asset Finance / Leasing": 0.14,
    "Trade Finance": 0.08,
}

# Risk rating 1 (lowest risk) to 10 (highest). Skewed towards healthy customers.
RISK_RATING_WEIGHTS = [0.06, 0.12, 0.17, 0.18, 0.15, 0.12, 0.09, 0.06, 0.03, 0.02]

NAME_PARTS = {
    "Norway": (["Fjord", "Nord", "Vest", "Polar", "Berg", "Skog", "Havbris", "Nordlys", "Stein", "Elve",
                "Dal", "Tind", "Kyst", "Viking", "Midnatt", "Isbre", "Lyng", "Furu"],
               ["Logistikk", "Bygg", "Eiendom", "Sjømat", "Energi", "Teknologi", "Maskin", "Transport",
                "Handel", "Konsult", "Elektro", "Industri", "Marine", "Trelast", "Agri"]),
    "Sweden": (["Norr", "Sjö", "Björk", "Gran", "Älv", "Fjäll", "Dal", "Ström", "Ek", "Lin",
                "Skär", "Vind", "Sol", "Mal", "Berg", "Ljung", "Hav", "Sten"],
               ["Bygg", "Fastigheter", "Logistik", "Teknik", "Industri", "Handel", "Energi", "Transport",
                "Konsult", "Verkstad", "Livs", "Media", "Mekan", "Skog", "Data"]),
    "Denmark": (["Nord", "Strand", "Bøg", "Fjord", "Hav", "Lys", "Vind", "Mark", "Skov", "Sø",
                 "Kyst", "Klint", "Hede", "Bro", "Lund", "Vang", "Klit", "Ager"],
                ["Byg", "Ejendomme", "Logistik", "Teknik", "Handel", "Energi", "Transport", "Rådgivning",
                 "Fødevarer", "Industri", "Møbler", "Medico", "Agro", "Design", "Data"]),
    "Finland": (["Järvi", "Metsä", "Kivi", "Revon", "Lumi", "Koski", "Saari", "Tuuli", "Kallio", "Aalto",
                 "Ranta", "Kuusi", "Mänty", "Laakso", "Vuori", "Sammal", "Pohjan", "Aurora"],
                ["Rakennus", "Kiinteistöt", "Logistiikka", "Tekniikka", "Kauppa", "Energia", "Kuljetus",
                 "Konsultointi", "Elintarvike", "Teollisuus", "Puu", "Metalli", "Media", "Data", "Agro"]),
}

FAKERS = {c: Faker(meta["locale"]) for c, meta in COUNTRIES.items()}
for f in FAKERS.values():
    f.seed_instance(SEED)

SNAPSHOT_DATE = date(2026, 9, 30)  # month-end risk monitoring snapshot


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def weighted_choice(options: dict[str, float]) -> str:
    keys, weights = zip(*options.items())
    return random.choices(keys, weights=weights, k=1)[0]


def ascii_slug(text: str) -> str:
    table = str.maketrans({"æ": "ae", "ø": "o", "å": "a", "ä": "a", "ö": "o", "ü": "u",
                           "Æ": "Ae", "Ø": "O", "Å": "A", "Ä": "A", "Ö": "O", "é": "e"})
    return text.translate(table).lower().replace(" ", "").replace("-", "")


def company_name(country: str, used: set[str]) -> str:
    prefixes, sectors = NAME_PARTS[country]
    while True:
        name = f"{random.choice(prefixes)}{random.choice(sectors).lower()} {random.choice(COUNTRIES[country]['suffix'])}"
        if random.random() < 0.25:
            name = f"{random.choice(prefixes)} {random.choice(sectors)} {random.choice(COUNTRIES[country]['suffix'])}"
        if name not in used:
            used.add(name)
            return name


def messy_phone(country: str) -> str:
    """Return a phone number in one of several inconsistent formats."""
    dial = COUNTRIES[country]["dial"]
    local = "".join(str(random.randint(0, 9)) for _ in range(8 if country != "Finland" else 9))
    local = ("4" if country in ("Norway", "Finland") else "7") + local[1:]
    fmt = random.choices(["intl_spaced", "intl_compact", "double_zero", "local"],
                         weights=[0.45, 0.25, 0.15, 0.15])[0]
    if fmt == "intl_spaced":
        return f"+{dial} {local[:3]} {local[3:5]} {local[5:]}"
    if fmt == "intl_compact":
        return f"+{dial}{local}"
    if fmt == "double_zero":
        return f"00{dial}{local}"
    return local


def messy_country(country: str) -> str:
    r = random.random()
    if r < 0.86:
        return country
    if r < 0.91:
        return country.upper()
    if r < 0.95:
        return country.lower()
    return COUNTRIES[country]["iso"]


# --------------------------------------------------------------------------------------
# 1. Customer responsibles (bank employees) – 3 per branch
# --------------------------------------------------------------------------------------
employees = []
emp_counter = 1000
for country, branch_list in BRANCHES.items():
    fk = FAKERS[country]
    for branch_id, branch_name in branch_list:
        for _ in range(3):
            first, last = fk.first_name(), fk.last_name()
            emp_counter += 1
            employees.append({
                "EMPLOYEE_ID": f"E{emp_counter}",
                "CUSTOMER_RESPONSIBLE_NAME": f"{first} {last}",
                "EMAIL": f"{ascii_slug(first)}.{ascii_slug(last)}@nordicbank.example",
                "PHONE": messy_phone(country),
                "BRANCH_ID": branch_id,
                "BRANCH_NAME": branch_name,
                "COUNTRY": country,
                "ROLE_TITLE": random.choice(["Relationship Manager", "Senior Relationship Manager",
                                             "Corporate Banker", "Customer Responsible"]),
            })
emp_df = pd.DataFrame(employees)

# --------------------------------------------------------------------------------------
# 2. Loan portfolio risk monitoring – one row per customer (ORG_ID is the key)
# --------------------------------------------------------------------------------------
used_names: set[str] = set()
country_keys = list(COUNTRIES)
country_weights = [COUNTRIES[c]["weight"] for c in country_keys]

loans, assignments = [], []
for i in range(N_CUSTOMERS):
    country = random.choices(country_keys, weights=country_weights)[0]
    branch_id, branch_name = random.choice(BRANCHES[country])
    responsible = emp_df[emp_df.BRANCH_ID == branch_id].sample(1, random_state=random.randint(0, 10**6)).iloc[0]

    org_id = f"ORG{100001 + i}"
    rating = random.choices(range(1, 11), weights=RISK_RATING_WEIGHTS)[0]
    loan_type = weighted_choice(LOAN_TYPES)
    exposure = round(float(np.random.lognormal(mean=15.2, sigma=1.1)), -3)
    if loan_type == "Overdraft Facility":
        exposure = round(exposure * 0.2, -3)

    loans.append({
        "ORG_ID": org_id,
        "CUSTOMER_NAME": company_name(country, used_names),
        "LOAN_TYPE": loan_type,
        "RISK_RATING": rating,
        "COUNTRY": country,
        "BRANCH": branch_name,
        # --- columns not needed for the report (removed during cleaning) ---
        "EXPOSURE_AMOUNT": max(exposure, 50_000.0),
        "CURRENCY": COUNTRIES[country]["currency"],
        "LAST_REVIEW_DATE": (SNAPSHOT_DATE - timedelta(days=random.randint(5, 400))).isoformat(),
        "SNAPSHOT_DATE": SNAPSHOT_DATE.isoformat(),
        "SOURCE_SYSTEM": random.choice(["CORE_LENDING", "CORE_LENDING", "LEASING_SYS"]),
        "ETL_LOAD_TS": datetime(2026, 10, 1, 2, random.randint(0, 59), random.randint(0, 59)).isoformat(sep=" "),
    })
    assignments.append((org_id, responsible))

loan_df = pd.DataFrame(loans)

# --------------------------------------------------------------------------------------
# 3. Customer responsible contact table – one row per customer/responsible assignment
# --------------------------------------------------------------------------------------
contact_rows = []
for org_id, emp in assignments:
    contact_rows.append({
        "ORG_ID": org_id,
        "BRANCH_ID": emp.BRANCH_ID,
        "BRANCH_NAME": emp.BRANCH_NAME,
        "CUSTOMER_RESPONSIBLE_NAME": emp.CUSTOMER_RESPONSIBLE_NAME,
        "EMAIL": emp.EMAIL,
        "PHONE": emp.PHONE,
        # --- columns not needed for the report ---
        "EMPLOYEE_ID": emp.EMPLOYEE_ID,
        "ROLE_TITLE": emp.ROLE_TITLE,
        "VALID_FROM": (SNAPSHOT_DATE - timedelta(days=random.randint(200, 1500))).isoformat(),
        "LAST_UPDATED_TS": datetime(2025, random.randint(1, 12), random.randint(1, 28), 9, 0).isoformat(sep=" "),
    })
contact_df = pd.DataFrame(contact_rows)

# --------------------------------------------------------------------------------------
# 4. Inject realistic data quality issues
# --------------------------------------------------------------------------------------
# 4a. Loan data: inconsistent country labels
loan_df["COUNTRY"] = loan_df["COUNTRY"].apply(messy_country)

# 4b. Loan data: stray whitespace in names and branch labels
idx = loan_df.sample(frac=0.05, random_state=1).index
loan_df.loc[idx, "CUSTOMER_NAME"] = "  " + loan_df.loc[idx, "CUSTOMER_NAME"] + " "
idx = loan_df.sample(frac=0.04, random_state=2).index
loan_df.loc[idx, "BRANCH"] = loan_df.loc[idx, "BRANCH"] + "  "

# 4c. Loan data: org IDs keyed in with lower case / trailing space
idx = loan_df.sample(frac=0.03, random_state=3).index
loan_df.loc[idx, "ORG_ID"] = loan_df.loc[idx, "ORG_ID"].str.lower() + " "

# 4d. Loan data: a handful of customers still awaiting a rating
idx = loan_df.sample(n=6, random_state=4).index
loan_df.loc[idx, "RISK_RATING"] = np.nan

# 4e. Loan data: duplicate rows caused by a double ETL load
dupes = loan_df.sample(n=12, random_state=5)
loan_df = pd.concat([loan_df, dupes], ignore_index=True)

# 4f. Contacts: mixed-case e-mails and org IDs
idx = contact_df.sample(frac=0.10, random_state=6).index
contact_df.loc[idx, "EMAIL"] = contact_df.loc[idx, "EMAIL"].str.title()
idx = contact_df.sample(frac=0.03, random_state=7).index
contact_df.loc[idx, "ORG_ID"] = " " + contact_df.loc[idx, "ORG_ID"].str.lower()

# 4g. Contacts: responsible reassigned -> old row still in the table (older LAST_UPDATED_TS)
reassigned = contact_df.sample(n=15, random_state=8)
old_rows = []
for _, row in reassigned.iterrows():
    other = emp_df[(emp_df.BRANCH_ID == row.BRANCH_ID) &
                   (emp_df.CUSTOMER_RESPONSIBLE_NAME != row.CUSTOMER_RESPONSIBLE_NAME)].iloc[0]
    old = row.copy()
    old["CUSTOMER_RESPONSIBLE_NAME"] = other.CUSTOMER_RESPONSIBLE_NAME
    old["EMAIL"] = other.EMAIL
    old["PHONE"] = other.PHONE
    old["EMPLOYEE_ID"] = other.EMPLOYEE_ID
    old["LAST_UPDATED_TS"] = "2023-03-15 09:00:00"
    old_rows.append(old)
contact_df = pd.concat([contact_df, pd.DataFrame(old_rows)], ignore_index=True)

# 4h. Contacts: some customers have no responsible registered yet
missing = contact_df.drop_duplicates("ORG_ID").sample(n=9, random_state=9)["ORG_ID"]
contact_df = contact_df[~contact_df["ORG_ID"].isin(missing)]

# 4i. Contacts: rows for customers that have left the portfolio (orphans)
orphans = []
for i in range(7):
    emp = emp_df.sample(1, random_state=100 + i).iloc[0]
    orphans.append({
        "ORG_ID": f"ORG{900001 + i}", "BRANCH_ID": emp.BRANCH_ID, "BRANCH_NAME": emp.BRANCH_NAME,
        "CUSTOMER_RESPONSIBLE_NAME": emp.CUSTOMER_RESPONSIBLE_NAME, "EMAIL": emp.EMAIL,
        "PHONE": emp.PHONE, "EMPLOYEE_ID": emp.EMPLOYEE_ID, "ROLE_TITLE": emp.ROLE_TITLE,
        "VALID_FROM": "2019-01-01", "LAST_UPDATED_TS": "2024-06-01 09:00:00",
    })
contact_df = pd.concat([contact_df, pd.DataFrame(orphans)], ignore_index=True)

# Shuffle so problems are not neatly grouped
loan_df = loan_df.sample(frac=1, random_state=10).reset_index(drop=True)
contact_df = contact_df.sample(frac=1, random_state=11).reset_index(drop=True)
loan_df["RISK_RATING"] = loan_df["RISK_RATING"].astype("Int64")

# --------------------------------------------------------------------------------------
# 5. Write files
# --------------------------------------------------------------------------------------
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
loan_path = OUTPUT_DIR / "loan_portfolio_risk.csv"
contact_path = OUTPUT_DIR / "customer_responsible_contact.csv"
loan_df.to_csv(loan_path, index=False, encoding="utf-8")
contact_df.to_csv(contact_path, index=False, encoding="utf-8")

print(f"Wrote {len(loan_df):>4} rows -> {loan_path.relative_to(OUTPUT_DIR.parents[1])}")
print(f"Wrote {len(contact_df):>4} rows -> {contact_path.relative_to(OUTPUT_DIR.parents[1])}")
