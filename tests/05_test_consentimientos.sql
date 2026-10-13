-- ============================================================================
-- TEST 05: SISTEMA DE CONSENTIMIENTOS
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 6.1.a: Consentimiento del interesado como base jurídica
--   • RGPD Art. 7: Condiciones para el consentimiento
--   • RGPD Art. 7.1: Demostración del consentimiento (prueba)
--   • RGPD Art. 7.3: Derecho a retirar el consentimiento fácilmente
--   • LOPDGDD Art. 6: Consentimiento inequívoco (acción afirmativa clara)
--   • LOPDGDD Art. 6.3: Conservar prueba del consentimiento otorgado
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: CRÍTICA (base jurídica fundamental)
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Bases Jurídicas (Art. 6-7)
--                          PARTE 2 (LOPDGDD) - Disposiciones Generales (Art. 6)
-- ============================================================================
-- Verifica el sistema completo de consentimientos RGPD
-- Ejecutar: \i /path/to/05_test_consentimientos.sql

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


-- Configurar variables de sesión para tests
SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';
SET app.hash_pepper = 'TEST_PEPPER_V1_FOR_HMAC_FUNCTIONS';
SET app.hash_pepper_version = '1';
SET app.audit_hmac_key = 'TEST_AUDIT_KEY_FOR_HMAC_CHAIN__';

