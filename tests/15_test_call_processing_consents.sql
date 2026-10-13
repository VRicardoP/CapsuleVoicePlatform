-- ============================================================================
-- TEST 15: CALL_PROCESSING_CONSENTS - Consentimientos por Llamada
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 7: Condiciones del consentimiento
--   • RGPD Art. 6.1.a: Consentimiento como base legal
--   • RGPD Art. 13.2.c: Informar derecho a retirar consentimiento
--   • Guía AEPD Grabación de Llamadas: consentimiento expreso
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: CRÍTICA
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Art. 6-7, PARTE 10 (Guías AEPD)
-- ============================================================================
-- Verifica la correcta gestión de consentimientos vinculados a llamadas
-- Art. 5.1.b RGPD (limitación de finalidad)
-- Ejecutar: psql -U postgres -d sfera -f 15_test_call_processing_consents.sql
-- ============================================================================

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '=============================================='
\echo 'TEST 15: CALL PROCESSING CONSENTS'
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
        'test_key_cpc_' || substring(gen_random_uuid()::TEXT, 1, 8),
        pgp_sym_encrypt(encode(gen_random_bytes(32), 'hex'), current_setting('app.kms_master_key'), 'cipher-algo=aes256'),
        true,
        'hashicorp-vault',
        CURRENT_TIMESTAMP
    );
EXCEPTION WHEN OTHERS THEN
    NULL;
END $$;

-- ============================================================================
-- TEST 15.1: Crear call_processing_consent correctamente
-- ============================================================================

\echo ''
\echo '--- Test 15.1: Crear call_processing_consent ---'

DO $$
DECLARE
    v_user_id UUID;
    v_contact_id UUID;
    v_call_id UUID;
    v_purpose_id UUID;
    v_consent_id UUID;
    v_consent_version_id UUID;
    v_cpc_id UUID;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario de prueba
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_CPC_USER', 'cpc_user_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Crear contacto
    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_user_id,
        encrypt_pii_with_metadata('CPC Test'),
        encrypt_pii_with_metadata('+34600000001'),
        (secure_hash_with_pepper('+34600000001')).hash
    )
    RETURNING id INTO v_contact_id;

    -- Crear llamada
    INSERT INTO calls (
        user_id, contact_id, call_date, call_time, caller_name_encrypted, caller_phone_encrypted,
        caller_phone_hash, call_timestamp, duration_seconds, status, recording_encrypted
    )
    VALUES (
        v_user_id, v_contact_id, CURRENT_DATE, CURRENT_TIME,
        encrypt_pii_with_metadata('Test Caller'),
        encrypt_pii_with_metadata('+34600000001'),
        (secure_hash_with_pepper('+34600000001')).hash,
        CURRENT_TIMESTAMP, 120, 'completed', false
    )
    RETURNING id INTO v_call_id;

    -- Obtener propósito de grabación
    SELECT id INTO v_purpose_id FROM data_processing_purposes WHERE code = 'call_recording' LIMIT 1;

    -- Crear consentimiento
    -- Crear consent_version primero
    INSERT INTO consent_versions (purpose_id, version, effective_from, consent_text, consent_text_hash)
    VALUES (v_purpose_id, '1.0', CURRENT_TIMESTAMP, 'Test consent text', encode(sha256('Test consent text'::bytea), 'hex'))
    ON CONFLICT DO NOTHING;
    
    SELECT id INTO v_consent_version_id FROM consent_versions WHERE purpose_id = v_purpose_id LIMIT 1;
    
    INSERT INTO data_consents (
        data_subject_id, data_subject_type, purpose_id, consent_version_id, consent_given, obtained_method,
        ip_address
    )
    VALUES (
        v_contact_id, 'contact', v_purpose_id, v_consent_version_id, true, 'explicit_verbal',
        '127.0.0.1'::INET
    )
    RETURNING id INTO v_consent_id;

    -- Crear call_processing_consent
    INSERT INTO call_processing_consents (
        call_id, purpose_id, consent_id, retention_until
    )
    VALUES (
        v_call_id, v_purpose_id, v_consent_id,
        CURRENT_DATE + INTERVAL '90 days'
    )
    RETURNING id INTO v_cpc_id;

    IF v_cpc_id IS NOT NULL THEN
        v_status := 'PASS';
        v_details := format('call_processing_consent created: %s', v_cpc_id);
    ELSE
        v_status := 'FAIL';
        v_details := 'Failed to create call_processing_consent';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Create call_processing_consent', 'Call_Processing', v_status, v_details);

    RAISE NOTICE '  [%] Create CPC: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Create call_processing_consent', 'Call_Processing', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Create CPC: Exception - %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 15.2: Validar que consent_id pertenece al contacto de la llamada
