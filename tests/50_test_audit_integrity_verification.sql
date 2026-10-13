-- ============================================================================
-- TEST 50: Verificación de Integridad del Audit Log
-- ============================================================================
-- Fecha: 2025-12-04
-- Cobertura:
--   - RGPD Art. 5.2: Responsabilidad proactiva (demostrar integridad)
--   - RGPD Art. 30: Registro de actividades de tratamiento
--   - NIS2 Art. 21.2.f: Evaluación de eficacia de medidas de seguridad
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'TEST 50: Verificación de Integridad del Audit Log'
\echo '============================================================================'
\echo 'RGPD Art. 5.2, Art. 30 | NIS2 Art. 21.2.f'
\echo '============================================================================'
\echo ''

BEGIN;
\set ON_ERROR_STOP on
SET client_min_messages = notice;

CREATE TEMP TABLE test_results (
    test_id SERIAL,
    test_name TEXT,
    test_category TEXT,
    status TEXT CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMPTZ DEFAULT NOW()
);

SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';
SET app.audit_hmac_key = 'TEST_AUDIT_KEY_FOR_HMAC_CHAIN__';

-- ============================================================================
-- TEST 50.1: Función validate_audit_log_integrity existe
-- ============================================================================

\echo '--- Test 50.1: Función validate_audit_log_integrity existe ---'

DO $$
DECLARE
    v_function_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE p.proname = 'validate_audit_log_integrity'
        AND n.nspname = 'public'
    ) INTO v_function_exists;

    IF v_function_exists THEN
        v_status := 'PASS';
        v_details := 'Función validate_audit_log_integrity() existe (RGPD Art. 5.2)';
    ELSE
        v_status := 'FAIL';
        v_details := 'Función validate_audit_log_integrity() NO existe';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Validate Integrity Function', 'Audit_Integrity', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 50.2: Función verify_audit_log_integrity_summary existe
-- ============================================================================

\echo '--- Test 50.2: Función resumen de integridad existe ---'

DO $$
DECLARE
    v_function_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE p.proname = 'verify_audit_log_integrity_summary'
        AND n.nspname = 'public'
    ) INTO v_function_exists;

    IF v_function_exists THEN
        v_status := 'PASS';
        v_details := 'Función verify_audit_log_integrity_summary() existe para verificaciones periódicas';
    ELSE
        v_status := 'FAIL';
        v_details := 'Función verify_audit_log_integrity_summary() NO existe';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Summary Function', 'Audit_Integrity', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 50.3: Vista v_audit_log_integrity_status existe
-- ============================================================================

\echo '--- Test 50.3: Vista de estado de integridad ---'

DO $$
DECLARE
    v_view_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.views
        WHERE table_name = 'v_audit_log_integrity_status'
    ) INTO v_view_exists;

    IF v_view_exists THEN
        v_status := 'PASS';
        v_details := 'Vista v_audit_log_integrity_status existe para dashboards';
    ELSE
        v_status := 'FAIL';
        v_details := 'Vista v_audit_log_integrity_status NO existe';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Integrity Status View', 'Audit_Integrity', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 50.4: Campos de hash chain en audit_log
-- ============================================================================

\echo '--- Test 50.4: Campos de hash chain en audit_log ---'

DO $$
DECLARE
    v_hash_fields INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(*) INTO v_hash_fields
    FROM information_schema.columns
    WHERE table_name = 'audit_log'
    AND column_name IN ('previous_hash', 'current_hash', 'timestamp_signature');

    IF v_hash_fields = 3 THEN
        v_status := 'PASS';
        v_details := 'Campos hash chain presentes: previous_hash, current_hash, timestamp_signature';
    ELSE
        v_status := 'FAIL';
        v_details := format('Solo %s/3 campos de hash chain encontrados', v_hash_fields);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Hash Chain Fields', 'Audit_Integrity', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 50.5: Trigger audit_log_hash_chain existe
-- ============================================================================

\echo '--- Test 50.5: Trigger de hash chain existe ---'

DO $$
DECLARE
    v_trigger_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_trigger t
        JOIN pg_class c ON t.tgrelid = c.oid
        WHERE t.tgname = 'audit_log_hash_chain'
        AND c.relname = 'audit_log'
    ) INTO v_trigger_exists;

    IF v_trigger_exists THEN
        v_status := 'PASS';
        v_details := 'Trigger audit_log_hash_chain activo para generar cadena de hashes';
    ELSE
        v_status := 'FAIL';
        v_details := 'Trigger audit_log_hash_chain NO existe';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Hash Chain Trigger', 'Audit_Integrity', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 50.6: Verificación de integridad funciona correctamente
