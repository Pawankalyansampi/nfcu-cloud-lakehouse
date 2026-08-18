DROP TABLE IF EXISTS gold_daily_volume;
CREATE TABLE gold_daily_volume AS
SELECT
    type,
    COUNT(*) AS txn_count,
    SUM(amount) AS txn_amount,
    SUM(CASE WHEN fraud_flag = 'Yes' THEN 1 ELSE 0 END) AS fraud_count
FROM payments
GROUP BY type;