-- ============================================================================

\echo ''
\echo '--- Test 15.2: Validar ownership de consentimiento ---'

DO $$
DECLARE
    v_user_id UUID;
    v_contact1_id UUID;
    v_contact2_id UUID;
    v_call_id UUID;
    v_purpose_id UUID;
    v_consent_version_id UUID;
    v_consent_other_id UUID;
    v_error_raised BOOLEAN := false;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_CPC_OWNER', 'cpc_owner_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Crear dos contactos diferentes
    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_user_id,
        encrypt_pii_with_metadata('Contact1 Test'),
        encrypt_pii_with_metadata('+34600000011'),
        (secure_hash_with_pepper('+34600000011')).hash
    )
    RETURNING id INTO v_contact1_id;

    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_user_id,
        encrypt_pii_with_metadata('Contact2 Test'),
        encrypt_pii_with_metadata('+34600000012'),
        (secure_hash_with_pepper('+34600000012')).hash
    )
    RETURNING id INTO v_contact2_id;

    -- Llamada del contacto 1
    INSERT INTO calls (
        user_id, contact_id, call_date, call_time, caller_name_encrypted, caller_phone_encrypted,
        caller_phone_hash, call_timestamp, duration_seconds, status, recording_encrypted
    )
    VALUES (
        v_user_id, v_contact1_id, CURRENT_DATE, CURRENT_TIME,
        encrypt_pii_with_metadata('Test'),
        encrypt_pii_with_metadata('+34600000002'),
        (secure_hash_with_pepper('+34600000002')).hash,
        CURRENT_TIMESTAMP, 60, 'completed', false
    )
    RETURNING id INTO v_call_id;

    -- Obtener propósito
    SELECT id INTO v_purpose_id FROM data_processing_purposes WHERE code = 'call_recording' LIMIT 1;

    -- Consentimiento del contacto 2 (diferente)
    -- Crear consent_version primero
    INSERT INTO consent_versions (purpose_id, version, effective_from, consent_text, consent_text_hash)
    VALUES (v_purpose_id, '1.0', CURRENT_TIMESTAMP, 'Test consent text', encode(sha256('Test consent text'::bytea), 'hex'))
    ON CONFLICT DO NOTHING;
    
    SELECT id INTO v_consent_version_id FROM consent_versions WHERE purpose_id = v_purpose_id LIMIT 1;
    
    INSERT INTO data_consents (
        data_subject_id, data_subject_type, purpose_id, consent_version_id, consent_given, obtained_method,
        ip_address
    )
    VALUES (
        v_contact2_id, 'contact', v_purpose_id, v_consent_version_id, true, 'explicit_verbal',
        '127.0.0.1'::INET
    )
    RETURNING id INTO v_consent_other_id;

    -- Intentar vincular consentimiento de otro contacto (debe fallar)
    BEGIN
        INSERT INTO call_processing_consents (
            call_id, purpose_id, consent_id, retention_until
        )
        VALUES (
            v_call_id, v_purpose_id, v_consent_other_id,
            CURRENT_DATE + INTERVAL '90 days'
        );
    EXCEPTION WHEN OTHERS THEN
        v_error_raised := true;
    END;

    IF v_error_raised THEN
        v_status := 'PASS';
        v_details := 'Correctly rejected consent from different contact';
    ELSE
        v_status := 'FAIL';
        v_details := 'Should have rejected consent from different contact';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Consent Ownership Validation', 'Call_Processing', v_status, v_details);

    RAISE NOTICE '  [%] Ownership: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Consent Ownership Validation', 'Call_Processing', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Ownership: Exception - %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 15.3: Retención automática según propósito
-- ============================================================================

\echo ''
\echo '--- Test 15.3: Calculo de retencion automatica ---'

