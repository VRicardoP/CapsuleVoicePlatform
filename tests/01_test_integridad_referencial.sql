-- ============================================================================
-- TEST 01: INTEGRIDAD REFERENCIAL
-- ============================================================================
-- COBERTURA LEGAL:
--   • Integridad de Base de Datos (general)
--   • No verifica compliance legal específico
--   • Fundamento técnico necesario para garantizar RGPD Art. 32.1.b
--     (integridad de los datos y sistemas de tratamiento)
-- 
-- NIVEL DE COMPLIANCE: N/A (test técnico de infraestructura)
-- CRITICIDAD: ALTA (base para funcionamiento correcto de otros tests)
-- REQUISITOS NORMATIVA.MD: Soporte indirecto para PARTE 1 (RGPD) - Art. 32
-- ============================================================================
-- Verifica constraints, foreign keys, cascadas y validaciones de datos
-- Ejecutar: \i /path/to/01_test_integridad_referencial.sql

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

-- Tabla para almacenar resultados
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
-- TEST 1.1: Verificar Foreign Keys Existen
-- ============================================================================

DO $$
DECLARE
    v_expected_fks TEXT[] := ARRAY[
        'users',
        'user_sessions.user_id -> users.id',
        'user_preferences.user_id -> users.id',
        'contacts.user_id -> users.id',
        'calls.user_id -> users.id',
        'calls.contact_id -> contacts.id',
        'transcriptions.call_id -> calls.id',
        'automated_actions.call_id -> calls.id',
        'automated_actions.user_id -> users.id',
        'campaigns.user_id -> users.id',
        'conversions.call_id -> calls.id',
        'conversions.user_id -> users.id',
        'data_consents.purpose_id -> data_processing_purposes.id',
        'data_consents.consent_version_id -> consent_versions.id',
        'user_consents.user_id -> users.id',
        'user_consents.consent_id -> data_consents.id',
        'contact_consents.contact_id -> contacts.id',
        'contact_consents.consent_id -> data_consents.id',
        'contacts.call_recording_consent_id -> data_consents.id',
        'contacts.data_processing_consent_id -> data_consents.id',
        'calls.recording_consent_id -> data_consents.id',
        'call_processing_consents.call_id -> calls.id',
        'call_processing_consents.purpose_id -> data_processing_purposes.id',
        'call_processing_consents.consent_id -> data_consents.id'
    ];
    v_fk_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(DISTINCT conname)::INTEGER INTO v_fk_count
    FROM pg_constraint
    WHERE contype = 'f'
        AND connamespace = 'public'::regnamespace;

    IF v_fk_count >= 20 THEN
        v_status := 'PASS';
        v_details := format('Found %s foreign keys (expected >= 20)', v_fk_count);
    ELSE
        v_status := 'FAIL';
        v_details := format('Found only %s foreign keys (expected >= 20)', v_fk_count);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Foreign Keys Exist', 'Integrity', v_status, v_details);
    
    RAISE NOTICE '  [%] Foreign Keys: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 1.2: Verificar Cascadas de Eliminación
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_test_contact_id UUID;
    v_test_call_id UUID;
    v_recording_purpose_id UUID;
    v_analytics_purpose_id UUID;
    v_recording_consent_id UUID;
    v_analytics_consent_id UUID;
    v_recording_version_id UUID;
    v_analytics_version_id UUID;
    v_calls_deleted BOOLEAN;
    v_sessions_deleted BOOLEAN;
    v_contacts_deleted BOOLEAN;
    v_transcriptions_deleted BOOLEAN;
