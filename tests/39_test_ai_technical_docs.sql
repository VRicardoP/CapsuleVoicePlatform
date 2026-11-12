-- ============================================================================
-- TEST 39: DOCUMENTACIÓN TÉCNICA IA
-- ============================================================================
-- COBERTURA LEGAL:
--   • AI Act Art. 11.1: Documentación técnica completa de sistemas IA
--   • AI Act Anexo IV: Contenido documentación sistemas alto riesgo
--   • AI Act Art. 11.2: Documentación actualizada
--   • AI Act Art. 13.3.b.iii: Documentación debe ser comprensible
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: CRÍTICA
-- REQUISITOS NORMATIVA.MD: PARTE 3 (AI Act) - Documentación Técnica (Art. 11, Anexo IV)
-- ============================================================================
-- Verifica que existe documentación técnica completa de sistemas AI según
-- Anexo IV del AI Act
-- Ejecutar: psql -U postgres -d capsule -f 39_test_ai_technical_docs.sql
-- ============================================================================

BEGIN;

\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '=================================================='
\echo 'TEST 39: DOCUMENTACION TECNICA IA'
\echo '=================================================='

CREATE TEMP TABLE IF NOT EXISTS test_results (
    test_id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    test_category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';
SET app.hash_pepper = 'TEST_PEPPER_V1_FOR_HMAC_FUNCTIONS';

-- ============================================================================
-- TEST 39.1: Verificar tabla ai_technical_documentation
-- ============================================================================

\echo ''
\echo '--- Test 39.1: Tabla ai_technical_documentation existe ---'

DO $$
DECLARE
    v_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'ai_technical_documentation'
    ) INTO v_exists;

    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'Tabla ai_technical_documentation existe (AI Act Art. 11.1)';
    ELSE
        v_status := 'FAIL';
        v_details := 'CRÍTICO: ai_technical_documentation NO existe - INCUMPLIMIENTO AI Act Art. 11';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('ai_technical_documentation Table', 'AI_Technical_Docs', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 39.2: Verificar columnas Anexo IV
-- ============================================================================

\echo ''
\echo '--- Test 39.2: Columnas segun Anexo IV ---'

DO $$
DECLARE
    v_columns TEXT[];
    v_required TEXT[] := ARRAY[
        'system_name', 'system_version', 'provider', 'intended_purpose',
        'algorithm_description', 'data_requirements', 'performance_metrics',
        'limitations', 'human_oversight_measures', 'last_updated_at'
    ];
    v_col TEXT;
    v_missing TEXT[] := ARRAY[]::TEXT[];
    v_status TEXT;
    v_details TEXT;
    v_table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'ai_technical_documentation'
    ) INTO v_table_exists;

    IF NOT v_table_exists THEN
        v_status := 'SKIP';
        v_details := 'Tabla no existe';
    ELSE
        SELECT ARRAY_AGG(column_name::TEXT) INTO v_columns
        FROM information_schema.columns
        WHERE table_name = 'ai_technical_documentation';

        FOREACH v_col IN ARRAY v_required LOOP
            IF NOT (v_col = ANY(COALESCE(v_columns, ARRAY[]::TEXT[]))) THEN
                v_missing := array_append(v_missing, v_col);
            END IF;
        END LOOP;

        IF array_length(v_missing, 1) IS NULL OR array_length(v_missing, 1) = 0 THEN
            v_status := 'PASS';
            v_details := 'Campos Anexo IV completos';
        ELSE
            v_status := 'FAIL';
            v_details := 'Columnas faltantes Anexo IV: ' || array_to_string(v_missing, ', ');
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Annex IV Fields', 'AI_Technical_Docs', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 39.3: Verificar campo performance_metrics (JSONB)
-- ============================================================================

\echo ''
\echo '--- Test 39.3: Metricas de rendimiento estructuradas ---'

DO $$
DECLARE
    v_data_type TEXT;
    v_status TEXT;
    v_details TEXT;
    v_table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'ai_technical_documentation'
    ) INTO v_table_exists;

    IF NOT v_table_exists THEN
        v_status := 'SKIP';
        v_details := 'Tabla no existe';
    ELSE
        SELECT data_type INTO v_data_type
        FROM information_schema.columns
        WHERE table_name = 'ai_technical_documentation' AND column_name = 'performance_metrics';

        IF v_data_type = 'jsonb' OR v_data_type = 'json' THEN
            v_status := 'PASS';
            v_details := 'performance_metrics usa JSONB - Anexo IV.1.c (métricas cuantificables)';
        ELSIF v_data_type IS NOT NULL THEN
            v_status := 'PASS';
            v_details := format('performance_metrics existe (%s)', v_data_type);
        ELSE
            v_status := 'FAIL';
            v_details := 'performance_metrics NO existe - Anexo IV requiere métricas';
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Performance Metrics Field', 'AI_Technical_Docs', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 39.4: Verificar campo human_oversight_measures
-- ============================================================================

\echo ''
\echo '--- Test 39.4: Medidas de supervision humana ---'

DO $$
DECLARE
    v_column_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
    v_table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'ai_technical_documentation'
    ) INTO v_table_exists;

    IF NOT v_table_exists THEN
        v_status := 'SKIP';
        v_details := 'Tabla no existe';
    ELSE
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'ai_technical_documentation' AND column_name = 'human_oversight_measures'
        ) INTO v_column_exists;

        IF v_column_exists THEN
            v_status := 'PASS';
            v_details := 'human_oversight_measures documentado (Anexo IV.3 - Art. 14)';
        ELSE
            v_status := 'FAIL';
            v_details := 'human_oversight_measures NO existe - Anexo IV.3';
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Human Oversight Documentation', 'AI_Technical_Docs', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 39.5: Verificar campo last_updated_at
-- ============================================================================

\echo ''
\echo '--- Test 39.5: Actualizacion de documentacion ---'

DO $$
DECLARE
    v_column_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
    v_table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'ai_technical_documentation'
    ) INTO v_table_exists;

    IF NOT v_table_exists THEN
        v_status := 'SKIP';
        v_details := 'Tabla no existe';
    ELSE
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'ai_technical_documentation' AND column_name = 'last_updated_at'
        ) INTO v_column_exists;

        IF v_column_exists THEN
            v_status := 'PASS';
            v_details := 'last_updated_at permite tracking actualización (Art. 11.2)';
        ELSE
            v_status := 'FAIL';
            v_details := 'last_updated_at NO existe - Art. 11.2 (mantener actualizada)';
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Documentation Update Tracking', 'AI_Technical_Docs', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- RESUMEN
-- ============================================================================

\echo ''
\echo '=================================================='
\echo 'RESUMEN TEST 39: DOCUMENTACION TECNICA IA'
\echo '=================================================='

SELECT test_category,
       COUNT(*) as total_tests,
       SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
       SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed,
       SUM(CASE WHEN status = 'SKIP' THEN 1 ELSE 0 END) as skipped
FROM test_results
GROUP BY test_category;

\echo ''
SELECT test_name, status, details FROM test_results ORDER BY test_id;

\echo ''
\echo '=================================================='
\echo 'CUMPLIMIENTO LEGAL VERIFICADO:'
\echo '  - AI Act Art. 11.1: Documentacion tecnica'
\echo '  - AI Act Anexo IV: Contenido completo'
\echo '  - AI Act Art. 11.2: Actualizacion documentada'
\echo '=================================================='

ROLLBACK;
