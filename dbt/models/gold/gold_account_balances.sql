DROP TABLE IF EXISTS gold_account_balances;
CREATE TABLE gold_account_balances AS
SELECT
    account_type,
    COUNT(*) AS account_count,
    SUM(balance) AS total_balance
FROM accounts
GROUP BY account_type;