BEGIN
    -- Obtener propósitos existentes
    SELECT id INTO v_recording_purpose_id FROM data_processing_purposes WHERE code = 'call_recording';
    SELECT id INTO v_analytics_purpose_id FROM data_processing_purposes WHERE code = 'call_analytics';

    -- Crear usuario de prueba
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_USER_CASCADE', 'test_cascade_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash', 'user')
    RETURNING id INTO v_test_user_id;

    -- Crear versiones de consentimiento para los propósitos existentes
    INSERT INTO consent_versions (purpose_id, version, consent_text, consent_text_hash, effective_from)
    VALUES (v_recording_purpose_id, 'test_1.0', 'Test consent for recording', 'hash_recording_test', CURRENT_TIMESTAMP)
    RETURNING id INTO v_recording_version_id;

    INSERT INTO consent_versions (purpose_id, version, consent_text, consent_text_hash, effective_from)
    VALUES (v_analytics_purpose_id, 'test_1.0', 'Test consent for analytics', 'hash_analytics_test', CURRENT_TIMESTAMP)
    RETURNING id INTO v_analytics_version_id;

    -- Crear contacto de prueba primero (sin consentimientos)
    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_test_user_id,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        'TEST_HASH_CASCADE'
    )
    RETURNING id INTO v_test_contact_id;

    -- Crear consentimiento de grabación asociado al contacto
    INSERT INTO data_consents (
        data_subject_id, data_subject_type, purpose_id, consent_version_id,
        consent_given, obtained_at, obtained_method, evidence_type, evidence_reference
    )
    VALUES (
        v_test_contact_id, 'contact', v_recording_purpose_id, v_recording_version_id, true,
        CURRENT_TIMESTAMP, 'web_form', 'form_submission', 'TEST_RECORDING_EVIDENCE'
    )
    RETURNING id INTO v_recording_consent_id;

    -- Crear consentimiento de procesamiento asociado al contacto
    INSERT INTO data_consents (
        data_subject_id, data_subject_type, purpose_id, consent_version_id,
        consent_given, obtained_at, obtained_method, evidence_type, evidence_reference
    )
    VALUES (
        v_test_contact_id, 'contact', v_analytics_purpose_id, v_analytics_version_id, true,
        CURRENT_TIMESTAMP, 'web_form', 'form_submission', 'TEST_ANALYTICS_EVIDENCE'
    )
    RETURNING id INTO v_analytics_consent_id;

    -- Actualizar contacto con los consentimientos
    UPDATE contacts SET
        call_recording_consent_id = v_recording_consent_id,
        data_processing_consent_id = v_analytics_consent_id
    WHERE id = v_test_contact_id;

    -- Crear llamada de prueba (sin grabación encriptada para evitar validación adicional)
    INSERT INTO calls (user_id, contact_id, call_date, call_time, call_timestamp,
                       duration_seconds, caller_phone_hash, status, recording_encrypted)
    VALUES (
        v_test_user_id,
        v_test_contact_id,
        CURRENT_DATE,
        CURRENT_TIME,
        CURRENT_TIMESTAMP,
        100,
        'TEST_HASH_CASCADE',
        'completed',
        false
    )
    RETURNING id INTO v_test_call_id;

    -- Crear transcripción de prueba
    INSERT INTO transcriptions (call_id, segment_timestamp, sequence_number, speaker, text_encrypted)
    VALUES (
        v_test_call_id,
        CURRENT_TIMESTAMP,
        1,
        'assistant',
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB
    );

    -- Crear sesión de prueba
    INSERT INTO user_sessions (user_id, token_hash, expires_at, ip_address)
    VALUES (
        v_test_user_id,
        'TEST_TOKEN_HASH_CASCADE',
        CURRENT_TIMESTAMP + INTERVAL '1 hour',
        '127.0.0.1'::INET
    );

    -- ELIMINAR USUARIO (debe cascadear)
    DELETE FROM users WHERE id = v_test_user_id;

    -- Verificar cascadas
    v_calls_deleted := NOT EXISTS(SELECT 1 FROM calls WHERE id = v_test_call_id);
    v_sessions_deleted := NOT EXISTS(SELECT 1 FROM user_sessions WHERE user_id = v_test_user_id);
    v_contacts_deleted := NOT EXISTS(SELECT 1 FROM contacts WHERE id = v_test_contact_id);
    v_transcriptions_deleted := NOT EXISTS(SELECT 1 FROM transcriptions WHERE call_id = v_test_call_id);

    -- Limpiar datos de prueba (primero consentimientos, luego versiones)
    DELETE FROM data_consents WHERE id IN (v_recording_consent_id, v_analytics_consent_id);
    DELETE FROM consent_versions WHERE id IN (v_recording_version_id, v_analytics_version_id);

    IF v_calls_deleted AND v_sessions_deleted AND v_contacts_deleted AND v_transcriptions_deleted THEN
        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('ON DELETE CASCADE', 'Integrity', 'PASS', 'All cascades work correctly');
        RAISE NOTICE '  [PASS] ON DELETE CASCADE: All cascades work correctly';
    ELSE
        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('ON DELETE CASCADE', 'Integrity', 'FAIL', format('Cascades failed - calls:%s, sessions:%s, contacts:%s, transcriptions:%s',
            v_calls_deleted, v_sessions_deleted, v_contacts_deleted, v_transcriptions_deleted));
        RAISE NOTICE '  [FAIL] ON DELETE CASCADE: Some cascades did not work';
    END IF;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('ON DELETE CASCADE', 'Integrity', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] ON DELETE CASCADE: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 1.3: Verificar CHECK Constraints
-- ============================================================================