DO $$
DECLARE
    v_user_id UUID;
    v_contact_id UUID;
    v_call_id UUID;
    v_purpose_id UUID;
    v_consent_id UUID;
    v_consent_version_id UUID;
    v_retention_days INTEGER;
    v_actual_retention DATE;
    v_expected_retention DATE;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_CPC_RET', 'cpc_ret_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Crear contacto
    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_user_id,
        encrypt_pii_with_metadata('Retention Test'),
        encrypt_pii_with_metadata('+34600000003'),
        (secure_hash_with_pepper('+34600000003')).hash
    )
    RETURNING id INTO v_contact_id;

    -- Obtener propósito y su período de retención
    SELECT id, retention_period_days INTO v_purpose_id, v_retention_days
    FROM data_processing_purposes WHERE code = 'call_recording' LIMIT 1;

    -- Crear llamada
    INSERT INTO calls (
        user_id, contact_id, call_date, call_time, caller_name_encrypted, caller_phone_encrypted,
        caller_phone_hash, call_timestamp, duration_seconds, status, recording_encrypted
    )
    VALUES (
        v_user_id, v_contact_id, CURRENT_DATE, CURRENT_TIME,
        encrypt_pii_with_metadata('Retention Test'),
        encrypt_pii_with_metadata('+34600000003'),
        (secure_hash_with_pepper('+34600000003')).hash,
        CURRENT_TIMESTAMP, 90, 'completed', false
    )
    RETURNING id INTO v_call_id;

    -- Crear consentimiento
    -- Crear consent_version primero
    INSERT INTO consent_versions (purpose_id, version, effective_from, consent_text, consent_text_hash)
    VALUES (v_purpose_id, '1.0', CURRENT_TIMESTAMP, 'Test consent text', encode(sha256('Test consent text'::bytea), 'hex'))
    ON CONFLICT DO NOTHING;
    
    SELECT id INTO v_consent_version_id FROM consent_versions WHERE purpose_id = v_purpose_id LIMIT 1;
    
    INSERT INTO data_consents (
        data_subject_id, data_subject_type, purpose_id, consent_version_id, consent_given, obtained_method,
        ip_address
    )
    VALUES (
        v_contact_id, 'contact', v_purpose_id, v_consent_version_id, true, 'explicit_verbal',
        '127.0.0.1'::INET
    )
    RETURNING id INTO v_consent_id;

    -- Calcular retención esperada
    v_expected_retention := CURRENT_DATE + (v_retention_days || ' days')::INTERVAL;

    -- Crear call_processing_consent con retención calculada
    INSERT INTO call_processing_consents (
        call_id, purpose_id, consent_id, retention_until
    )
    VALUES (
        v_call_id, v_purpose_id, v_consent_id, v_expected_retention
    );

    -- Verificar
    SELECT retention_until INTO v_actual_retention
    FROM call_processing_consents
    WHERE call_id = v_call_id AND purpose_id = v_purpose_id;

    IF v_actual_retention = v_expected_retention THEN
        v_status := 'PASS';
        v_details := format('Retention correctly set to %s days from today (%s)', v_retention_days, v_actual_retention);
    ELSE
        v_status := 'FAIL';
        v_details := format('Retention mismatch: expected %s, got %s', v_expected_retention, v_actual_retention);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Retention Period Calculation', 'Call_Processing', v_status, v_details);

    RAISE NOTICE '  [%] Retention: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Retention Period Calculation', 'Call_Processing', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Retention: Exception - %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 15.4: Indices de rendimiento
-- ============================================================================

\echo ''
\echo '--- Test 15.4: Indices de rendimiento ---'

DO $$
DECLARE
    v_idx_call BOOLEAN;
    v_idx_purpose BOOLEAN;
    v_idx_consent BOOLEAN;
    v_idx_retention BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Verificar índices
    SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE indexname = 'idx_call_processing_call') INTO v_idx_call;
    SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE indexname = 'idx_call_processing_purpose') INTO v_idx_purpose;
    SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE indexname = 'idx_call_processing_consent') INTO v_idx_consent;
    SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE indexname = 'idx_call_processing_retention') INTO v_idx_retention;

    IF v_idx_call AND v_idx_purpose AND v_idx_consent AND v_idx_retention THEN
        v_status := 'PASS';
        v_details := 'All performance indexes exist';
    ELSE
        v_status := 'FAIL';
        v_details := format('Missing indexes - call:%s purpose:%s consent:%s retention:%s',
            v_idx_call, v_idx_purpose, v_idx_consent, v_idx_retention);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Performance Indexes', 'Call_Processing', v_status, v_details);

    RAISE NOTICE '  [%] Indexes: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Performance Indexes', 'Call_Processing', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 15.5: Cascade delete cuando se elimina la llamada
