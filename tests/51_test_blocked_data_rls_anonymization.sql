-- ============================================================================
-- TEST 51: RLS BLOCKED_DATA + ANONIMIZACIÓN TERCEROS (LOPDGDD Art. 33 + RGPD Art. 15.4)
-- ============================================================================
-- COBERTURA LEGAL:
--   LOPDGDD Art. 33.3: Acceso restringido a datos bloqueados (solo autoridades judiciales)
--   RGPD Art. 15.4: El derecho de acceso no debe afectar derechos de terceros
--   LOPDGDD Art. 33.4: Destrucción de datos bloqueados tras prescripción
--
-- NIVEL DE COMPLIANCE: CRÍTICO
-- CRITICIDAD: ALTA
-- ============================================================================
-- Verifica:
-- 51.1-51.4: RLS en blocked_data
-- 51.5-51.7: Función register_blocked_data_access
-- 51.8-51.9: Vista v_blocked_data_pending_destruction
-- 51.10-51.12: Anonimización de terceros en exportaciones
-- Ejecutar: psql -U postgres -d capsule -f 51_test_blocked_data_rls_anonymization.sql
-- ============================================================================

BEGIN;

\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '=============================================='
\echo 'TEST 51: RLS Blocked Data + Anonimización Terceros'
\echo '=============================================='

CREATE TEMP TABLE IF NOT EXISTS test_results (
    test_id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    test_category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMPTZ DEFAULT NOW()
);

SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';
SET app.audit_hmac_key = 'TEST_AUDIT_KEY_FOR_HMAC_CHAIN__';

-- ============================================================================
-- TEST 51.1: RLS habilitado en blocked_data
-- ============================================================================

\echo '--- Test 51.1: RLS habilitado en blocked_data ---'

DO $$
DECLARE
    v_rls_enabled BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT relrowsecurity INTO v_rls_enabled
    FROM pg_class
    WHERE relname = 'blocked_data';

    IF v_rls_enabled THEN
        v_status := 'PASS';
        v_details := 'RLS habilitado en blocked_data (LOPDGDD Art. 33.3)';
    ELSE
        v_status := 'FAIL';
        v_details := 'RLS NO habilitado en blocked_data';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('RLS Enabled on blocked_data', 'LOPDGDD_Art33', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 51.2: Política blocked_data_judicial_access existe
-- ============================================================================

\echo '--- Test 51.2: Política judicial_access existe ---'

DO $$
DECLARE
    v_policy_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'blocked_data'
        AND policyname = 'blocked_data_judicial_access'
    ) INTO v_policy_exists;

    IF v_policy_exists THEN
        v_status := 'PASS';
        v_details := 'Política blocked_data_judicial_access existe';
    ELSE
        v_status := 'FAIL';
        v_details := 'Política blocked_data_judicial_access NO encontrada';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Judicial Access Policy', 'LOPDGDD_Art33', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 51.3: Rol capsule_judicial_authority existe
-- ============================================================================

\echo '--- Test 51.3: Rol judicial_authority existe ---'

DO $$
DECLARE
    v_role_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'capsule_judicial_authority'
    ) INTO v_role_exists;

    IF v_role_exists THEN
        v_status := 'PASS';
        v_details := 'Rol capsule_judicial_authority existe para autoridades judiciales';
    ELSE
        v_status := 'FAIL';
        v_details := 'Rol capsule_judicial_authority NO existe';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Judicial Role Exists', 'LOPDGDD_Art33', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 51.4: Políticas completas para blocked_data (INSERT, UPDATE, DELETE)
-- ============================================================================

\echo '--- Test 51.4: Políticas completas blocked_data ---'

DO $$
DECLARE
    v_policy_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(*) INTO v_policy_count
    FROM pg_policies
    WHERE tablename = 'blocked_data';

    IF v_policy_count >= 4 THEN
        v_status := 'PASS';
        v_details := format('%s políticas RLS en blocked_data (SELECT, INSERT, UPDATE, DELETE)', v_policy_count);
    ELSE
        v_status := 'FAIL';
        v_details := format('Solo %s políticas RLS (esperado: 4)', v_policy_count);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Complete RLS Policies', 'LOPDGDD_Art33', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 51.5: Función register_blocked_data_access existe