DO $$
DECLARE
    v_check_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(*)::INTEGER INTO v_check_count
    FROM pg_constraint
    WHERE contype = 'c'
        AND connamespace = 'public'::regnamespace
        AND conname NOT LIKE '%_not_null';

    IF v_check_count >= 30 THEN
        v_status := 'PASS';
        v_details := format('Found %s CHECK constraints (expected >= 30)', v_check_count);
    ELSE
        v_status := 'FAIL';
        v_details := format('Found only %s CHECK constraints (expected >= 30)', v_check_count);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('CHECK Constraints Exist', 'Integrity', v_status, v_details);
    
    RAISE NOTICE '  [%] CHECK Constraints: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 1.4: Verificar Email Validation
-- ============================================================================

DO $$
DECLARE
    v_invalid_email_rejected BOOLEAN := false;
BEGIN
    BEGIN
        INSERT INTO users (name, email, password_hash)
        VALUES ('TEST_INVALID_EMAIL', 'invalid-email', 'test_hash');
    EXCEPTION WHEN check_violation THEN
        v_invalid_email_rejected := true;
    END;

    IF v_invalid_email_rejected THEN
        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('Email Validation', 'Integrity', 'PASS', 'Invalid email correctly rejected');
        RAISE NOTICE '  [PASS] Email Validation: Invalid email correctly rejected';
    ELSE
        DELETE FROM users WHERE email = 'invalid-email';
        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('Email Validation', 'Integrity', 'FAIL', 'Invalid email was accepted');
        RAISE NOTICE '  [FAIL] Email Validation: Invalid email was accepted';
    END IF;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Email Validation', 'Integrity', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 1.5: Verificar UNIQUE Constraints
-- ============================================================================

DO $$
DECLARE
    v_duplicate_rejected BOOLEAN := false;
    v_test_user_id UUID;
    v_test_email TEXT;
BEGIN
    -- Generar email único para este test
    v_test_email := 'test_unique_' || gen_random_uuid()::TEXT || '@test.local';

    -- Crear usuario
    INSERT INTO users (name, email, password_hash)
    VALUES ('TEST_UNIQUE_1', v_test_email, 'test_hash')
    RETURNING id INTO v_test_user_id;

    -- Intentar duplicar MISMO email (debe fallar)
    BEGIN
        INSERT INTO users (name, email, password_hash)
        VALUES ('TEST_UNIQUE_2', v_test_email, 'test_hash');
    EXCEPTION WHEN unique_violation THEN
        v_duplicate_rejected := true;
    END;

    IF v_duplicate_rejected THEN
        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('UNIQUE Constraints', 'Integrity', 'PASS', 'Duplicate email correctly rejected');
        RAISE NOTICE '  [PASS] UNIQUE Constraints: Duplicate email correctly rejected';
    ELSE
        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('UNIQUE Constraints', 'Integrity', 'FAIL', 'Duplicate email was accepted');
        RAISE NOTICE '  [FAIL] UNIQUE Constraints: Duplicate email was accepted';
    END IF;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('UNIQUE Constraints', 'Integrity', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 1.6: Verificar NOT NULL Constraints en Campos Críticos
-- ============================================================================

DO $$
DECLARE
    v_null_rejected BOOLEAN := false;
BEGIN
    BEGIN
        INSERT INTO users (name, email, password_hash)
        VALUES ('TEST_NULL', NULL, 'test_hash');
    EXCEPTION WHEN not_null_violation THEN
        v_null_rejected := true;
    END;

    IF v_null_rejected THEN
        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('NOT NULL Constraints', 'Integrity', 'PASS', 'NULL email correctly rejected');
        RAISE NOTICE '  [PASS] NOT NULL Constraints: NULL email correctly rejected';
    ELSE
        DELETE FROM users WHERE name = 'TEST_NULL';
        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('NOT NULL Constraints', 'Integrity', 'FAIL', 'NULL email was accepted');
        RAISE NOTICE '  [FAIL] NOT NULL Constraints: NULL email was accepted';
    END IF;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('NOT NULL Constraints', 'Integrity', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 1.7: Verificar Índice Único de Clave Activa
-- ============================================================================

DO $$
DECLARE
    v_index_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'public'
            AND indexname = 'idx_single_active_key'
    ) INTO v_index_exists;

    IF v_index_exists THEN
        v_status := 'PASS';
        v_details := 'Unique index on active encryption key exists';
    ELSE
        v_status := 'FAIL';
        v_details := 'Missing unique index idx_single_active_key';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Active Key Unique Index', 'Integrity', v_status, v_details);
    
    RAISE NOTICE '  [%] Active Key Index: %', v_status, v_details;
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
WHERE test_category = 'Integrity'
GROUP BY test_category;

SELECT test_name, details
FROM test_results
WHERE test_category = 'Integrity' AND status = 'FAIL';


-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
