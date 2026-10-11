/* =====================================================================================
   03_load_data.sql
   Loads the two CSV files from data/raw/ into the tables via an internal stage.

   Step A  Create the file format and the stage (this script, section 1).
   Step B  Upload the CSV files to the stage. Two options:
           - Snowsight UI: Data > Databases > LOAN_DATA > PUBLIC > Stages > RAW_FILES_STAGE
             > "+ Files" and drop both CSVs in.
           - Command line (Snowflake CLI or SnowSQL), see section 2.
           Note: the PUT command does NOT run inside a Snowsight worksheet.
   Step C  Run sections 3 and 4 of this script.

   (Alternative to all of this: Snowsight's "Load data into a table" wizard. See
   docs/snowflake_setup_guide.md.)
   ===================================================================================== */

USE ROLE SYSADMIN;
USE WAREHOUSE LOAN_WH;
USE DATABASE LOAN_DATA;

-- -------------------------------------------------------------------------------------
-- 1. File format + internal stage
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE FILE FORMAT LOAN_DATA.PUBLIC.CSV_WITH_HEADER
    TYPE                         = CSV
    FIELD_DELIMITER              = ','
    SKIP_HEADER                  = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    TRIM_SPACE                   = FALSE   -- keep raw whitespace; cleaning is done in the notebook
    NULL_IF                      = ('', 'NULL', 'nan')
    EMPTY_FIELD_AS_NULL          = TRUE
    ENCODING                     = 'UTF8';

CREATE STAGE IF NOT EXISTS LOAN_DATA.PUBLIC.RAW_FILES_STAGE
    FILE_FORMAT = LOAN_DATA.PUBLIC.CSV_WITH_HEADER
    DIRECTORY   = (ENABLE = TRUE)
    COMMENT     = 'Landing area for the raw mock CSV files';

-- -------------------------------------------------------------------------------------
-- 2. Upload (command line only, skip if you used the Snowsight UI)
--    Run from the repository root:
--
--    snow stage copy data/raw/loan_portfolio_risk.csv          @LOAN_DATA.PUBLIC.RAW_FILES_STAGE
--    snow stage copy data/raw/customer_responsible_contact.csv @LOAN_DATA.PUBLIC.RAW_FILES_STAGE
--
--    or with SnowSQL:
--    PUT file://data/raw/*.csv @LOAN_DATA.PUBLIC.RAW_FILES_STAGE AUTO_COMPRESS=TRUE;
-- -------------------------------------------------------------------------------------
LIST @LOAN_DATA.PUBLIC.RAW_FILES_STAGE;   -- both files should appear here before continuing

-- -------------------------------------------------------------------------------------
-- 3. Copy into the tables
-- -------------------------------------------------------------------------------------
COPY INTO LOAN_PORTFOLIO_RISK.LOAN_RISK_MONITORING
FROM @LOAN_DATA.PUBLIC.RAW_FILES_STAGE
PATTERN = '.*loan_portfolio_risk\\.csv.*'
ON_ERROR = 'ABORT_STATEMENT';

COPY INTO CUSTOMER_RESPONSIBLE_CONTACT.CUSTOMER_RESPONSIBLE
FROM @LOAN_DATA.PUBLIC.RAW_FILES_STAGE
PATTERN = '.*customer_responsible_contact\\.csv.*'
ON_ERROR = 'ABORT_STATEMENT';

-- -------------------------------------------------------------------------------------
-- 4. Reconcile row counts against the source files (expected: 812 and 813)
-- -------------------------------------------------------------------------------------
SELECT 'LOAN_RISK_MONITORING' AS TABLE_NAME, COUNT(*) AS ROW_COUNT
FROM LOAN_PORTFOLIO_RISK.LOAN_RISK_MONITORING
UNION ALL
SELECT 'CUSTOMER_RESPONSIBLE', COUNT(*)
FROM CUSTOMER_RESPONSIBLE_CONTACT.CUSTOMER_RESPONSIBLE;