-- ============================================================================

\echo '--- Test 51.5: Función register_blocked_data_access ---'

DO $$
DECLARE
    v_func_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public' AND p.proname = 'register_blocked_data_access'
    ) INTO v_func_exists;

    IF v_func_exists THEN
        v_status := 'PASS';
        v_details := 'Función register_blocked_data_access existe para trazabilidad de accesos';
    ELSE
        v_status := 'FAIL';
        v_details := 'Función register_blocked_data_access NO encontrada';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Register Access Function', 'LOPDGDD_Art33', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 51.6: Campo access_log existe en blocked_data
-- ============================================================================

\echo '--- Test 51.6: Campo access_log en blocked_data ---'

DO $$
DECLARE
    v_col_exists BOOLEAN;
    v_col_type TEXT;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'blocked_data' AND column_name = 'access_log'
    ) INTO v_col_exists;

    IF v_col_exists THEN
        SELECT data_type INTO v_col_type
        FROM information_schema.columns
        WHERE table_name = 'blocked_data' AND column_name = 'access_log';

        v_status := 'PASS';
        v_details := format('Campo access_log existe (tipo: %s) para registro de accesos judiciales', v_col_type);
    ELSE
        v_status := 'FAIL';
        v_details := 'Campo access_log NO existe en blocked_data';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Access Log Field', 'LOPDGDD_Art33', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 51.7: Campo accessible_by con valores correctos
-- ============================================================================

\echo '--- Test 51.7: Campo accessible_by con valores LOPDGDD ---'

DO $$
DECLARE
    v_default_val TEXT;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT column_default INTO v_default_val
    FROM information_schema.columns
    WHERE table_name = 'blocked_data' AND column_name = 'accessible_by';

    IF v_default_val LIKE '%JUDGES%' AND v_default_val LIKE '%PROSECUTORS%' THEN
        v_status := 'PASS';
        v_details := 'accessible_by tiene valores LOPDGDD Art. 33.3: JUDGES, PROSECUTORS, COMPETENT_AUTHORITIES';
    ELSE
        v_status := 'FAIL';
        v_details := format('accessible_by default incorrecto: %s', v_default_val);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Accessible By Values', 'LOPDGDD_Art33', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 51.8: Vista v_blocked_data_pending_destruction existe
-- ============================================================================

\echo '--- Test 51.8: Vista pending_destruction existe ---'

DO $$
DECLARE
    v_view_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.views
        WHERE table_name = 'v_blocked_data_pending_destruction'
    ) INTO v_view_exists;

    IF v_view_exists THEN
        v_status := 'PASS';
        v_details := 'Vista v_blocked_data_pending_destruction existe para monitoreo LOPDGDD Art. 33.4';
    ELSE
        v_status := 'FAIL';
        v_details := 'Vista v_blocked_data_pending_destruction NO encontrada';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Pending Destruction View', 'LOPDGDD_Art33', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 51.9: Vista pending_destruction es consultable
-- ============================================================================

\echo '--- Test 51.9: Vista pending_destruction consultable ---'

DO $$
DECLARE
    v_can_query BOOLEAN := false;
    v_status TEXT;
    v_details TEXT;
BEGIN
    BEGIN
        PERFORM * FROM v_blocked_data_pending_destruction LIMIT 1;
        v_can_query := true;
    EXCEPTION WHEN OTHERS THEN
        v_can_query := false;
    END;

    IF v_can_query THEN
        v_status := 'PASS';
        v_details := 'Vista v_blocked_data_pending_destruction consultable correctamente';
    ELSE
        v_status := 'FAIL';
        v_details := 'Vista v_blocked_data_pending_destruction no consultable';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('View Queryable', 'LOPDGDD_Art33', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 51.10: Función anonymize_third_party_data existe (RGPD Art. 15.4)
-- ============================================================================

\echo '--- Test 51.10: Función anonymize_third_party_data ---'

DO $$
DECLARE
    v_func_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public' AND p.proname = 'anonymize_third_party_data'
    ) INTO v_func_exists;

    IF v_func_exists THEN
        v_status := 'PASS';
        v_details := 'Función anonymize_third_party_data existe (RGPD Art. 15.4)';
    ELSE
        v_status := 'FAIL';
        v_details := 'Función anonymize_third_party_data NO encontrada';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Anonymize Third Party Function', 'RGPD_Art15_4', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 51.11: Función export_user_data_gdpr_compliant existe
