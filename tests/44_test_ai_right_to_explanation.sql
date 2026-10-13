-- ============================================================================
-- TEST 44: DERECHO A EXPLICACIÓN IA
-- ============================================================================
-- COBERTURA LEGAL:
--   • AI Act Art. 86.1: Derecho a obtener explicación de decisiones IA
--   • RGPD Art. 22.3: Garantías para decisiones automatizadas
-- 
-- NIVEL DE COMPLIANCE: MEDIO
-- CRITICIDAD: ALTA
-- REQUISITOS NORMATIVA.MD: PARTE 3 (AI Act) - Derecho a Explicación (Art. 86)
-- ============================================================================

BEGIN;

\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '==========================================  ======'
\echo 'TEST 44: DERECHO A EXPLICACION IA'
\echo '=================================================='

CREATE TEMP TABLE IF NOT EXISTS test_results (
    test_id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    test_category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- TEST 44.1: Tabla ai_explanation_log
DO $$
DECLARE v_exists BOOLEAN; v_status TEXT; v_details TEXT;
BEGIN
    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ai_explanation_log') INTO v_exists;
    
    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'ai_explanation_log existe (AI Act Art. 86.1)';
    ELSE
        v_status := 'FAIL';
        v_details := 'ai_explanation_log NO existe - Art. 86.1 (derecho explicación)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Explanation Log Table', 'AI_Right_to_Explanation', v_status, v_details);
    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- TEST 44.2: FK a ai_decision_logs
DO $$
DECLARE v_fk_exists BOOLEAN; v_status TEXT; v_details TEXT; v_table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ai_explanation_log') INTO v_table_exists;
    
    IF NOT v_table_exists THEN
        v_status := 'SKIP';
        v_details := 'Tabla no existe';
    ELSE
        SELECT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE table_name = 'ai_explanation_log' AND constraint_type = 'FOREIGN KEY'
        ) INTO v_fk_exists;

        IF v_fk_exists THEN
            v_status := 'PASS';
            v_details := 'FK a ai_decision_logs vincula explicaciones a decisiones';
        ELSE
            v_status := 'FAIL';
            v_details := 'FK faltante - no se vinculan explicaciones a decisiones';
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Explanation-Decision Link', 'AI_Right_to_Explanation', v_status, v_details);
    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

\echo ''
\echo '=================================================='
\echo 'RESUMEN TEST 44'
\echo '=================================================='

SELECT test_category, COUNT(*) as total,
       SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
       SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed
FROM test_results GROUP BY test_category;

SELECT test_name, status, details FROM test_results ORDER BY test_id;

ROLLBACK;
