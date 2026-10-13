-- ============================================================================
-- TEST 43: SISTEMA DE GESTIÓN DE CALIDAD IA
-- ============================================================================
-- COBERTURA LEGAL:
--   • AI Act Art. 17: Sistema de gestión de calidad
--   • AI Act Art. 17.1.a-h: Elementos del sistema de calidad
-- 
-- NIVEL DE COMPLIANCE: MEDIO
-- CRITICIDAD: ALTA
-- REQUISITOS NORMATIVA.MD: PARTE 3 (AI Act) - Sistema de Gestión de Calidad (Art. 17)
-- ====================================================================================

BEGIN;

\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '=================================================='
\echo 'TEST 43: SISTEMA DE GESTION DE CALIDAD IA'
\echo '=================================================='

CREATE TEMP TABLE IF NOT EXISTS test_results (
    test_id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    test_category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- TEST 43.1: Tabla ai_quality_management
DO $$
DECLARE v_exists BOOLEAN; v_status TEXT; v_details TEXT;
BEGIN
    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ai_quality_management') INTO v_exists;
    
    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'ai_quality_management existe (AI Act Art. 17)';
    ELSE
        v_status := 'FAIL';
        v_details := 'ai_quality_management NO existe - Art. 17';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Quality Management Table', 'AI_Quality_Management', v_status, v_details);
    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- TEST 43.2: Campo next_review_date
DO $$
DECLARE v_exists BOOLEAN; v_status TEXT; v_details TEXT; v_table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ai_quality_management') INTO v_table_exists;
    
    IF NOT v_table_exists THEN
        v_status := 'SKIP';
        v_details := 'Tabla no existe';
    ELSE
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'ai_quality_management' AND column_name = 'next_review_date'
        ) INTO v_exists;

        IF v_exists THEN
            v_status := 'PASS';
            v_details := 'next_review_date permite revisiones periódicas (Art. 17.1)';
        ELSE
            v_status := 'FAIL';
            v_details := 'next_review_date NO existe - sin planificación revisiones';
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Periodic Review Tracking', 'AI_Quality_Management', v_status, v_details);
    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

\echo ''
\echo '=================================================='
\echo 'RESUMEN TEST 43'
\echo '=================================================='

SELECT test_category, COUNT(*) as total,
       SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
       SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed
FROM test_results GROUP BY test_category;

SELECT test_name, status, details FROM test_results ORDER BY test_id;

ROLLBACK;