-- ============================================================================

\echo '--- Test 51.11: Función export_user_data_gdpr_compliant ---'

DO $$
DECLARE
    v_func_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public' AND p.proname = 'export_user_data_gdpr_compliant'
    ) INTO v_func_exists;

    IF v_func_exists THEN
        v_status := 'PASS';
        v_details := 'Función export_user_data_gdpr_compliant existe (Art. 15.4 + Art. 20)';
    ELSE
        v_status := 'FAIL';
        v_details := 'Función export_user_data_gdpr_compliant NO encontrada';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('GDPR Compliant Export Function', 'RGPD_Art15_4', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 51.12: Función anonymize_third_party_data funciona correctamente
-- ============================================================================

\echo '--- Test 51.12: Anonimización de terceros funciona ---'

DO $$
DECLARE
    v_test_data JSONB;
    v_result JSONB;
    v_anonymized BOOLEAN := false;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear datos de prueba con contact_id de tercero
    v_test_data := jsonb_build_object(
        'calls', jsonb_build_array(
            jsonb_build_object(
                'call_id', 'test-call-1',
                'contact_id', '12345678-1234-1234-1234-123456789012',
                'duration', 120
            )
        ),
        'export_metadata', jsonb_build_object('format', 'json')
    );

    -- Aplicar anonimización
    v_result := anonymize_third_party_data(v_test_data, gen_random_uuid());

    -- Verificar que el contact_id fue anonimizado
    IF v_result->'calls'->0->>'contact_id' LIKE 'ANONYMIZED_%' THEN
        v_anonymized := true;
    END IF;

    -- Verificar que se añadió el flag de tercero
    IF v_result->'calls'->0->>'third_party_contact' = 'true' THEN
        v_anonymized := v_anonymized AND true;
    END IF;

    -- Verificar metadatos de anonimización
    IF v_result->'export_metadata'->'third_party_anonymization'->>'applied' = 'true' THEN
        v_anonymized := v_anonymized AND true;
    END IF;

    IF v_anonymized THEN
        v_status := 'PASS';
        v_details := format('Anonimización correcta: contact_id=%s', v_result->'calls'->0->>'contact_id');
    ELSE
        v_status := 'FAIL';
        v_details := format('Anonimización fallida: %s', v_result::TEXT);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Anonymization Works', 'RGPD_Art15_4', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- RESUMEN DE TESTS
-- ============================================================================

\echo ''
\echo '=============================================='
\echo 'RESUMEN TEST 51 - RLS Blocked Data + Anonimización'
\echo '=============================================='

DO $$
DECLARE
    v_total INTEGER;
    v_passed INTEGER;
    v_failed INTEGER;
    v_skipped INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_total FROM test_results;
    SELECT COUNT(*) INTO v_passed FROM test_results WHERE status = 'PASS';
    SELECT COUNT(*) INTO v_failed FROM test_results WHERE status = 'FAIL';
    SELECT COUNT(*) INTO v_skipped FROM test_results WHERE status = 'SKIP';

    RAISE NOTICE '';
    RAISE NOTICE 'Total tests: %', v_total;
    RAISE NOTICE 'Passed:      % (%.1f%%)', v_passed, (v_passed::NUMERIC / v_total * 100);
    RAISE NOTICE 'Failed:      %', v_failed;
    RAISE NOTICE 'Skipped:     %', v_skipped;
    RAISE NOTICE '';

    IF v_failed > 0 THEN
        RAISE NOTICE 'TESTS FALLIDOS:';
        FOR v_total IN
            SELECT test_id FROM test_results WHERE status = 'FAIL'
        LOOP
            RAISE NOTICE '  - Test %', v_total;
        END LOOP;
    END IF;
END $$;

SELECT
    test_name,
    test_category,
    status,
    details
FROM test_results
ORDER BY test_id;

ROLLBACK;