-- ============================================================================

\echo ''
\echo '--- Test 15.5: Cascade delete con llamada ---'

DO $$
DECLARE
    v_user_id UUID;
    v_contact_id UUID;
    v_call_id UUID;
    v_purpose_id UUID;
    v_consent_id UUID;
    v_consent_version_id UUID;
    v_cpc_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_CASCADE', 'cascade_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Crear contacto
    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_user_id,
        encrypt_pii_with_metadata('Cascade Test'),
        encrypt_pii_with_metadata('+34600000004'),
        (secure_hash_with_pepper('+34600000004')).hash
    )
    RETURNING id INTO v_contact_id;

    -- Obtener propósito
    SELECT id INTO v_purpose_id FROM data_processing_purposes WHERE code = 'call_recording' LIMIT 1;

    -- Crear llamada
    INSERT INTO calls (
        user_id, contact_id, call_date, call_time, caller_name_encrypted, caller_phone_encrypted,
        caller_phone_hash, call_timestamp, duration_seconds, status, recording_encrypted
    )
    VALUES (
        v_user_id, v_contact_id, CURRENT_DATE, CURRENT_TIME,
        encrypt_pii_with_metadata('Cascade Test'),
        encrypt_pii_with_metadata('+34600000004'),
        (secure_hash_with_pepper('+34600000004')).hash,
        CURRENT_TIMESTAMP, 45, 'completed', false
    )
    RETURNING id INTO v_call_id;

    -- Crear consentimiento
    -- Crear consent_version primero
    INSERT INTO consent_versions (purpose_id, version, effective_from, consent_text, consent_text_hash)
    VALUES (v_purpose_id, '1.0', CURRENT_TIMESTAMP, 'Test consent text', encode(sha256('Test consent text'::bytea), 'hex'))
    ON CONFLICT DO NOTHING;
    
    SELECT id INTO v_consent_version_id FROM consent_versions WHERE purpose_id = v_purpose_id LIMIT 1;
    
    INSERT INTO data_consents (
        data_subject_id, data_subject_type, purpose_id, consent_version_id, consent_given, obtained_method,
        ip_address
    )
    VALUES (
        v_contact_id, 'contact', v_purpose_id, v_consent_version_id, true, 'explicit_written',
        '127.0.0.1'::INET
    )
    RETURNING id INTO v_consent_id;

    -- Crear call_processing_consent
    INSERT INTO call_processing_consents (
        call_id, purpose_id, consent_id, retention_until
    )
    VALUES (
        v_call_id, v_purpose_id, v_consent_id,
        CURRENT_DATE + INTERVAL '90 days'
    );

    -- Eliminar llamada
    DELETE FROM calls WHERE id = v_call_id;

    -- Verificar que call_processing_consent se eliminó
    SELECT EXISTS(
        SELECT 1 FROM call_processing_consents WHERE call_id = v_call_id
    ) INTO v_cpc_exists;

    IF NOT v_cpc_exists THEN
        v_status := 'PASS';
        v_details := 'call_processing_consent correctly deleted on call deletion';
    ELSE
        v_status := 'FAIL';
        v_details := 'call_processing_consent orphaned after call deletion';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Cascade Delete', 'Call_Processing', v_status, v_details);

    RAISE NOTICE '  [%] Cascade: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Cascade Delete', 'Call_Processing', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Cascade: Exception - %', SQLERRM;
END $$;

-- ============================================================================
-- RESUMEN DE RESULTADOS
-- ============================================================================

\echo ''
\echo '=============================================='
\echo 'RESUMEN TEST 15: CALL_PROCESSING_CONSENTS'
\echo '=============================================='

SELECT
    test_category,
    COUNT(*) as total_tests,
    COUNT(*) FILTER (WHERE status = 'PASS') as passed,
    COUNT(*) FILTER (WHERE status = 'FAIL') as failed,
    COUNT(*) FILTER (WHERE status = 'SKIP') as skipped
FROM test_results
WHERE test_category = 'Call_Processing'
GROUP BY test_category;

SELECT test_name, status, details
FROM test_results
WHERE test_category = 'Call_Processing'
ORDER BY test_id;

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
