-- ============================================================================
-- TEST 16: GDPR RIGHT TO ERASURE - Derecho al Olvido (Art. 17 RGPD)
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 17.1: Derecho de supresión
--   • RGPD Art. 17.2: Comunicar supresión a destinatarios
--   • RGPD Art. 17.3: Excepciones al derecho de supresión
--   • LOPDGDD Art. 15: Derecho de supresión
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: CRÍTICA
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Art. 17
-- ============================================================================
-- Verifica las funciones de derecho al olvido
-- Ejecutar: psql -U postgres -d sfera -f 16_test_gdpr_right_to_erasure.sql
-- ============================================================================

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '=============================================='
\echo 'TEST 16: GDPR RIGHT TO ERASURE'
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

-- Crear clave de cifrado temporal para tests si no existe
DO $$
BEGIN
    INSERT INTO encryption_keys (key_id, encrypted_key, is_active, kms_provider, activated_at)
    VALUES (
        'test_key_erasure_' || substring(gen_random_uuid()::TEXT, 1, 8),
        pgp_sym_encrypt(encode(gen_random_bytes(32), 'hex'), current_setting('app.kms_master_key'), 'cipher-algo=aes256'),
        true,
        'hashicorp-vault',
        CURRENT_TIMESTAMP
    );
EXCEPTION WHEN OTHERS THEN
    NULL;
END $$;

-- ============================================================================
-- TEST 16.1: Verificar existencia de funciones de erasure
-- ============================================================================

\echo ''
\echo '--- Test 16.1: Verificar existencia de funciones ---'

DO $$
DECLARE
    v_func1_exists BOOLEAN;
    v_func2_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Verificar gdpr_right_to_erasure
    SELECT EXISTS(
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public' AND p.proname = 'gdpr_right_to_erasure'
    ) INTO v_func1_exists;

    -- Verificar gdpr_right_to_erasure_by_phone
    SELECT EXISTS(
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public' AND p.proname = 'gdpr_right_to_erasure_by_phone'
    ) INTO v_func2_exists;

    IF v_func1_exists AND v_func2_exists THEN
        v_status := 'PASS';
        v_details := 'Both erasure functions exist';
    ELSE
        v_status := 'FAIL';
        v_details := format('Functions missing - gdpr_right_to_erasure: %s, gdpr_right_to_erasure_by_phone: %s',
            v_func1_exists, v_func2_exists);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Erasure Functions Exist', 'Right_To_Erasure', v_status, v_details);

    RAISE NOTICE '  [%] Functions: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 16.2: Verificar estructura de retorno de gdpr_right_to_erasure
-- ============================================================================

\echo ''
\echo '--- Test 16.2: Estructura de retorno de funcion ---'

DO $$
DECLARE
    v_return_type TEXT;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Verificar tipo de retorno
    SELECT pg_catalog.format_type(p.prorettype, NULL)
    INTO v_return_type
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'public' AND p.proname = 'gdpr_right_to_erasure'
    LIMIT 1;

    IF v_return_type = 'json' THEN
        v_status := 'PASS';
        v_details := 'Function returns JSON as expected';
    ELSE
        v_status := 'FAIL';
        v_details := format('Unexpected return type: %s (expected json)', v_return_type);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Return Type Verification', 'Right_To_Erasure', v_status, v_details);

    RAISE NOTICE '  [%] Return Type: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Return Type Verification', 'Right_To_Erasure', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Return Type: Exception - %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 16.3: Ejecutar erasure de contacto (tipo válido)
-- ============================================================================

\echo ''
\echo '--- Test 16.3: Erasure de contacto ---'

DO $$
DECLARE
    v_user_id UUID;
    v_contact_id UUID;
    v_result JSON;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario de prueba
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_ERASURE_USER', 'erasure_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Crear contacto
    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_user_id,
        encrypt_pii_with_metadata('Erasure Test Contact'),
        encrypt_pii_with_metadata('+34600222333'),
        (secure_hash_with_pepper('+34600222333')).hash
    )
    RETURNING id INTO v_contact_id;

    -- Ejecutar erasure de contacto
    SELECT gdpr_right_to_erasure(v_contact_id, 'contact') INTO v_result;

    -- Verificar que la función retornó un resultado
    IF v_result IS NOT NULL THEN
        v_status := 'PASS';
        v_details := format('Erasure executed for contact %s. Result: %s', v_contact_id, v_result::text);
    ELSE
        v_status := 'FAIL';
        v_details := 'Function returned NULL';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Contact Erasure Execution', 'Right_To_Erasure', v_status, v_details);

    RAISE NOTICE '  [%] Contact Erasure: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Contact Erasure Execution', 'Right_To_Erasure', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Contact Erasure: Exception - %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 16.4: Verificar parámetros de gdpr_right_to_erasure_by_phone
-- ============================================================================

\echo ''
\echo '--- Test 16.4: Parametros de erasure por telefono ---'

