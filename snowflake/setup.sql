-- Run in a Snowflake 30-day trial worksheet (optional second warehouse).
-- Then add SNOWFLAKE_ACCOUNT / USER / PASSWORD to .env and re-run python run_local.py.

CREATE WAREHOUSE IF NOT EXISTS NFCU_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;

CREATE DATABASE IF NOT EXISTS NFCU;
CREATE SCHEMA IF NOT EXISTS NFCU.GOLD;

USE WAREHOUSE NFCU_WH;
USE DATABASE NFCU;
USE SCHEMA GOLD;

-- Tables are created/overwritten by app/snowflake_wh.py (write_pandas).
-- After the Python load, check:

SELECT * FROM GOLD_DAILY_VOLUME;
SELECT * FROM GOLD_FRAUD_SUMMARY;
SELECT * FROM GOLD_ACCOUNT_BALANCES;
