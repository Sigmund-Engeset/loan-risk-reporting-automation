/* =====================================================================================
   01_setup_database.sql
   Creates the warehouse, database, schemas and a least-privilege role for the
   Loan Risk Reporting Automation project.

   Run in a Snowsight SQL worksheet. Run the whole script top to bottom (Ctrl/Cmd+Shift+Enter).
   Unquoted identifiers are stored in UPPER CASE in Snowflake, so
   Loan_Portfolio_Risk becomes LOAN_PORTFOLIO_RISK. Keep it that way: quoted, mixed-case
   names force you to quote them in every query forever after.
   ===================================================================================== */

-- 1. Compute: a small warehouse that suspends itself after 60s idle (keeps trial credits low)
USE ROLE SYSADMIN;

CREATE WAREHOUSE IF NOT EXISTS LOAN_WH
    WAREHOUSE_SIZE      = 'XSMALL'
    AUTO_SUSPEND        = 60
    AUTO_RESUME         = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Warehouse for the loan risk reporting portfolio project';

-- 2. Storage: database and the two source schemas
CREATE DATABASE IF NOT EXISTS LOAN_DATA
    COMMENT = 'Mock loan portfolio data for the loan risk reporting portfolio project';

CREATE SCHEMA IF NOT EXISTS LOAN_DATA.LOAN_PORTFOLIO_RISK
    COMMENT = 'Monthly loan portfolio risk monitoring snapshot';

CREATE SCHEMA IF NOT EXISTS LOAN_DATA.CUSTOMER_RESPONSIBLE_CONTACT
    COMMENT = 'Customer responsible (relationship manager) assignments and contact details';

-- 3. Access: a dedicated read-only role for the reporting notebook
USE ROLE SECURITYADMIN;

CREATE ROLE IF NOT EXISTS LOAN_REPORTING_RO
    COMMENT = 'Read-only access to LOAN_DATA for the reporting notebook';

GRANT USAGE ON WAREHOUSE LOAN_WH                                 TO ROLE LOAN_REPORTING_RO;
GRANT USAGE ON DATABASE  LOAN_DATA                               TO ROLE LOAN_REPORTING_RO;
GRANT USAGE ON ALL SCHEMAS IN DATABASE LOAN_DATA                 TO ROLE LOAN_REPORTING_RO;
GRANT SELECT ON ALL TABLES    IN DATABASE LOAN_DATA              TO ROLE LOAN_REPORTING_RO;
GRANT SELECT ON FUTURE TABLES IN DATABASE LOAN_DATA              TO ROLE LOAN_REPORTING_RO;

-- Let your own user use the new role
SET MY_USER = CURRENT_USER();
GRANT ROLE LOAN_REPORTING_RO TO USER IDENTIFIER($MY_USER);

-- Roll the new role up under SYSADMIN (Snowflake best practice: no orphaned roles)
GRANT ROLE LOAN_REPORTING_RO TO ROLE SYSADMIN;

-- 4. Check
USE ROLE SYSADMIN;
SHOW SCHEMAS IN DATABASE LOAN_DATA;
