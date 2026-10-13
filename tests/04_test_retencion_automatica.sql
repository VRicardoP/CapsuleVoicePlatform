-- ============================================================================
-- TEST 04: RETENCIÓN AUTOMÁTICA
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 5.1.e: Limitación del plazo de conservación
--   • RGPD Art. 17.1.a: Supresión cuando datos ya no son necesarios para fines
--   • RGPD Art. 13.2.a: Informar al interesado del plazo de conservación
--   • RGPD Art. 32.1.c: Capacidad de restaurar disponibilidad y acceso a datos
--
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: CRÍTICA (principio fundamental de minimización temporal)
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Principios del Tratamiento (Art. 5)
-- ============================================================================
-- Verifica políticas de retención, scheduled_deletion y triggers automáticos
-- Ejecutar: \i /path/to/04_test_retencion_automatica.sql

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

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
-- TEST 4.1: Sesiones Expiradas se Eliminan
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_expired_session_id UUID;
    v_valid_session_id UUID;
    v_expired_deleted BOOLEAN;
    v_valid_kept BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario de prueba
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_RETENTION_USER', 'test_retention_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash', 'admin')
    RETURNING id INTO v_test_user_id;

    -- Crear sesión EXPIRADA (hace 2 días) - debe estar revocada para cumplir constraint
    INSERT INTO user_sessions (user_id, token_hash, token_algorithm, expires_at, ip_address, is_revoked)
    VALUES (
        v_test_user_id,
        'EXPIRED_SESSION_' || gen_random_uuid()::TEXT,
        'sha256',
        CURRENT_TIMESTAMP - INTERVAL '2 days',
        '127.0.0.1'::INET,
        true  -- Revocada porque está expirada
    )
    RETURNING id INTO v_expired_session_id;

    -- Crear sesión VÁLIDA (expira en 1 hora)
    INSERT INTO user_sessions (user_id, token_hash, token_algorithm, expires_at, ip_address, is_revoked)
    VALUES (
        v_test_user_id,
        'VALID_SESSION_' || gen_random_uuid()::TEXT,
        'sha256',
        CURRENT_TIMESTAMP + INTERVAL '1 hour',
        '127.0.0.1'::INET,
        false
    )
    RETURNING id INTO v_valid_session_id;

    -- Ejecutar mantenimiento programado
    PERFORM scheduled_maintenance();

    -- Verificar resultados
    v_expired_deleted := NOT EXISTS(SELECT 1 FROM user_sessions WHERE id = v_expired_session_id);
    v_valid_kept := EXISTS(SELECT 1 FROM user_sessions WHERE id = v_valid_session_id);

    IF v_expired_deleted AND v_valid_kept THEN
        v_status := 'PASS';
        v_details := 'Expired sessions deleted, valid sessions kept';
    ELSE
        v_status := 'FAIL';
        v_details := format('Retention failed - expired_deleted:%s, valid_kept:%s',
            v_expired_deleted, v_valid_kept);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Expired Sessions Cleanup', 'Data_Retention', v_status, v_details);

    RAISE NOTICE '  [%] Expired Sessions: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Expired Sessions Cleanup', 'Data_Retention', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 4.2: Anonimización de IPs Antiguas
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_old_session_id UUID;
    v_ip_anonymized BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario de prueba
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_IP_ANON_USER', 'test_ip_anon_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash', 'admin')
    RETURNING id INTO v_test_user_id;

    -- Crear sesión antigua con IP (más de 90 días, pero no expirada para evitar eliminación)
    INSERT INTO user_sessions (user_id, token_hash, token_algorithm, expires_at, ip_address, ip_anonymized, is_revoked, created_at)
    VALUES (
        v_test_user_id,
        'OLD_IP_SESSION_' || gen_random_uuid()::TEXT,
        'sha256',
        CURRENT_TIMESTAMP + INTERVAL '1 hour',
        '192.168.1.100'::INET,
        false,
        false,
        CURRENT_TIMESTAMP - INTERVAL '100 days'
    )
    RETURNING id INTO v_old_session_id;

    -- Ejecutar anonimización de IPs
    PERFORM anonymize_old_ip_addresses();

    -- Verificar que la IP fue anonimizada
    SELECT ip_anonymized INTO v_ip_anonymized
    FROM user_sessions WHERE id = v_old_session_id;

    IF v_ip_anonymized THEN
        v_status := 'PASS';
        v_details := 'Old IP addresses correctly anonymized';
    ELSE
        v_status := 'FAIL';
        v_details := 'Old IP addresses were not anonymized';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('IP Anonymization', 'Data_Retention', v_status, v_details);

    RAISE NOTICE '  [%] IP Anonymization: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('IP Anonymization', 'Data_Retention', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 4.3: Período de Retención por Propósito
-- ============================================================================

DO $$
DECLARE
    v_purpose_id UUID;
    v_retention_days INTEGER;
    v_has_retention BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Verificar que todos los propósitos tienen período de retención definido
    SELECT
        COUNT(*) = 0 INTO v_has_retention
    FROM data_processing_purposes
    WHERE retention_period_days IS NULL OR retention_period_days <= 0;

    -- Obtener ejemplo de retención
    SELECT id, retention_period_days INTO v_purpose_id, v_retention_days
    FROM data_processing_purposes
    WHERE code = 'call_recording'
    LIMIT 1;

    IF v_has_retention AND v_retention_days > 0 THEN
        v_status := 'PASS';
        v_details := format('All purposes have retention periods defined (e.g., call_recording: %s days)', v_retention_days);
    ELSE
        v_status := 'FAIL';
        v_details := 'Some purposes missing retention period definition';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Retention Period Defined', 'Data_Retention', v_status, v_details);

    RAISE NOTICE '  [%] Retention Period: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Retention Period Defined', 'Data_Retention', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 4.4: Función scheduled_maintenance Existe y Ejecuta
-- ============================================================================

DO $$
DECLARE
    v_function_exists BOOLEAN;
    v_executes_ok BOOLEAN := false;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Verificar que la función existe
    SELECT EXISTS(
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public' AND p.proname = 'scheduled_maintenance'
    ) INTO v_function_exists;

    IF v_function_exists THEN
        -- Intentar ejecutar
        BEGIN
            PERFORM scheduled_maintenance();
            v_executes_ok := true;
        EXCEPTION WHEN OTHERS THEN
            v_executes_ok := false;
        END;
    END IF;

    IF v_function_exists AND v_executes_ok THEN
        v_status := 'PASS';
        v_details := 'scheduled_maintenance() exists and executes successfully';
    ELSIF v_function_exists THEN
        v_status := 'FAIL';
        v_details := 'scheduled_maintenance() exists but fails to execute';
    ELSE
        v_status := 'FAIL';
        v_details := 'scheduled_maintenance() function does not exist';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Maintenance Function', 'Data_Retention', v_status, v_details);

    RAISE NOTICE '  [%] Maintenance Function: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Maintenance Function', 'Data_Retention', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- RESUMEN DE RESULTADOS
-- ============================================================================

SELECT
    test_category,
    COUNT(*) as total_tests,
    COUNT(*) FILTER (WHERE status = 'PASS') as passed,
    COUNT(*) FILTER (WHERE status = 'FAIL') as failed,
    COUNT(*) FILTER (WHERE status = 'SKIP') as skipped
FROM test_results
WHERE test_category = 'Data_Retention'
GROUP BY test_category;

SELECT test_name, details
FROM test_results
WHERE test_category = 'Data_Retention' AND status = 'FAIL';

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