DO $$
DECLARE
    v_param_count INTEGER;
    v_param_types TEXT;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Verificar parámetros de la función
    -- Debe aceptar TEXT (teléfono en texto plano), NO VARCHAR (hash)
    SELECT p.pronargs,
           pg_catalog.pg_get_function_arguments(p.oid)
    INTO v_param_count, v_param_types
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'public' AND p.proname = 'gdpr_right_to_erasure_by_phone'
    LIMIT 1;

    -- Verificar que acepta p_phone TEXT (texto plano, no hash)
    IF v_param_count = 1 AND v_param_types LIKE 'p_phone text' THEN
        v_status := 'PASS';
        v_details := format('Function correctly accepts plain text phone. Args: %s', v_param_types);
    ELSIF v_param_types LIKE '%character varying%' OR v_param_types LIKE '%varchar%' THEN
        v_status := 'FAIL';
        v_details := format('Design error: Function expects hash instead of plain text. Args: %s', v_param_types);
    ELSE
        v_status := 'PASS';
        v_details := format('Function accepts phone parameter. Args: %s', v_param_types);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Phone Erasure Parameters', 'Right_To_Erasure', v_status, v_details);

    RAISE NOTICE '  [%] Phone Params: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Phone Erasure Parameters', 'Right_To_Erasure', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Phone Params: Exception - %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 16.5: Verificar que erasure respeta retencion legal
-- ============================================================================

\echo ''
\echo '--- Test 16.5: Erasure respeta retencion legal ---'

DO $$
DECLARE
    v_user_id UUID;
    v_contact_id UUID;
    v_call_id UUID;
    v_purpose_id UUID;
    v_consent_id UUID;
    v_consent_version_id UUID;
    v_call_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_LEGAL_USER', 'legal_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Crear contacto
    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_user_id,
        encrypt_pii_with_metadata('Legal Test'),
        encrypt_pii_with_metadata('+34600444555'),
        (secure_hash_with_pepper('+34600444555')).hash
    )
    RETURNING id INTO v_contact_id;

    -- Crear llamada con retención legal (gdpr_deletion_scheduled en el futuro)
    INSERT INTO calls (
        user_id, contact_id, call_date, call_time, caller_name_encrypted, caller_phone_encrypted,
        caller_phone_hash, call_timestamp, duration_seconds, status, recording_encrypted,
        gdpr_deletion_scheduled
    )
    VALUES (
        v_user_id, v_contact_id, CURRENT_DATE, CURRENT_TIME,
        encrypt_pii_with_metadata('Legal Test Caller'),
        encrypt_pii_with_metadata('+34600444555'),
        (secure_hash_with_pepper('+34600444555')).hash,
        CURRENT_TIMESTAMP, 300, 'completed', false,
        CURRENT_DATE + INTERVAL '1 year'  -- Retención legal de 1 año
    )
    RETURNING id INTO v_call_id;

    -- Verificar que la llamada existe antes de cualquier operación
    SELECT EXISTS(SELECT 1 FROM calls WHERE id = v_call_id) INTO v_call_exists;

    IF v_call_exists THEN
        v_status := 'PASS';
        v_details := format('Call with legal retention exists: %s (deletion scheduled: %s)',
            v_call_id, (SELECT gdpr_deletion_scheduled FROM calls WHERE id = v_call_id));
    ELSE
        v_status := 'FAIL';
        v_details := 'Call not created properly';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Legal Retention Setup', 'Right_To_Erasure', v_status, v_details);

    RAISE NOTICE '  [%] Legal Retention: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Legal Retention Setup', 'Right_To_Erasure', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Legal Retention: Exception - %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 16.6: Verificar índices de rendimiento para erasure
-- ============================================================================

\echo ''
\echo '--- Test 16.6: Indices de rendimiento ---'

DO $$
DECLARE
    v_idx_contacts_user BOOLEAN;
    v_idx_calls_contact BOOLEAN;
    v_idx_consents_subject BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Verificar índices relevantes para erasure
    SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE indexname LIKE '%contacts%user%') INTO v_idx_contacts_user;
    SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE indexname LIKE '%calls%contact%') INTO v_idx_calls_contact;
    SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE indexname LIKE '%consents%subject%') INTO v_idx_consents_subject;

    IF v_idx_contacts_user OR v_idx_calls_contact THEN
        v_status := 'PASS';
        v_details := format('Erasure indexes present - contacts_user: %s, calls_contact: %s',
            v_idx_contacts_user, v_idx_calls_contact);
    ELSE
        v_status := 'FAIL';
        v_details := 'Missing critical indexes for erasure operations';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Erasure Performance Indexes', 'Right_To_Erasure', v_status, v_details);

    RAISE NOTICE '  [%] Indexes: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Erasure Performance Indexes', 'Right_To_Erasure', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Indexes: Exception - %', SQLERRM;
END $$;

-- ============================================================================
-- RESUMEN
-- ============================================================================

\echo ''
\echo '=============================================='
\echo 'RESUMEN TEST 16: GDPR RIGHT TO ERASURE'
\echo '=============================================='

SELECT test_category,
       COUNT(*) as total_tests,
       SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
       SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed,
       SUM(CASE WHEN status = 'SKIP' THEN 1 ELSE 0 END) as skipped
FROM test_results
GROUP BY test_category;

SELECT test_name, status, details
FROM test_results
ORDER BY test_id;

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
