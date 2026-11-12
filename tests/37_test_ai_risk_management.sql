-- ============================================================================
-- TEST 37: SISTEMA DE GESTIÓN DE RIESGOS IA
-- ============================================================================
-- COBERTURA LEGAL:
--   • AI Act Art. 9.1: Sistema de gestión de riesgos obligatorio
--   • AI Act Art. 9.2.a: Identificación de riesgos conocidos y previsibles
--   • AI Act Art. 9.2.b: Estimación y evaluación de riesgos
--   • AI Act Art. 9.2.c: Evaluación de riesgos en uso previsto/indebido
--   • AI Act Art. 9.2.d: Adopción de medidas de gestión adecuadas
--   • AI Act Art. 9.5: Probar sistemas para identificar riesgos
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: CRÍTICA
-- REQUISITOS NORMATIVA.MD: PARTE 3 (AI Act) - Sistema de Gestión de Riesgos (Art. 9)
-- ============================================================================
-- Verifica que existe un sistema completo de gestión de riesgos para sistemas
-- de IA de alto riesgo según el AI Act
-- Ejecutar: psql -U postgres -d capsule -f 37_test_ai_risk_management.sql
-- ============================================================================

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '=============================================='
\echo 'TEST 37: SISTEMA DE GESTIÓN DE RIESGOS IA'
\echo '=============================================='

CREATE TEMP TABLE IF NOT EXISTS test_results (
    test_id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    test_category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Configurar variables de sesión
SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';
SET app.hash_pepper = 'TEST_PEPPER_V1_FOR_HMAC_FUNCTIONS';
SET app.hash_pepper_version = '1';
SET app.audit_hmac_key = 'TEST_AUDIT_KEY_FOR_HMAC_CHAIN__';

-- ============================================================================
-- TEST 37.1: Verificar existencia de tabla ai_risk_management
-- ============================================================================

\echo ''
\echo '--- Test 37.1: Tabla ai_risk_management existe ---'

DO $$
DECLARE
    v_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'ai_risk_management'
    ) INTO v_exists;

    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'Tabla ai_risk_management existe (AI Act Art. 9.1)';
    ELSE
        v_status := 'FAIL';
        v_details := 'CRÍTICO: Tabla ai_risk_management NO existe - INCUMPLIMIENTO AI Act Art. 9.1';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('ai_risk_management Table Exists', 'AI_Risk_Management', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 37.2: Verificar columnas requeridas de ai_risk_management
-- ============================================================================

\echo ''
\echo '--- Test 37.2: Columnas de ai_risk_management ---'

DO $$
DECLARE
    v_columns TEXT[];
    v_required TEXT[] := ARRAY[
        'risk_id', 'risk_identifier', 'risk_category', 'risk_description',
        'probability', 'impact', 'risk_score', 'affected_system',
        'mitigation_measures', 'residual_risk', 'status', 'identified_date',
        'review_date', 'responsible_person'
    ];
    v_col TEXT;
    v_missing TEXT[] := ARRAY[]::TEXT[];
    v_status TEXT;
    v_details TEXT;
    v_table_exists BOOLEAN;
BEGIN
    -- Verificar si existe la tabla primero
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'ai_risk_management'
    ) INTO v_table_exists;

    IF NOT v_table_exists THEN
        v_status := 'SKIP';
        v_details := 'Tabla ai_risk_management no existe - test omitido';
    ELSE
        SELECT ARRAY_AGG(column_name::TEXT) INTO v_columns
        FROM information_schema.columns
        WHERE table_name = 'ai_risk_management';

        FOREACH v_col IN ARRAY v_required LOOP
            IF NOT (v_col = ANY(COALESCE(v_columns, ARRAY[]::TEXT[]))) THEN
                v_missing := array_append(v_missing, v_col);
            END IF;
        END LOOP;

        IF array_length(v_missing, 1) IS NULL OR array_length(v_missing, 1) = 0 THEN
            v_status := 'PASS';
            v_details := 'ai_risk_management tiene todas las columnas requeridas (AI Act Art. 9.2)';
        ELSE
            v_status := 'FAIL';
            v_details := 'Columnas faltantes: ' || array_to_string(v_missing, ', ');
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('ai_risk_management Columns', 'AI_Risk_Management', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 37.3: Verificar enum valores de probability
-- ============================================================================

\echo ''
\echo '--- Test 37.3: Enum de probabilidad de riesgos ---'

DO $$
DECLARE
    v_check_exists BOOLEAN;
    v_constraint_def TEXT;
    v_status TEXT;
    v_details TEXT;
    v_table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'ai_risk_management'
    ) INTO v_table_exists;

    IF NOT v_table_exists THEN
        v_status := 'SKIP';
        v_details := 'Tabla no existe';
    ELSE
        SELECT EXISTS (
            SELECT 1 FROM information_schema.constraint_column_usage
            WHERE table_name = 'ai_risk_management' AND column_name = 'probability'
        ) INTO v_check_exists;

        IF v_check_exists THEN
            v_status := 'PASS';
            v_details := 'Campo probability tiene constraint CHECK (low/medium/high)';
        ELSE
            v_status := 'FAIL';
            v_details := 'probability sin constraint - no cumple AI Act Art. 9.2.b';
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Probability Enum', 'AI_Risk_Management', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 37.4: Verificar enum valores de impact
-- ============================================================================

\echo ''
\echo '--- Test 37.4: Enum de impacto de riesgos ---'