-- ============================================================================

\echo '--- Test 50.6: Verificación de integridad funciona ---'

DO $$
DECLARE
    v_test_user_id UUID;
    v_result RECORD;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario de prueba
    INSERT INTO users (email, password_hash, name, role)
    VALUES ('test_integrity_' || gen_random_uuid()::text || '@test.com', 'hash', 'Test Integrity User', 'user')
    RETURNING id INTO v_test_user_id;

    -- Crear registro en audit_log usando acción válida
    INSERT INTO audit_log (user_id, action, entity_type, entity_id, details, ip_address, legal_basis)
    VALUES (v_test_user_id, 'SYSTEM_ALERT', 'test', gen_random_uuid(),
            '{"test": "integrity_verification", "alert_type": "TEST"}'::jsonb, '127.0.0.1'::inet, 'Test');

    -- Verificar integridad del último registro
    SELECT * INTO v_result
    FROM validate_audit_log_integrity()
    ORDER BY sequence_num DESC
    LIMIT 1;

    IF v_result.is_valid THEN
        v_status := 'PASS';
        v_details := 'Verificación de integridad funciona: registro válido con hash correcto';
    ELSE
        v_status := 'FAIL';
        v_details := format('Verificación falló: %s', v_result.error_details);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Integrity Verification Works', 'Audit_Integrity', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 50.7: Función resumen retorna datos correctos
-- ============================================================================

\echo '--- Test 50.7: Función resumen retorna datos correctos ---'

DO $$
DECLARE
    v_result RECORD;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT * INTO v_result FROM verify_audit_log_integrity_summary();

    IF v_result.verification_status IS NOT NULL AND v_result.total_records >= 0 THEN
        v_status := 'PASS';
        v_details := format('Resumen: %s registros, %s%% integridad, estado: %s',
                           v_result.total_records, v_result.integrity_percentage, v_result.verification_status);
    ELSE
        v_status := 'FAIL';
        v_details := 'Función resumen no retorna datos válidos';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Summary Function Works', 'Audit_Integrity', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 50.8: Vista de estado accesible
-- ============================================================================

\echo '--- Test 50.8: Vista de estado accesible ---'

DO $$
DECLARE
    v_result RECORD;
    v_status TEXT;
    v_details TEXT;
    v_can_query BOOLEAN := false;
BEGIN
    -- La vista puede no retornar datos si no hay registros, pero debe ser consultable
    BEGIN
        SELECT * INTO v_result FROM v_audit_log_integrity_status LIMIT 1;
        v_can_query := true;
    EXCEPTION WHEN OTHERS THEN
        v_can_query := false;
    END;

    IF v_can_query THEN
        v_status := 'PASS';
        IF v_result.verification_status IS NOT NULL THEN
            v_details := format('Vista accesible - Estado: %s, Integridad: %s%%',
                               v_result.verification_status, v_result.integrity_percentage);
        ELSE
            v_details := 'Vista accesible y funcional';
        END IF;
    ELSE
        v_status := 'FAIL';
        v_details := 'Vista v_audit_log_integrity_status no es consultable';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Status View Accessible', 'Audit_Integrity', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 50.9: Inmutabilidad del audit_log (no UPDATE)
-- ============================================================================

\echo '--- Test 50.9: Inmutabilidad - UPDATE bloqueado ---'

DO $$
DECLARE
    v_update_blocked BOOLEAN := false;
    v_test_user_id UUID;
    v_seq_num BIGINT;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario y registro de prueba
    INSERT INTO users (email, password_hash, name, role)
    VALUES ('test_immut_upd_' || gen_random_uuid()::text || '@test.com', 'hash', 'Test Immut', 'user')
    RETURNING id INTO v_test_user_id;

    INSERT INTO audit_log (user_id, action, entity_type, entity_id, details, ip_address, legal_basis)
    VALUES (v_test_user_id, 'LOGIN', 'users', v_test_user_id,
            '{"test": "immutability"}'::jsonb, '127.0.0.1'::inet, 'Test')
    RETURNING sequence_number INTO v_seq_num;

    -- Intentar UPDATE
    BEGIN
        UPDATE audit_log SET action = 'LOGOUT' WHERE sequence_number = v_seq_num;
    EXCEPTION WHEN OTHERS THEN
        v_update_blocked := true;
    END;

    IF v_update_blocked THEN
        v_status := 'PASS';
        v_details := 'UPDATE bloqueado en audit_log (RGPD Art. 30 - inmutabilidad)';
    ELSE
        v_status := 'FAIL';
        v_details := 'ALERTA: UPDATE permitido en audit_log - viola inmutabilidad';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Immutability UPDATE Block', 'Audit_Integrity', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 50.10: Inmutabilidad del audit_log (no DELETE)
