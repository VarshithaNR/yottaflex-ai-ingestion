-- Current target entity counts
SELECT 'customers' AS entity, COUNT(*) AS rows FROM customers
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_events', COUNT(*) FROM order_events;

-- Referential integrity check (expected: zero rows)
SELECT o.order_id, o.customer_id
FROM orders AS o
LEFT JOIN customers AS c ON c.customer_id = o.customer_id
WHERE c.customer_id IS NULL;

-- Event history counts per current order
SELECT order_id, COUNT(*) AS event_count, MAX(updated_at) AS latest_event_at
FROM order_events
GROUP BY order_id
ORDER BY order_id;

-- Current order totals by currency
SELECT currency, SUM(CAST(amount AS NUMERIC)) AS current_amount
FROM orders
GROUP BY currency;
