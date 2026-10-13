-- ============================================================================
-- TEST 42: EXACTITUD, ROBUSTEZ Y CIBERSEGURIDAD IA
-- ============================================================================
-- COBERTURA LEGAL:
--   • AI Act Art. 15.1: Exactitud apropiada de sistemas IA
--   • AI Act Art. 15.3: Robustez técnica contra manipulación
--   • AI Act Art. 15.4: Ciberseguridad de sistemas IA
--   • AI Act Art. 15.5: Mecanismos de respaldo para fallos
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: ALTA
-- REQUISITOS NORMATIVA.MD: PARTE 3 (AI Act) - Exactitud y Robustez (Art. 15)
-- ============================================================================

BEGIN;

\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '=================================================='
\echo 'TEST 42: EXACTITUD Y ROBUSTEZ IA'
\echo '=================================================='

CREATE TEMP TABLE IF NOT EXISTS test_results (
    test_id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    test_category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- TEST 42.1: Tabla ai_accuracy_metrics
DO $$
DECLARE v_exists BOOLEAN; v_status TEXT; v_details TEXT;
BEGIN
    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ai_accuracy_metrics') INTO v_exists;
    
    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'ai_accuracy_metrics existe (AI Act Art. 15.1)';
    ELSE
        v_status := 'FAIL';
        v_details := 'CRÍTICO: ai_accuracy_metrics NO existe - Art. 15.1';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Accuracy Metrics Table', 'AI_Accuracy_Robustness', v_status, v_details);
    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- TEST 42.2: Columnas de métricas de exactitud
DO $$
DECLARE
    v_columns TEXT[];
    v_required TEXT[] := ARRAY['accuracy', 'precision_score', 'recall', 'f1_score'];
    v_missing TEXT[] := ARRAY[]::TEXT[];
    v_col TEXT; -- Missing variable declaration
    v_table_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ai_accuracy_metrics') INTO v_table_exists;
    
    IF NOT v_table_exists THEN
        v_status := 'SKIP';
        v_details := 'Tabla no existe';
    ELSE
        SELECT ARRAY_AGG(column_name::TEXT) INTO v_columns
        FROM information_schema.columns WHERE table_name = 'ai_accuracy_metrics';

        FOREACH v_col IN ARRAY v_required LOOP
            IF NOT (v_col = ANY(COALESCE(v_columns, ARRAY[]::TEXT[]))) THEN
                v_missing := array_append(v_missing, v_col);
            END IF;
        END LOOP;

        IF array_length(v_missing, 1) IS NULL THEN
            v_status := 'PASS';
            v_details := 'Métricas de exactitud completas (accuracy, precision, recall, F1)';
        ELSE
            v_status := 'FAIL';
            v_details := 'Métricas faltantes: ' || array_to_string(v_missing, ', ');
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Accuracy Metrics Columns', 'AI_Accuracy_Robustness', v_status, v_details);
    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- TEST 42.3: Tabla ai_security_assessment
DO $$
DECLARE v_exists BOOLEAN; v_status TEXT; v_details TEXT;
BEGIN
    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ai_security_assessment') INTO v_exists;
    
    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'ai_security_assessment existe (AI Act Art. 15.4 - Ciberseguridad)';
    ELSE
        v_status := 'FAIL';
        v_details := 'ai_security_assessment NO existe - Art. 15.4 (ciberseguridad)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Security Assessment Table', 'AI_Accuracy_Robustness', v_status, v_details);
    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

\echo ''
\echo '=================================================='
\echo 'RESUMEN TEST 42'
\echo '=================================================='

SELECT test_category, COUNT(*) as total,
       SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
       SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed
FROM test_results GROUP BY test_category;

SELECT test_name, status, details FROM test_results ORDER BY test_id;

ROLLBACK;
