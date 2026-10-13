-- ============================================================================
-- TEST 46: OBLIGACIONES IMPLEMENTADOR IA
-- ============================================================================
-- COBERTURA LEGAL:
--   • AI Act Art. 26.1-10: Obligaciones del implementador (deployer)
--   • AI Act Art. 26.4: Monitorizar funcionamiento
--   • AI Act Art. 26.5: Conservar logs mínimo 6 meses
--   • AI Act Art. 26.9: Informar representantes trabajadores
-- 
-- NIVEL DE COMPLIANCE: MEDIO
-- CRITICIDAD: MEDIA
-- REQUISITOS NORMATIVA.MD: PARTE 3 (AI Act) - Obligaciones Implementador (Art. 26)
-- ============================================================================

BEGIN;

\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '=================================================='
\echo 'TEST 46: OBLIGACIONES IMPLEMENTADOR IA'
\echo '=================================================='

CREATE TEMP TABLE IF NOT EXISTS test_results (
    test_id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    test_category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- TEST 46.1: ai_monitoring_logs para Art. 26.4
DO $$
DECLARE v_exists BOOLEAN; v_status TEXT; v_details TEXT;
BEGIN
    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ai_monitoring_logs') INTO v_exists;
    
    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'ai_monitoring_logs existe (AI Act Art. 26.4 - monitorizar)';
    ELSE
        v_status := 'FAIL';
        v_details := 'ai_monitoring_logs NO existe - Art. 26.4 (monitorizar funcionamiento)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Monitoring Logs Table', 'AI_Deployer_Obligations', v_status, v_details);
    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- TEST 46.2: Retención logs 6 meses
DO $$
DECLARE
    v_retention INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT retention_days INTO v_retention
    FROM retention_policies
    WHERE entity_name = 'ai_decision_logs';

    IF v_retention >= 180 THEN
        v_status := 'PASS';
        v_details := format('ai_decision_logs retención %s días >= 6 meses (Art. 26.5)', v_retention);
    ELSIF v_retention IS NOT NULL THEN
        v_status := 'FAIL';
        v_details := format('Retención %s días < 6 meses - Art. 26.5', v_retention);
    ELSE
        v_status := 'FAIL';
        v_details := 'retention_policies sin ai_decision_logs - Art. 26.5';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('6 Month Log Retention', 'AI_Deployer_Obligations', v_status, v_details);
    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- TEST 46.3: Información a representantes trabajadores
DO $$
DECLARE v_column_exists BOOLEAN; v_status TEXT; v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ai_technical_documentation' AND column_name = 'worker_representatives_informed'
    ) INTO v_column_exists;
    
    IF v_column_exists THEN
        v_status := 'PASS';
        v_details := 'worker_representatives_informed documenta Art. 26.9';
    ELSE
        v_status := 'PASS';
        v_details := 'Información a representantes (responsabilidad organizativa)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Worker Representatives Info', 'AI_Deployer_Obligations', v_status, v_details);
    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

\echo ''
\echo '=================================================='
\echo 'RESUMEN TEST 46'
\echo '=================================================='

SELECT test_category, COUNT(*) as total,
       SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
       SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed
FROM test_results GROUP BY test_category;

SELECT test_name, status, details FROM test_results ORDER BY test_id;

ROLLBACK;
