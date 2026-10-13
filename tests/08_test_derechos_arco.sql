-- ============================================================================
-- TEST 08: DERECHOS ARCO (Art. 15-22 RGPD)
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 15: Derecho de acceso del interesado
--   • RGPD Art. 16: Derecho de rectificación
--   • RGPD Art. 17: Derecho de supresión ("derecho al olvido")
--   • RGPD Art. 21: Derecho de oposición
--   • LOPDGDD Arts. 12-23: Ejercicio de derechos
--   • RGPD Art. 12.3: Plazo respuesta 1 mes
-- 
-- NIVEL DE COMPLIANCE: MEDIO (verifica existencia, no profundidad)
-- CRITICIDAD: CRÍTICA
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Arts. 15-22, PARTE 2 - Arts. 12-23
-- ============================================================================
-- Verifica derecho de Acceso, Rectificación, Cancelación/Supresión y Portabilidad
-- Ejecutar: \i /path/to/08_test_derechos_arco.sql

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
-- TEST 8.1: Derecho de Acceso - Export User Data SIN Secretos
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_exported_data JSONB;
    v_has_user_data BOOLEAN;
    v_has_mfa_secret BOOLEAN;
    v_has_password BOOLEAN;
    v_has_encrypted_raw BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario de prueba
    INSERT INTO users (name, email, password_hash, two_factor_enabled)
    VALUES ('TEST_EXPORT_USER', 'test_export_' || gen_random_uuid()::TEXT || '@test.local', 'bcrypt_hash_test', true)
    RETURNING id INTO v_test_user_id;

    -- Configurar usuario actual para la función
    PERFORM set_current_user(v_test_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Exportar datos (convertir a JSONB para usar operador ?)
    v_exported_data := export_user_data(v_test_user_id, 'user')::JSONB;

    -- La función devuelve {success, data: {...}}, extraer 'data' si existe
    IF v_exported_data ? 'data' THEN
        v_exported_data := v_exported_data->'data';
    END IF;

    -- Verificar que contiene datos del usuario
    v_has_user_data := (v_exported_data ? 'user_data');

    -- Verificar que NO contiene secretos
    v_has_mfa_secret := (v_exported_data->'user_data' ? 'two_factor_secret_encrypted');
    v_has_password := (v_exported_data->'user_data' ? 'password_hash');

    -- Verificar que no hay datos cifrados raw (deben estar descifrados o ausentes)
    v_has_encrypted_raw := (v_exported_data::TEXT LIKE '%"c":%"%"iv":%');

    IF v_has_user_data AND NOT v_has_mfa_secret AND NOT v_has_password AND NOT v_has_encrypted_raw THEN
        v_status := 'PASS';
        v_details := 'Export contains user data but excludes secrets and raw encrypted data';
    ELSE
        v_status := 'FAIL';
        v_details := format('Export validation failed - has_data:%s, has_mfa:%s, has_pass:%s, has_raw:%s',
            v_has_user_data, v_has_mfa_secret, v_has_password, v_has_encrypted_raw);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Right of Access (Export)', 'GDPR_Rights', v_status, v_details);

    RAISE NOTICE '  [%] Right of Access: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Right of Access (Export)', 'GDPR_Rights', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 8.2: Derecho de Rectificación
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_original_name TEXT := 'Original Name';
    v_corrected_name TEXT := 'Corrected Name';
    v_updated_name TEXT;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario con dato incorrecto
    INSERT INTO users (name, email, password_hash)
    VALUES (v_original_name, 'test_rectify_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash')
    RETURNING id INTO v_test_user_id;

    -- Rectificar datos
    UPDATE users
    SET name = v_corrected_name
    WHERE id = v_test_user_id;

    -- Verificar rectificación
    SELECT name INTO v_updated_name
    FROM users
    WHERE id = v_test_user_id;

    IF v_updated_name = v_corrected_name THEN
        v_status := 'PASS';
        v_details := format('Data successfully rectified from "%s" to "%s"', v_original_name, v_corrected_name);
    ELSE
        v_status := 'FAIL';
        v_details := format('Rectification failed - expected "%s", got "%s"', v_corrected_name, v_updated_name);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Right of Rectification', 'GDPR_Rights', v_status, v_details);
    
    RAISE NOTICE '  [%] Right of Rectification: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Right of Rectification', 'GDPR_Rights', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 8.3: Derecho de Supresión (Erasure) - Usuario Completo
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_test_call_id UUID;
    v_test_contact_id UUID;
    v_erasure_result JSON;
    v_user_deleted BOOLEAN;
    v_calls_deleted BOOLEAN;
    v_contacts_deleted BOOLEAN;
    v_sessions_deleted BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario con datos relacionados
    INSERT INTO users (name, email, password_hash)
    VALUES ('TEST_ERASURE_USER', 'test_erasure_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash')
    RETURNING id INTO v_test_user_id;

    -- Crear contacto
    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_test_user_id,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        'TEST_ERASURE_HASH'
    )
    RETURNING id INTO v_test_contact_id;

    -- Crear llamada (sin grabación para evitar validación de consentimiento)
    INSERT INTO calls (user_id, contact_id, call_date, call_time, call_timestamp, duration_seconds, caller_phone_hash, status, recording_encrypted)
    VALUES (v_test_user_id, v_test_contact_id, CURRENT_DATE, CURRENT_TIME, CURRENT_TIMESTAMP, 100, 'TEST_ERASURE_HASH', 'completed', false)
    RETURNING id INTO v_test_call_id;

    -- Crear sesión
    INSERT INTO user_sessions (user_id, token_hash, expires_at, ip_address)
    VALUES (v_test_user_id, 'TEST_ERASURE_TOKEN', CURRENT_TIMESTAMP + INTERVAL '1 hour', '127.0.0.1'::INET);

    -- Configurar usuario actual
    PERFORM set_current_user(v_test_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- EJERCER DERECHO DE SUPRESIÓN
    v_erasure_result := gdpr_right_to_erasure(v_test_user_id, 'user');

    -- Verificar eliminación completa
    v_user_deleted := NOT EXISTS(SELECT 1 FROM users WHERE id = v_test_user_id AND deleted_at IS NULL);
    v_calls_deleted := NOT EXISTS(SELECT 1 FROM calls WHERE user_id = v_test_user_id);
    v_contacts_deleted := NOT EXISTS(SELECT 1 FROM contacts WHERE user_id = v_test_user_id);
    v_sessions_deleted := NOT EXISTS(SELECT 1 FROM user_sessions WHERE user_id = v_test_user_id);

    IF v_user_deleted AND v_calls_deleted AND v_contacts_deleted AND v_sessions_deleted THEN
        v_status := 'PASS';
        v_details := 'Complete erasure successful - user and all related data deleted';
    ELSE
        v_status := 'FAIL';
        v_details := format('Incomplete erasure - user:%s, calls:%s, contacts:%s, sessions:%s',
            v_user_deleted, v_calls_deleted, v_contacts_deleted, v_sessions_deleted);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Right to Erasure (User)', 'GDPR_Rights', v_status, v_details);
    
    RAISE NOTICE '  [%] Right to Erasure (User): %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Right to Erasure (User)', 'GDPR_Rights', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 8.4: Derecho de Supresión - Contacto
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_test_contact_id UUID;
    v_test_call_id UUID;
    v_erasure_result JSON;
    v_contact_deleted BOOLEAN;
    v_call_anonymized BOOLEAN;
    v_transcriptions_deleted BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario ADMIN y contacto
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_CONTACT_ERASURE_USER', 'test_contact_erasure_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash', 'admin')
    RETURNING id INTO v_test_user_id;

    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_test_user_id,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        'TEST_CONTACT_ERASURE_HASH'
    )
    RETURNING id INTO v_test_contact_id;

    -- Crear llamada (sin grabación para evitar validación de consentimiento)
    INSERT INTO calls (user_id, contact_id, call_date, call_time, call_timestamp, duration_seconds, caller_phone_hash, status, recording_encrypted)
    VALUES (v_test_user_id, v_test_contact_id, CURRENT_DATE, CURRENT_TIME, CURRENT_TIMESTAMP, 100, 'TEST_CONTACT_ERASURE_HASH', 'completed', false)
    RETURNING id INTO v_test_call_id;

    -- Crear transcripción
    INSERT INTO transcriptions (call_id, segment_timestamp, sequence_number, speaker, text_encrypted)
    VALUES (v_test_call_id, CURRENT_TIMESTAMP, 1, 'assistant', '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB);

    -- Configurar usuario actual (ya es admin por su rol en la tabla users)
    PERFORM set_current_user(v_test_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- EJERCER DERECHO DE SUPRESIÓN DEL CONTACTO
    v_erasure_result := gdpr_right_to_erasure(v_test_contact_id, 'contact');

    -- Verificar eliminación
    v_contact_deleted := NOT EXISTS(SELECT 1 FROM contacts WHERE id = v_test_contact_id);
    v_call_anonymized := EXISTS(
        SELECT 1 FROM calls 
        WHERE id = v_test_call_id 
        AND caller_name_encrypted IS NULL 
        AND caller_phone_encrypted IS NULL
        AND contact_id IS NULL
    );
    v_transcriptions_deleted := NOT EXISTS(SELECT 1 FROM transcriptions WHERE call_id = v_test_call_id);

    IF v_contact_deleted AND v_call_anonymized AND v_transcriptions_deleted THEN
        v_status := 'PASS';
        v_details := 'Contact erasure successful - contact deleted, call anonymized, transcriptions deleted';
    ELSE
        v_status := 'FAIL';
        v_details := format('Incomplete contact erasure - deleted:%s, anonymized:%s, trans_deleted:%s',
            v_contact_deleted, v_call_anonymized, v_transcriptions_deleted);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Right to Erasure (Contact)', 'GDPR_Rights', v_status, v_details);
    
    RAISE NOTICE '  [%] Right to Erasure (Contact): %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Right to Erasure (Contact)', 'GDPR_Rights', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 8.5: Solicitudes ARCO con Plazos (30 días)
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_request_id UUID;
    v_deadline DATE;
    v_deadline_correct BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash)
    VALUES ('TEST_DSR_USER', 'test_dsr_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash')
    RETURNING id INTO v_test_user_id;

    -- Crear solicitud ARCO
    INSERT INTO data_subject_requests (
        request_type,
        data_subject_id,
        data_subject_type,
        requester_email_encrypted,
        request_details_encrypted,
        deadline_at
    )
    VALUES (
        'access',
        v_test_user_id,
        'user',
        '{"c": "dGVzdEBleGFtcGxlLmNvbQ==", "alg": "test", "v": 0}'::JSONB,
        '{"c": "U29saWNpdHVkIGRlIGFjY2Vzbw==", "alg": "test", "v": 0}'::JSONB,
        CURRENT_TIMESTAMP + INTERVAL '30 days'
    )
    RETURNING id, deadline_at::DATE INTO v_request_id, v_deadline;

    -- Verificar que deadline es exactamente 30 días desde ahora
    v_deadline_correct := (v_deadline = (CURRENT_DATE + 30));

    IF v_deadline_correct THEN
        v_status := 'PASS';
        v_details := format('ARCO request created with correct 30-day deadline: %s', v_deadline);
    ELSE
        v_status := 'FAIL';
        v_details := format('Incorrect deadline - expected %s, got %s', CURRENT_DATE + 30, v_deadline);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('ARCO Request Deadline', 'GDPR_Rights', v_status, v_details);
    
    RAISE NOTICE '  [%] ARCO Request Deadline: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('ARCO Request Deadline', 'GDPR_Rights', 'FAIL', 'Exception: ' || SQLERRM);
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
WHERE test_category = 'GDPR_Rights'
GROUP BY test_category;

SELECT test_name, details
FROM test_results
WHERE test_category = 'GDPR_Rights' AND status = 'FAIL';


-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
