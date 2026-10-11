# Snowflake setup guide

How to create the `LOAN_DATA` database with schemas `LOAN_PORTFOLIO_RISK` and `CUSTOMER_RESPONSIBLE_CONTACT`, load the mock data, and connect the notebook.

Time needed: about 20 minutes. All SQL is in the [`sql/`](../sql) folder.

---

## 0. Before you start: naming

Snowflake stores **unquoted** names in UPPER CASE. `Loan_Portfolio_Risk` and `LOAN_PORTFOLIO_RISK` are the same object, as long as you never wrap the name in double quotes. If you create `"Loan_Portfolio_Risk"` (with quotes) you must type it with quotes and exact casing in every query forever. The scripts therefore use upper case without quotes:

| Object | Name |
|---|---|
| Database | `LOAN_DATA` |
| Schema | `LOAN_DATA.LOAN_PORTFOLIO_RISK` |
| Schema | `LOAN_DATA.CUSTOMER_RESPONSIBLE_CONTACT` |
| Table | `LOAN_PORTFOLIO_RISK.LOAN_RISK_MONITORING` |
| Table | `CUSTOMER_RESPONSIBLE_CONTACT.CUSTOMER_RESPONSIBLE` |
| Warehouse | `LOAN_WH` (X-Small, auto-suspends after 60 s) |
| Role | `LOAN_REPORTING_RO` (read-only, used by the notebook) |

## 1. Find your account identifier

In Snowsight, click your name (bottom left) → **Connect a tool to Snowflake** / **Account details**. Copy the **account identifier**, in the form `ORGNAME-ACCOUNTNAME` (e.g. `ABCDEFG-XY12345`). You need it for the `.env` file later.

## 2. Create warehouse, database, schemas and role

1. Snowsight → **Projects → Worksheets** (or **+ → SQL Worksheet**).
2. Paste the contents of [`sql/01_setup_database.sql`](../sql/01_setup_database.sql).
3. Run all (**Ctrl/Cmd + Shift + Enter**).

The final `SHOW SCHEMAS` should list `CUSTOMER_RESPONSIBLE_CONTACT`, `LOAN_PORTFOLIO_RISK`, `PUBLIC` and `INFORMATION_SCHEMA`.

> Why `SYSADMIN` and not `ACCOUNTADMIN`? Trial accounts log you in as `ACCOUNTADMIN`, but objects should be owned by `SYSADMIN`. Using `ACCOUNTADMIN` for everyday work is a common bad habit that reviewers notice.

## 3. Create the tables

New worksheet → paste [`sql/02_create_tables.sql`](../sql/02_create_tables.sql) → run all.

Note the comment on the primary key: Snowflake **does not enforce** PRIMARY KEY or UNIQUE constraints on standard tables. They document intent. That is exactly why the raw data can contain duplicates and why the notebook deduplicates and validates.

## 4. Load the CSV files

Pick **one** option.

### Option A: Snowsight wizard (easiest)

1. Snowsight → **Data → Databases → LOAN_DATA → LOAN_PORTFOLIO_RISK → Tables → LOAN_RISK_MONITORING**.
2. Click **Load Data** (top right; Snowsight occasionally moves this into a `…` menu).
3. Select `data/raw/loan_portfolio_risk.csv`, pick warehouse `LOAN_WH`.
4. File format: CSV, **header: skip first line**, field optionally enclosed by `"`, and treat empty values as NULL.
5. Repeat for `CUSTOMER_RESPONSIBLE` with `customer_responsible_contact.csv`.

### Option B: Stage + `COPY INTO` (the scripted, repeatable way)

1. Run section 1 of [`sql/03_load_data.sql`](../sql/03_load_data.sql) to create the file format and stage.
2. Upload both CSVs to the stage: **Data → Databases → LOAN_DATA → PUBLIC → Stages → RAW_FILES_STAGE → + Files**.
   (Or from a terminal with the Snowflake CLI: `snow stage copy data/raw/loan_portfolio_risk.csv @LOAN_DATA.PUBLIC.RAW_FILES_STAGE`. The `PUT` command does not work inside Snowsight worksheets.)
3. Run the rest of the script. The final query should return:

| TABLE_NAME | ROW_COUNT |
|---|---|
| LOAN_RISK_MONITORING | 812 |
| CUSTOMER_RESPONSIBLE | 813 |

Option B is the better one to mention in interviews: it is how loads are automated in practice.

## 5. Explore the data quality in SQL

Run [`sql/04_data_quality_checks.sql`](../sql/04_data_quality_checks.sql). Each query surfaces one of the problems the notebook fixes (duplicates, country spellings, reassigned responsibles, unmatched customers). Good material for screenshots in a LinkedIn post.

## 6. Connect the notebook

Snowflake is phasing out password-only sign-in, and new accounts require MFA for password logins. For a script, use **key-pair authentication**: no password, no MFA prompt each run.

### 6a. Create a key pair (run in a terminal, outside the repo folder)

```bash
mkdir -p ~/.snowflake && cd ~/.snowflake
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8 -nocrypt
openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub
```

On Windows, `openssl` is included with Git for Windows (use **Git Bash**).

### 6b. Register the public key on your user

Copy the contents of `rsa_key.pub` **without** the `-----BEGIN/END PUBLIC KEY-----` lines, then in a worksheet:

```sql
USE ROLE SECURITYADMIN;
ALTER USER <your_username> SET RSA_PUBLIC_KEY = 'MIIBIjANBgkqh...';
DESC USER <your_username>;   -- RSA_PUBLIC_KEY_FP should now have a value
```

### 6c. Fill in `.env`

```bash
cp .env.example .env
```

```
DATA_SOURCE=snowflake
SNOWFLAKE_ACCOUNT=ABCDEFG-XY12345
SNOWFLAKE_USER=YOUR_USERNAME
SNOWFLAKE_ROLE=LOAN_REPORTING_RO
SNOWFLAKE_WAREHOUSE=LOAN_WH
SNOWFLAKE_PRIVATE_KEY_PATH=C:/Users/you/.snowflake/rsa_key.p8
```

`.env` is in `.gitignore`. **Never commit it, and never put the private key inside the repo folder.**

Prefer to use your password instead? Leave `SNOWFLAKE_PRIVATE_KEY_PATH` empty and set `SNOWFLAKE_PASSWORD`. The notebook then uses `username_password_mfa`, which sends a push to your authenticator app on each connection.

### 6d. Test

Restart the Jupyter kernel and run the notebook. The extract cell should report 812 and 813 rows, the same as the CSV mode.

## Troubleshooting

| Error | Fix |
|---|---|
| `Object does not exist or not authorized` | Check role: `LOAN_REPORTING_RO` needs the grants from `01_setup_database.sql`. Tables created *after* the grants are covered by `FUTURE TABLES`; if you recreated tables, re-run the grant section. |
| `No active warehouse` | `USE WAREHOUSE LOAN_WH;` in the worksheet, or set `SNOWFLAKE_WAREHOUSE` in `.env`. |
| `JWT token is invalid` | Public key pasted with header lines or line breaks, or wrong user. Re-run `ALTER USER … SET RSA_PUBLIC_KEY`. |
| `Number of columns in file does not match` | The header row is being read as data, or quoting is off. Use the `CSV_WITH_HEADER` file format from `03_load_data.sql`. |
| `Numeric value '…' is not recognized` | Usually the same cause as above (the header row hitting a NUMBER column). |
| Credits running down | Warehouse auto-suspends after 60 s. Check **Admin → Cost Management**. |
