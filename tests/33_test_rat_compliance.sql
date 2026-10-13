-- ============================================================================
-- TEST 33: REGISTRO DE ACTIVIDADES DE TRATAMIENTO (RAT)
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 30: Registro de actividades de tratamiento (RAT)
--   • RGPD Art. 5.2: Responsabilidad proactiva (demostrar cumpl imiento)
--   • RGPD Art. 24.1: Medidas apropiadas y demostrables
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: ALTA
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Responsable y Encargado (Art. 30)
-- ============================================================================
-- Verifica que el RAT está completo y contiene todos elementos requeridos
-- Ejecutar: \i /path/to/33_test_rat_compliance.sql

BEGIN;
\set ON_ERROR_STOP on
SET client_min_messages = notice;

CREATE TEMP TABLE test_results (
    test_id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    test_category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';
SET app.hash_pepper = 'TEST_PEPPER_V1_FOR_HMAC_FUNCTIONS';
SET app.hash_pepper_version = '1';
SET app.audit_hmac_key = 'TEST_AUDIT_KEY_FOR_HMAC_CHAIN__';

-- ============================================================================
-- TEST 33.1: Tabla data_processing_purposes Contiene Elementos RAT
-- ============================================================================

DO $$
DECLARE
    v_required_columns TEXT[] := ARRAY['name', 'description', 'legal_basis', 'retention_period_days'];
    v_missing_columns TEXT[];
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT ARRAY_AGG(col)
    INTO v_missing_columns
    FROM UNNEST(v_required_columns) AS col
    WHERE NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'data_processing_purposes'
        AND column_name = col
    );

    IF v_missing_columns IS NULL OR array_length(v_missing_columns, 1) IS NULL THEN
        v_status := 'PASS';
        v_details := 'RAT table has all required columns per Art. 30 RGPD';
    ELSE
        v_status := 'FAIL';
        v_details := format('Missing RAT columns: %s', array_to_string(v_missing_columns, ', '));
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('RAT Required Columns', 'RAT_Compliance', v_status, v_details);
    RAISE NOTICE '  [%] RAT Columns: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('RAT Required Columns', 'RAT_Compliance', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 33.2: Todas las Finalidades Tienen Descripción Clara
-- ============================================================================

DO $$
DECLARE
    v_unclear_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(*) INTO v_unclear_count
    FROM data_processing_purposes
    WHERE description IS NULL
    OR length(description) < 20;

    IF v_unclear_count = 0 THEN
        v_status := 'PASS';
        v_details := 'All purposes have clear descriptions (Art. 30.1.b RGPD)';
    ELSE
        v_status := 'FAIL';
        v_details := format('%s purposes with unclear/missing descriptions', v_unclear_count);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('RAT Clear Descriptions', 'RAT_Compliance', v_status, v_details);
    RAISE NOTICE '  [%] RAT Descriptions: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('RAT Clear Descriptions', 'RAT_Compliance', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 33.3: Plazos de Conservación Documentados
-- ============================================================================

DO $$
DECLARE
    v_missing_retention INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(*) INTO v_missing_retention
    FROM data_processing_purposes
    WHERE retention_period_days IS NULL
    OR retention_period_days <= 0;

    IF v_missing_retention = 0 THEN
        v_status := 'PASS';
        v_details := 'All purposes have retention periods defined (Art. 30.1.f RGPD)';
    ELSE
        v_status := 'FAIL';
        v_details := format('%s purposes missing retention period', v_missing_retention);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('RAT Retention Periods', 'RAT_Compliance', v_status, v_details);
    RAISE NOTICE '  [%] RAT Retention: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('RAT Retention Periods', 'RAT_Compliance', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- RESUMEN
-- ============================================================================

SELECT test_category, COUNT(*) as total, COUNT(*) FILTER (WHERE status = 'PASS') as passed,
       COUNT(*) FILTER (WHERE status = 'FAIL') as failed
FROM test_results WHERE test_category = 'RAT_Compliance' GROUP BY test_category;

ROLLBACK;
