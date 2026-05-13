-- Rename strategy IDs to institutional naming convention (EQ_<TYPE>_001)
UPDATE signals
SET strategy_id = CASE strategy_id
    WHEN 'trend_following_v1' THEN 'EQ_TREND_001'
    WHEN 'mean_reversion_v1'  THEN 'EQ_REVERSION_001'
    WHEN 'momentum_v1'        THEN 'EQ_MOMENTUM_001'
    ELSE strategy_id
END
WHERE strategy_id IN ('trend_following_v1', 'mean_reversion_v1', 'momentum_v1');

UPDATE orders
SET strategy_id = CASE strategy_id
    WHEN 'trend_following_v1' THEN 'EQ_TREND_001'
    WHEN 'mean_reversion_v1'  THEN 'EQ_REVERSION_001'
    WHEN 'momentum_v1'        THEN 'EQ_MOMENTUM_001'
    ELSE strategy_id
END
WHERE strategy_id IN ('trend_following_v1', 'mean_reversion_v1', 'momentum_v1');

UPDATE trade_outcomes
SET strategy_id = CASE strategy_id
    WHEN 'trend_following_v1' THEN 'EQ_TREND_001'
    WHEN 'mean_reversion_v1'  THEN 'EQ_REVERSION_001'
    WHEN 'momentum_v1'        THEN 'EQ_MOMENTUM_001'
    ELSE strategy_id
END
WHERE strategy_id IN ('trend_following_v1', 'mean_reversion_v1', 'momentum_v1');