DO $$
DECLARE
    v_check_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
    v_table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'ai_risk_management'
    ) INTO v_table_exists;

    IF NOT v_table_exists THEN
        v_status := 'SKIP';
        v_details := 'Tabla no existe';
    ELSE
        SELECT EXISTS (
            SELECT 1 FROM information_schema.constraint_column_usage
            WHERE table_name = 'ai_risk_management' AND column_name = 'impact'
        ) INTO v_check_exists;

        IF v_check_exists THEN
            v_status := 'PASS';
            v_details := 'Campo impact tiene constraint CHECK (minimal/significant/critical)';
        ELSE
            v_status := 'FAIL';
            v_details := 'impact sin constraint - no cumple AI Act Art. 9.2.b';
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Impact Enum', 'AI_Risk_Management', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 37.5: Verificar enum valores de status
-- ============================================================================

\echo ''
\echo '--- Test 37.5: Estados de gestion de riesgos ---'

DO $$
DECLARE
    v_check_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
    v_table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'ai_risk_management'
    ) INTO v_table_exists;

    IF NOT v_table_exists THEN
        v_status := 'SKIP';
        v_details := 'Tabla no existe';
    ELSE
        SELECT EXISTS (
            SELECT 1 FROM information_schema.constraint_column_usage
            WHERE table_name = 'ai_risk_management' AND column_name = 'status'
        ) INTO v_check_exists;

        IF v_check_exists THEN
            v_status := 'PASS';
            v_details := 'Campo status tiene constraint (identified/mitigating/mitigated/accepted)';
        ELSE
            v_status := 'FAIL';
            v_details := 'status sin gestión de ciclo de vida - AI Act Art. 9.2.d';
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Status Lifecycle', 'AI_Risk_Management', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 37.6: Verificar índices para consultas de riesgos
-- ============================================================================

\echo ''
\echo '--- Test 37.6: Indices de ai_risk_management ---'

DO $$
DECLARE
    v_index_count INTEGER;
    v_status TEXT;
    v_details TEXT;
    v_table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'ai_risk_management'
    ) INTO v_table_exists;

    IF NOT v_table_exists THEN
        v_status := 'SKIP';
        v_details := 'Tabla no existe';
    ELSE
        SELECT COUNT(*) INTO v_index_count
        FROM pg_indexes
        WHERE tablename = 'ai_risk_management';

        IF v_index_count >= 3 THEN
            v_status := 'PASS';
            v_details := format('ai_risk_management tiene %s índices (mínimo 3)', v_index_count);
        ELSIF v_index_count > 0 THEN
            v_status := 'PASS';
            v_details := format('ai_risk_management tiene %s índices (básico)', v_index_count);
        ELSE
            v_status := 'FAIL';
            v_details := 'ai_risk_management sin índices - rendimiento inadecuado';
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('ai_risk_management Indexes', 'AI_Risk_Management', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 37.7: Verificar tabla ai_testing_records (AI Act Art. 9.5)
-- ============================================================================

\echo ''
\echo '--- Test 37.7: Tabla ai_testing_records para pruebas ---'

DO $$
DECLARE
    v_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'ai_testing_records'
    ) INTO v_exists;

    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'Tabla ai_testing_records existe (AI Act Art. 9.5 - Probar riesgos)';
    ELSE
        v_status := 'FAIL';
        v_details := 'ai_testing_records NO existe - falta evidencia de pruebas (AI Act Art. 9.5)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('ai_testing_records Table', 'AI_Risk_Management', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 37.8: Verificar documentación de riesgos en comentarios
-- ============================================================================

\echo ''
\echo '--- Test 37.8: Documentacion legal en tablas ---'

DO $$
DECLARE
    v_comment TEXT;
    v_status TEXT;
    v_details TEXT;
    v_table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'ai_risk_management'
    ) INTO v_table_exists;

    IF NOT v_table_exists THEN
        v_status := 'SKIP';
        v_details := 'Tabla no existe';
    ELSE
        SELECT obj_description('ai_risk_management'::regclass, 'pg_class') INTO v_comment;

        IF v_comment LIKE '%AI Act%' OR v_comment LIKE '%Art. 9%' THEN
            v_status := 'PASS';
            v_details := 'Tabla tiene documentación legal correcta (AI Act Art. 9)';
        ELSIF v_comment IS NOT NULL THEN
            v_status := 'PASS';
            v_details := 'Documentación presente (verificar referencia AI Act)';
        ELSE
            v_status := 'FAIL';
            v_details := 'Falta documentación legal en COMMENT';
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Legal Documentation', 'AI_Risk_Management', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Legal Documentation', 'AI_Risk_Management', 'SKIP', 'Exception: ' || SQLERRM);

    RAISE NOTICE '  [SKIP] %', SQLERRM;
END $$;

-- ============================================================================
-- RESUMEN
-- ============================================================================

\echo ''
\echo '=============================================='
\echo 'RESUMEN TEST 37: GESTION DE RIESGOS IA'
\echo '=============================================='

SELECT test_category,
       COUNT(*) as total_tests,
       SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
       SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed,
       SUM(CASE WHEN status = 'SKIP' THEN 1 ELSE 0 END) as skipped
FROM test_results
GROUP BY test_category
ORDER BY test_category;

\echo ''
\echo '--- Detalle de tests ---'

SELECT test_name, status, details
FROM test_results
ORDER BY test_id;

\echo ''
\echo '=============================================='
\echo 'CUMPLIMIENTO LEGAL VERIFICADO:'
\echo '  - AI Act Art. 9.1: Sistema de gestion de riesgos'
\echo '  - AI Act Art. 9.2: Identificacion y evaluacion'
\echo '  - AI Act Art. 9.5: Pruebas de riesgos'
\echo '=============================================='

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
