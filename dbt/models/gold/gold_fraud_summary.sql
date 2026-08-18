DROP TABLE IF EXISTS gold_fraud_summary;
CREATE TABLE gold_fraud_summary AS
SELECT
    type,
    COUNT(*) AS alert_count,
    SUM(amount) AS alert_amount
FROM fraud_alerts
GROUP BY type;