-- ============================================================================
-- TEST 5.1: Registro de Consentimiento con Evidencia Completa
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_test_contact_id UUID;
    v_consent_id UUID;
    v_consent_version_id UUID;
    v_purpose_id UUID;
    v_has_evidence BOOLEAN;
    v_has_hash BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario de prueba
    INSERT INTO users (name, email, password_hash)
    VALUES ('TEST_USER_CONSENT', 'test_consent_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash')
    RETURNING id INTO v_test_user_id;

    -- Crear contacto de prueba
    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_test_user_id,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        'TEST_CONSENT_HASH'
    )
    RETURNING id INTO v_test_contact_id;

    -- Obtener purpose
    SELECT id INTO v_purpose_id
    FROM data_processing_purposes
    WHERE code = 'call_recording'
    LIMIT 1;

    -- Crear versión de consentimiento
    INSERT INTO consent_versions (purpose_id, version, consent_text, consent_text_hash)
    VALUES (
        v_purpose_id,
        'v1_' || LEFT(gen_random_uuid()::TEXT, 10),
        'Texto de consentimiento de prueba',
        encode(digest('Texto de consentimiento de prueba', 'sha256'), 'hex')
    )
    RETURNING id INTO v_consent_version_id;

    -- Crear consentimiento con evidencia completa
    INSERT INTO data_consents (
        data_subject_id,
        data_subject_type,
        purpose_id,
        consent_version_id,
        consent_given,
        obtained_method,
        evidence_type,
        evidence_reference,
        evidence_hash
    )
    VALUES (
        v_test_contact_id,
        'contact',
        v_purpose_id,
        v_consent_version_id,
        true,
        'explicit_verbal',
        'audio_recording',
        '/recordings/test_consent_001.wav',
        encode(digest('test_recording_content', 'sha256'), 'hex')
    )
    RETURNING id INTO v_consent_id;

    -- Verificar evidencia
    SELECT
        evidence_reference IS NOT NULL AND evidence_hash IS NOT NULL
    INTO v_has_evidence
    FROM data_consents
    WHERE id = v_consent_id;

    IF v_has_evidence THEN
        v_status := 'PASS';
        v_details := 'Consent created with complete evidence (reference + hash)';
    ELSE
        v_status := 'FAIL';
        v_details := 'Consent missing evidence fields';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Consent with Evidence', 'GDPR_Consent', v_status, v_details);
    
    RAISE NOTICE '  [%] Consent with Evidence: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Consent with Evidence', 'GDPR_Consent', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 5.2: Validación de Ownership de Consentimiento
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_contact_1_id UUID;
    v_contact_2_id UUID;
    v_consent_id UUID;
    v_purpose_id UUID;
    v_consent_version_id UUID;
    v_invalid_ownership_rejected BOOLEAN := false;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario y dos contactos
    INSERT INTO users (name, email, password_hash)
    VALUES ('TEST_USER_OWN', 'test_ownership_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash')
    RETURNING id INTO v_test_user_id;

    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_test_user_id,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        'TEST_CONTACT_1_HASH'
    )
    RETURNING id INTO v_contact_1_id;

    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_test_user_id,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        'TEST_CONTACT_2_HASH'
    )
    RETURNING id INTO v_contact_2_id;

    -- Obtener purpose y version
    SELECT id INTO v_purpose_id FROM data_processing_purposes WHERE code = 'call_recording' LIMIT 1;
    
    INSERT INTO consent_versions (purpose_id, version, consent_text, consent_text_hash)
    VALUES (v_purpose_id, 'v2_' || LEFT(gen_random_uuid()::TEXT, 10), 'Test', encode(digest('Test', 'sha256'), 'hex'))
    RETURNING id INTO v_consent_version_id;

    -- Crear consentimiento para contact_1
    INSERT INTO data_consents (
        data_subject_id, data_subject_type, purpose_id, consent_version_id, consent_given, obtained_method
    )
    VALUES (v_contact_1_id, 'contact', v_purpose_id, v_consent_version_id, true, 'web_form')
    RETURNING id INTO v_consent_id;

    -- Intentar asignar consent de contact_1 a contact_2 (debe fallar)
    BEGIN
        UPDATE contacts
        SET call_recording_consent_id = v_consent_id
        WHERE id = v_contact_2_id;
        -- Si llegamos aquí, no se rechazó
        v_invalid_ownership_rejected := false;
    EXCEPTION WHEN OTHERS THEN
        v_invalid_ownership_rejected := (SQLERRM LIKE '%must belong to%contact%');
    END;

    IF v_invalid_ownership_rejected THEN
        v_status := 'PASS';
        v_details := 'Invalid consent ownership correctly rejected';
    ELSE
        v_status := 'FAIL';
        v_details := 'Invalid consent ownership was accepted';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Consent Ownership Validation', 'GDPR_Consent', v_status, v_details);
    
    RAISE NOTICE '  [%] Consent Ownership: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Consent Ownership Validation', 'GDPR_Consent', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 5.3: Caducidad de Consentimientos
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_test_contact_id UUID;
    v_consent_expired_id UUID;
    v_consent_valid_id UUID;
    v_purpose_id UUID;
    v_consent_version_id UUID;
    v_expired_rejected BOOLEAN := false;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario y contacto
    INSERT INTO users (name, email, password_hash)
    VALUES ('TEST_USER_EXP', 'test_expiry_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash')
    RETURNING id INTO v_test_user_id;

    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_test_user_id,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        'TEST_EXPIRY_HASH'
    )
    RETURNING id INTO v_test_contact_id;

    -- Obtener purpose y version
    SELECT id INTO v_purpose_id FROM data_processing_purposes WHERE code = 'call_recording' LIMIT 1;
    
    INSERT INTO consent_versions (purpose_id, version, consent_text, consent_text_hash)
    VALUES (v_purpose_id, 'v3_' || LEFT(gen_random_uuid()::TEXT, 10), 'Test', encode(digest('Test', 'sha256'), 'hex'))
    RETURNING id INTO v_consent_version_id;

    -- Crear consentimiento EXPIRADO
    INSERT INTO data_consents (
        data_subject_id,
        data_subject_type,
        purpose_id,
        consent_version_id,
        consent_given,
        obtained_method,
        expires_at
    )
    VALUES (
        v_test_contact_id,
        'contact',
        v_purpose_id,
        v_consent_version_id,
        true,
        'web_form',
        CURRENT_TIMESTAMP - INTERVAL '1 day'  -- Expirado ayer
    )
    RETURNING id INTO v_consent_expired_id;

    -- Intentar asignar consent expirado (debe fallar)
    BEGIN
        UPDATE contacts
        SET call_recording_consent_id = v_consent_expired_id
        WHERE id = v_test_contact_id;
        -- Si llegamos aquí, no se rechazó
        v_expired_rejected := false;
    EXCEPTION WHEN OTHERS THEN
        v_expired_rejected := (SQLERRM LIKE '%expired%');
    END;

    IF v_expired_rejected THEN
        v_status := 'PASS';
        v_details := 'Expired consent correctly rejected';
    ELSE
        v_status := 'FAIL';
        v_details := 'Expired consent was accepted';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Consent Expiry Validation', 'GDPR_Consent', v_status, v_details);
    
    RAISE NOTICE '  [%] Consent Expiry: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Consent Expiry Validation', 'GDPR_Consent', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 5.4: Grabaciones Requieren Consent Válido
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_test_contact_id UUID;
    v_test_call_id UUID;
    v_recording_without_consent_rejected BOOLEAN := false;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario y contacto
    INSERT INTO users (name, email, password_hash)
    VALUES ('TEST_USER_REC', 'test_recording_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash')
    RETURNING id INTO v_test_user_id;

    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_test_user_id,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        'TEST_REC_HASH'
    )
    RETURNING id INTO v_test_contact_id;

    -- Intentar crear llamada CON recording_url pero SIN recording_consent_id (debe fallar)
    BEGIN
        INSERT INTO calls (
            user_id,
            contact_id,
            call_date,
            call_time,
            call_timestamp,
            duration_seconds,
            caller_phone_hash,
            status,
            recording_url  -- SIN consent!
        )
        VALUES (
            v_test_user_id,
            v_test_contact_id,
            CURRENT_DATE,
            CURRENT_TIME,
            CURRENT_TIMESTAMP,
            100,
            'TEST_REC_HASH',
            'completed',
            'https://example.com/recording.wav'
        );
    EXCEPTION WHEN OTHERS THEN
        v_recording_without_consent_rejected := (
            SQLERRM LIKE '%without recording_consent_id%' OR
            SQLERRM LIKE '%require%consent%'
        );
    END;

    IF v_recording_without_consent_rejected THEN
        v_status := 'PASS';
        v_details := 'Recording without consent correctly rejected';
    ELSE
        v_status := 'FAIL';
        v_details := 'Recording without consent was accepted';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Recording Requires Consent', 'GDPR_Consent', v_status, v_details);
    
    RAISE NOTICE '  [%] Recording Requires Consent: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Recording Requires Consent', 'GDPR_Consent', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 5.5: Revocación de Consentimientos
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_test_contact_id UUID;
    v_consent_id UUID;
    v_purpose_id UUID;
    v_consent_version_id UUID;
    v_revoked_rejected BOOLEAN := false;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario y contacto
    INSERT INTO users (name, email, password_hash)
    VALUES ('TEST_USER_REV', 'test_revoke_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash')
    RETURNING id INTO v_test_user_id;

    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_test_user_id,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        'TEST_REV_HASH'
    )
    RETURNING id INTO v_test_contact_id;

    -- Crear consentimiento
    SELECT id INTO v_purpose_id FROM data_processing_purposes WHERE code = 'call_recording' LIMIT 1;
    
    INSERT INTO consent_versions (purpose_id, version, consent_text, consent_text_hash)
    VALUES (v_purpose_id, 'v4_' || LEFT(gen_random_uuid()::TEXT, 10), 'Test', encode(digest('Test', 'sha256'), 'hex'))
    RETURNING id INTO v_consent_version_id;

    INSERT INTO data_consents (
        data_subject_id, data_subject_type, purpose_id, consent_version_id, consent_given, obtained_method
    )
    VALUES (v_test_contact_id, 'contact', v_purpose_id, v_consent_version_id, true, 'web_form')
    RETURNING id INTO v_consent_id;

    -- REVOCAR consentimiento
    UPDATE data_consents
    SET revoked_at = CURRENT_TIMESTAMP,
        revoked_reason = 'User requested revocation',
        revoked_method = 'email'
    WHERE id = v_consent_id;

    -- Intentar usar consent revocado (debe fallar)
    BEGIN
        UPDATE contacts
        SET call_recording_consent_id = v_consent_id
        WHERE id = v_test_contact_id;
        -- Si llegamos aquí, no se rechazó
        v_revoked_rejected := false;
    EXCEPTION WHEN OTHERS THEN
        v_revoked_rejected := (SQLERRM LIKE '%revoked%');
    END;

    IF v_revoked_rejected THEN
        v_status := 'PASS';
        v_details := 'Revoked consent correctly rejected';
    ELSE
        v_status := 'FAIL';
        v_details := 'Revoked consent was accepted';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Consent Revocation', 'GDPR_Consent', v_status, v_details);
    
    RAISE NOTICE '  [%] Consent Revocation: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Consent Revocation', 'GDPR_Consent', 'FAIL', 'Exception: ' || SQLERRM);
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
WHERE test_category = 'GDPR_Consent'
GROUP BY test_category;

SELECT test_name, details
FROM test_results
WHERE test_category = 'GDPR_Consent' AND status = 'FAIL';


-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
