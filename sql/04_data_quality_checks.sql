/* =====================================================================================
   04_data_quality_checks.sql
   Profiling queries run against the raw tables before building the report.
   Each query answers one question that determines a cleaning rule in the notebook.
   ===================================================================================== */

USE ROLE LOAN_REPORTING_RO;
USE WAREHOUSE LOAN_WH;
USE DATABASE LOAN_DATA;

-- Q1. Is ORG_ID really unique in the risk table? (It is not: duplicate ETL loads)
SELECT UPPER(TRIM(ORG_ID)) AS ORG_ID_CLEAN, COUNT(*) AS N_ROWS
FROM LOAN_PORTFOLIO_RISK.LOAN_RISK_MONITORING
GROUP BY 1
HAVING COUNT(*) > 1
ORDER BY N_ROWS DESC;

-- Q2. How many ways is "country" spelled?
SELECT COUNTRY, COUNT(*) AS N_ROWS
FROM LOAN_PORTFOLIO_RISK.LOAN_RISK_MONITORING
GROUP BY 1
ORDER BY 1;

-- Q3. Which customers are still waiting for a risk rating?
SELECT ORG_ID, CUSTOMER_NAME, COUNTRY, BRANCH
FROM LOAN_PORTFOLIO_RISK.LOAN_RISK_MONITORING
WHERE RISK_RATING IS NULL;

-- Q4. Customers with more than one responsible registered (reassignments)
SELECT UPPER(TRIM(ORG_ID)) AS ORG_ID_CLEAN,
       COUNT(*)            AS N_RESPONSIBLES,
       MAX(LAST_UPDATED_TS) AS LATEST_UPDATE
FROM CUSTOMER_RESPONSIBLE_CONTACT.CUSTOMER_RESPONSIBLE
GROUP BY 1
HAVING COUNT(*) > 1;

-- Q5. Risk customers with no responsible (cannot be routed to anyone)
SELECT DISTINCT UPPER(TRIM(L.ORG_ID)) AS ORG_ID_CLEAN, L.CUSTOMER_NAME
FROM LOAN_PORTFOLIO_RISK.LOAN_RISK_MONITORING L
LEFT JOIN CUSTOMER_RESPONSIBLE_CONTACT.CUSTOMER_RESPONSIBLE C
       ON UPPER(TRIM(L.ORG_ID)) = UPPER(TRIM(C.ORG_ID))
WHERE C.ORG_ID IS NULL;

-- Q6. Contact rows for customers no longer in the portfolio (orphans)
SELECT C.*
FROM CUSTOMER_RESPONSIBLE_CONTACT.CUSTOMER_RESPONSIBLE C
LEFT JOIN LOAN_PORTFOLIO_RISK.LOAN_RISK_MONITORING L
       ON UPPER(TRIM(L.ORG_ID)) = UPPER(TRIM(C.ORG_ID))
WHERE L.ORG_ID IS NULL;
