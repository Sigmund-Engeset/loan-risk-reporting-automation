/* =====================================================================================
   02_create_tables.sql
   Creates the two source tables. Column types mirror the mock CSV files in data/raw/.
   ===================================================================================== */

USE ROLE SYSADMIN;
USE WAREHOUSE LOAN_WH;
USE DATABASE LOAN_DATA;

-- -------------------------------------------------------------------------------------
-- Loan portfolio risk monitoring (one row per customer; ORG_ID is the business key).
-- NB: the raw feed contains duplicate rows from a double ETL load, which is why
-- the PRIMARY KEY below is informational only. Snowflake does not enforce PK/UNIQUE
-- constraints on standard tables; deduplication happens in the notebook.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE LOAN_PORTFOLIO_RISK.LOAN_RISK_MONITORING (
    ORG_ID              VARCHAR(20)     NOT NULL  COMMENT 'Internal organisation (customer) ID',
    CUSTOMER_NAME       VARCHAR(200)              COMMENT 'Legal name of the customer',
    LOAN_TYPE           VARCHAR(50)               COMMENT 'Main credit product',
    RISK_RATING         NUMBER(2,0)               COMMENT 'Internal risk rating 1 (low) to 10 (high). NULL = pending',
    COUNTRY             VARCHAR(30)               COMMENT 'Booking country (raw, not standardised)',
    BRANCH              VARCHAR(100)              COMMENT 'Booking branch name',
    EXPOSURE_AMOUNT     NUMBER(18,2)              COMMENT 'Total exposure in local currency',
    CURRENCY            VARCHAR(3)                COMMENT 'ISO 4217 currency code',
    LAST_REVIEW_DATE    DATE                      COMMENT 'Date of last credit review',
    SNAPSHOT_DATE       DATE                      COMMENT 'Month-end snapshot date',
    SOURCE_SYSTEM       VARCHAR(30)               COMMENT 'Upstream system',
    ETL_LOAD_TS         TIMESTAMP_NTZ             COMMENT 'Load timestamp',
    CONSTRAINT PK_LOAN_RISK_MONITORING PRIMARY KEY (ORG_ID)
)
COMMENT = 'Monthly loan portfolio risk monitoring snapshot (mock data)';

-- -------------------------------------------------------------------------------------
-- Customer responsible contact details. ORG_ID links to LOAN_RISK_MONITORING.ORG_ID.
-- A customer can appear more than once when the responsible has been reassigned;
-- the latest LAST_UPDATED_TS is the current one.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE TABLE CUSTOMER_RESPONSIBLE_CONTACT.CUSTOMER_RESPONSIBLE (
    ORG_ID                     VARCHAR(20)   NOT NULL COMMENT 'Internal organisation (customer) ID',
    BRANCH_ID                  VARCHAR(10)            COMMENT 'Branch code, e.g. NO01',
    BRANCH_NAME                VARCHAR(100)           COMMENT 'Branch name',
    CUSTOMER_RESPONSIBLE_NAME  VARCHAR(150)           COMMENT 'Relationship manager full name',
    EMAIL                      VARCHAR(200)           COMMENT 'Relationship manager e-mail',
    PHONE                      VARCHAR(30)            COMMENT 'Relationship manager phone (raw format)',
    EMPLOYEE_ID                VARCHAR(10)            COMMENT 'HR employee ID',
    ROLE_TITLE                 VARCHAR(60)            COMMENT 'Job title',
    VALID_FROM                 DATE                   COMMENT 'Assignment valid from',
    LAST_UPDATED_TS            TIMESTAMP_NTZ          COMMENT 'Last update of the assignment'
)
COMMENT = 'Customer responsible assignments and contact details (mock data)';

SHOW TABLES IN DATABASE LOAN_DATA;