-- ============================================================================

\echo '--- Test 50.10: Inmutabilidad - DELETE bloqueado ---'

DO $$
DECLARE
    v_delete_blocked BOOLEAN := false;
    v_test_user_id UUID;
    v_seq_num BIGINT;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario y registro de prueba
    INSERT INTO users (email, password_hash, name, role)
    VALUES ('test_immut_del_' || gen_random_uuid()::text || '@test.com', 'hash', 'Test Immut Del', 'user')
    RETURNING id INTO v_test_user_id;

    INSERT INTO audit_log (user_id, action, entity_type, entity_id, details, ip_address, legal_basis)
    VALUES (v_test_user_id, 'LOGOUT', 'users', v_test_user_id,
            '{"test": "immutability_delete"}'::jsonb, '127.0.0.1'::inet, 'Test')
    RETURNING sequence_number INTO v_seq_num;

    -- Intentar DELETE
    BEGIN
        DELETE FROM audit_log WHERE sequence_number = v_seq_num;
    EXCEPTION WHEN OTHERS THEN
        v_delete_blocked := true;
    END;

    IF v_delete_blocked THEN
        v_status := 'PASS';
        v_details := 'DELETE bloqueado en audit_log (RGPD Art. 30 - inmutabilidad)';
    ELSE
        v_status := 'FAIL';
        v_details := 'ALERTA: DELETE permitido en audit_log - viola inmutabilidad';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Immutability DELETE Block', 'Audit_Integrity', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 50.11: Cadena de hashes válida
-- ============================================================================

\echo '--- Test 50.11: Cadena de hashes válida ---'

DO $$
DECLARE
    v_invalid_count INTEGER;
    v_total_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT
        COUNT(*) FILTER (WHERE is_valid = false),
        COUNT(*)
    INTO v_invalid_count, v_total_count
    FROM validate_audit_log_integrity();

    IF v_invalid_count = 0 AND v_total_count > 0 THEN
        v_status := 'PASS';
        v_details := format('Cadena de %s hashes verificada - 100%% válidos', v_total_count);
    ELSIF v_total_count = 0 THEN
        v_status := 'PASS';
        v_details := 'Sin registros previos - cadena vacía es válida';
    ELSE
        v_status := 'FAIL';
        v_details := format('%s de %s registros con hash inválido', v_invalid_count, v_total_count);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Hash Chain Valid', 'Audit_Integrity', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 50.12: Timestamp signature válida
-- ============================================================================

\echo '--- Test 50.12: Timestamp signatures válidas ---'

DO $$
DECLARE
    v_invalid_ts INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(*) INTO v_invalid_ts
    FROM validate_audit_log_integrity()
    WHERE has_valid_timestamp = false;

    IF v_invalid_ts = 0 THEN
        v_status := 'PASS';
        v_details := 'Todas las firmas de timestamp son válidas (HMAC-SHA256)';
    ELSE
        v_status := 'FAIL';
        v_details := format('%s registros con timestamp signature inválida', v_invalid_ts);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Timestamp Signatures Valid', 'Audit_Integrity', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- RESUMEN DE RESULTADOS
-- ============================================================================

\echo ''
\echo '--- Resumen Test 50 ---'

SELECT test_category,
       COUNT(*) as total,
       SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
       SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed,
       SUM(CASE WHEN status = 'SKIP' THEN 1 ELSE 0 END) as skipped
FROM test_results
GROUP BY test_category;

\echo ''
\echo '--- Detalle de Tests ---'

SELECT test_name, status, details FROM test_results ORDER BY test_id;

\echo ''
\echo '============================================================================'
\echo 'TEST 50 COMPLETADO - Verificación de Integridad del Audit Log'
\echo '============================================================================'

ROLLBACK;
