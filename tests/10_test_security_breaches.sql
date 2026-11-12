-- ============================================================================
-- TEST 10: SISTEMA DE BRECHAS DE SEGURIDAD (Art. 33-34 RGPD)
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 33: Notificación brechas a autoridad de control
--   • RGPD Art. 34: Comunicación brechas a interesados
--   • RGPD Art. 34.3.a: Excepción si datos cifrados
--   • RGPD Art. 32: Seguridad del tratamiento
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: CRÍTICA
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Arts. 32-34
-- ============================================================================
-- Valida la implementación completa del sistema de notificación de brechas:
--   - Tabla security_breaches y sus constraints
--   - Tabla breach_affected_subjects
--   - Tabla breach_notifications
--   - Funciones: register_security_breach, notify_authority_breach, etc.
--   - Cálculo automático de plazos (72 horas)
--   - Determinación de notificación a interesados
--
-- Ejecutar: psql -U postgres -d capsule -f 10_test_security_breaches.sql
-- ============================================================================

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo ''
\echo '============================================================================'
\echo 'TEST 10: SISTEMA DE BRECHAS DE SEGURIDAD (Art. 33-34 RGPD)'
\echo '============================================================================'
\echo ''

-- Crear tabla temporal para resultados
CREATE TEMP TABLE IF NOT EXISTS test_results (
    test_id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    test_category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Limpiar resultados anteriores de esta categoría
DELETE FROM test_results WHERE test_category = 'Security_Breaches';

-- Configurar variables de sesión para tests
SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';
SET app.hash_pepper = 'TEST_PEPPER_V1_FOR_HMAC_FUNCTIONS';
SET app.hash_pepper_version = '1';
SET app.audit_hmac_key = 'TEST_AUDIT_KEY_FOR_HMAC_CHAIN__';

-- Variable para almacenar IDs de prueba
DO $$ BEGIN PERFORM set_config('test.admin_user_id', '', false); END $$;
DO $$ BEGIN PERFORM set_config('test.breach_id', '', false); END $$;
DO $$ BEGIN PERFORM set_config('test.contact_id', '', false); END $$;

-- ============================================================================
-- SETUP: Crear clave de cifrado de prueba y usuario admin
-- ============================================================================

DO $$
DECLARE
    v_admin_id UUID;
    v_key_exists BOOLEAN;
BEGIN
    -- Verificar si ya existe una clave activa
    SELECT EXISTS(SELECT 1 FROM encryption_keys WHERE is_active = true) INTO v_key_exists;

    -- Crear clave de cifrado de prueba si no existe
    IF NOT v_key_exists THEN
        INSERT INTO encryption_keys (
            key_id,
            encrypted_key,
            algorithm,
            key_version,
            is_active,
            kms_provider,
            kms_key_id
        ) VALUES (
            'test_key_' || gen_random_uuid()::TEXT,
            pgp_sym_encrypt(
                gen_random_bytes(32)::TEXT,
                current_setting('app.kms_master_key'),
                'cipher-algo=aes256'
            ),
            'aes-256-cbc',
            1,
            true,
            'test',
            'test-key-id'
        );
        RAISE NOTICE 'Setup: Clave de cifrado de prueba creada';
    END IF;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Setup: Error creando clave de cifrado (ignorado): %', SQLERRM;
END $$;

DO $$
DECLARE
    v_admin_id UUID;
BEGIN
    -- Crear usuario admin de prueba
    INSERT INTO users (name, email, password_hash, password_algorithm, role, is_active)
    VALUES (
        'TEST_BREACH_ADMIN',
        'test_breach_admin_' || gen_random_uuid()::TEXT || '@test.local',
        'test_hash',
        'bcrypt',
        'admin',
        true
    )
    RETURNING id INTO v_admin_id;

    PERFORM set_config('test.admin_user_id', v_admin_id::TEXT, false);
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    RAISE NOTICE 'Setup: Usuario admin de prueba creado: %', v_admin_id;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Setup FAILED: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 10.1: Verificar existencia de tablas de brechas
-- ============================================================================

\echo '  [TEST 10.1] Verificar existencia de tablas de brechas'

DO $$
DECLARE
    v_tables_exist BOOLEAN;
    v_missing_tables TEXT[];
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Verificar las 3 tablas principales
    SELECT
        ARRAY_AGG(t.table_name) FILTER (WHERE NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = t.table_name
        ))
    INTO v_missing_tables
    FROM (VALUES
        ('security_breaches'),
        ('breach_affected_subjects'),
        ('breach_notifications')
    ) AS t(table_name);

    IF v_missing_tables IS NULL OR array_length(v_missing_tables, 1) IS NULL THEN
        v_status := 'PASS';
        v_details := 'Todas las tablas de brechas existen: security_breaches, breach_affected_subjects, breach_notifications';
    ELSE
        v_status := 'FAIL';
        v_details := 'Tablas faltantes: ' || array_to_string(v_missing_tables, ', ');
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Tables Existence', 'Security_Breaches', v_status, v_details);

    RAISE NOTICE '    [%] Tables Existence: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 10.2: Verificar constraints de breach_type
-- ============================================================================

\echo '  [TEST 10.2] Verificar constraints de breach_type'

DO $$
DECLARE
    v_valid_types_work BOOLEAN := true;
    v_invalid_blocked BOOLEAN := false;
    v_status TEXT;
    v_details TEXT;
    v_admin_id UUID;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;

    -- Intentar insertar tipo inválido
    BEGIN
        INSERT INTO security_breaches (
            breach_reference, breach_title, breach_description,
            breach_type, severity, risk_level, detected_at,
            authority_notification_deadline
        ) VALUES (
            'TEST-INVALID-TYPE',
            'Test Invalid Type',
            'Testing invalid breach type',
            'invalid_type',  -- Tipo inválido
            'low',
            'unlikely',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP + INTERVAL '72 hours'
        );
    EXCEPTION WHEN check_violation THEN
        v_invalid_blocked := true;
    END;

    IF v_invalid_blocked THEN
        v_status := 'PASS';
        v_details := 'Constraint breach_type funciona correctamente (rechaza tipos inválidos)';
    ELSE
        v_status := 'FAIL';
        v_details := 'Constraint breach_type NO bloquea tipos inválidos';
        -- Limpiar registro inválido si se insertó
        DELETE FROM security_breaches WHERE breach_reference = 'TEST-INVALID-TYPE';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Breach Type Constraint', 'Security_Breaches', v_status, v_details);

    RAISE NOTICE '    [%] Breach Type Constraint: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 10.3: Función register_security_breach() - Registro básico
-- ============================================================================

\echo '  [TEST 10.3] Función register_security_breach() - Registro básico'

DO $$
DECLARE
    v_result JSON;
    v_breach_id UUID;
    v_breach_ref TEXT;
    v_deadline TIMESTAMP WITH TIME ZONE;
    v_hours_remaining NUMERIC;
    v_status TEXT;
    v_details TEXT;
    v_admin_id UUID;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    -- Registrar brecha
    SELECT register_security_breach(
        'Acceso no autorizado a base de datos',
        'Se detectó acceso desde IP externa no autorizada a la tabla contacts',
        'confidentiality',
        'high',
        'likely',
        CURRENT_TIMESTAMP,
        ARRAY['email', 'phone', 'name'],
        false,
        150
    ) INTO v_result;

    -- Extraer valores
    v_breach_id := (v_result->>'breach_id')::UUID;
    v_breach_ref := v_result->>'breach_reference';
    v_deadline := (v_result->>'authority_deadline')::TIMESTAMP WITH TIME ZONE;
    v_hours_remaining := (v_result->>'hours_remaining')::NUMERIC;

    -- Guardar para tests posteriores
    PERFORM set_config('test.breach_id', v_breach_id::TEXT, false);

    -- Validar resultado
    IF v_breach_id IS NOT NULL
       AND v_breach_ref LIKE 'BREACH-%-___'
       AND v_hours_remaining BETWEEN 71 AND 73  -- Aproximadamente 72 horas
    THEN
        v_status := 'PASS';
        v_details := format('Brecha registrada: %s, deadline: %s, horas restantes: %s',
            v_breach_ref, v_deadline, ROUND(v_hours_remaining, 1));
    ELSE
        v_status := 'FAIL';
        v_details := format('Error en registro - ID: %s, Ref: %s, Horas: %s',
            v_breach_id, v_breach_ref, v_hours_remaining);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Register Breach Function', 'Security_Breaches', v_status, v_details);

    RAISE NOTICE '    [%] Register Breach Function: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Register Breach Function', 'Security_Breaches', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Register Breach Function: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 10.4: Cálculo automático de deadline 72 horas (Art. 33.1)
-- ============================================================================

\echo '  [TEST 10.4] Cálculo automático de deadline 72 horas (Art. 33.1)'

DO $$
DECLARE
    v_breach_id UUID;
    v_detected_at TIMESTAMP WITH TIME ZONE;
    v_deadline TIMESTAMP WITH TIME ZONE;
    v_diff_hours NUMERIC;
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_breach_id := current_setting('test.breach_id')::UUID;

    SELECT detected_at, authority_notification_deadline
    INTO v_detected_at, v_deadline
    FROM security_breaches
    WHERE id = v_breach_id;

    v_diff_hours := EXTRACT(EPOCH FROM (v_deadline - v_detected_at)) / 3600;

    IF v_diff_hours = 72 THEN
        v_status := 'PASS';
        v_details := format('Deadline calculado correctamente: %s horas desde detección', v_diff_hours);
    ELSE
        v_status := 'FAIL';
        v_details := format('Deadline incorrecto: %s horas (esperado: 72)', v_diff_hours);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('72h Deadline Calculation', 'Security_Breaches', v_status, v_details);

    RAISE NOTICE '    [%] 72h Deadline Calculation: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('72h Deadline Calculation', 'Security_Breaches', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] 72h Deadline Calculation: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 10.5: Determinación automática de notificación a interesados (Art. 34.1)
-- ============================================================================

\echo '  [TEST 10.5] Determinación automática de notificación a interesados (Art. 34.1)'

DO $$
DECLARE
    v_result_high JSON;
    v_result_low JSON;
    v_high_requires_notification BOOLEAN;
    v_low_requires_notification BOOLEAN;
    v_status TEXT;
    v_details TEXT;
    v_admin_id UUID;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    -- Brecha con riesgo alto -> DEBE requerir notificación
    SELECT register_security_breach(
        'Test High Risk Breach',
        'Testing high risk determination',
        'confidentiality',
        'critical',
        'high',  -- Riesgo alto
        CURRENT_TIMESTAMP,
        ARRAY['financial', 'health'],
        true,  -- Categorías especiales
        500
    ) INTO v_result_high;

    v_high_requires_notification := (v_result_high->>'users_notification_required')::BOOLEAN;

    -- Brecha con riesgo bajo -> NO debe requerir notificación
    SELECT register_security_breach(
        'Test Low Risk Breach',
        'Testing low risk determination',
        'availability',
        'low',
        'unlikely',  -- Riesgo improbable
        CURRENT_TIMESTAMP,
        ARRAY['name'],
        false,  -- Sin categorías especiales
        5
    ) INTO v_result_low;

    v_low_requires_notification := (v_result_low->>'users_notification_required')::BOOLEAN;

    IF v_high_requires_notification = true AND v_low_requires_notification = false THEN
        v_status := 'PASS';
        v_details := 'Determinación correcta: riesgo alto=notificar, riesgo bajo=no notificar';
    ELSE
        v_status := 'FAIL';
        v_details := format('Determinación incorrecta: alto=%s (esperado: true), bajo=%s (esperado: false)',
            v_high_requires_notification, v_low_requires_notification);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('User Notification Determination', 'Security_Breaches', v_status, v_details);

    RAISE NOTICE '    [%] User Notification Determination: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('User Notification Determination', 'Security_Breaches', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] User Notification Determination: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 10.6: Añadir sujetos afectados (add_breach_affected_subjects)
-- ============================================================================

\echo '  [TEST 10.6] Añadir sujetos afectados (add_breach_affected_subjects)'

DO $$
DECLARE
    v_breach_id UUID;
    v_contact_ids UUID[];
    v_contact_id UUID;
    v_result JSON;
    v_subjects_added INTEGER;
    v_total_affected INTEGER;
    v_status TEXT;
    v_details TEXT;
    v_admin_id UUID;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    v_breach_id := current_setting('test.breach_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    -- Crear contactos de prueba
    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES
        (v_admin_id, '{"c": "test1"}'::JSONB, '{"c": "phone1"}'::JSONB, 'hash1_' || gen_random_uuid());
    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES
        (v_admin_id, '{"c": "test2"}'::JSONB, '{"c": "phone2"}'::JSONB, 'hash2_' || gen_random_uuid());
    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES
        (v_admin_id, '{"c": "test3"}'::JSONB, '{"c": "phone3"}'::JSONB, 'hash3_' || gen_random_uuid())
    RETURNING id INTO v_contact_id;

    -- Obtener IDs de contactos creados
    SELECT ARRAY_AGG(id) INTO v_contact_ids
    FROM contacts
    WHERE user_id = v_admin_id
    LIMIT 3;

    -- Guardar un contact_id para tests posteriores
    PERFORM set_config('test.contact_id', v_contact_ids[1]::TEXT, false);

    -- Añadir sujetos afectados
    SELECT add_breach_affected_subjects(
        v_breach_id,
        v_contact_ids,
        'contact',
        ARRAY['email', 'phone']
    ) INTO v_result;

    v_subjects_added := (v_result->>'subjects_added')::INTEGER;
    v_total_affected := (v_result->>'total_affected')::INTEGER;

    IF v_subjects_added >= 1 AND v_total_affected >= 1 THEN
        v_status := 'PASS';
        v_details := format('Sujetos añadidos: %s, total afectados: %s', v_subjects_added, v_total_affected);
    ELSE
        v_status := 'FAIL';
        v_details := format('Error añadiendo sujetos - añadidos: %s, total: %s', v_subjects_added, v_total_affected);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Add Affected Subjects', 'Security_Breaches', v_status, v_details);

    RAISE NOTICE '    [%] Add Affected Subjects: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Add Affected Subjects', 'Security_Breaches', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Add Affected Subjects: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 10.7: Actualización de affected_records_count
-- ============================================================================

\echo '  [TEST 10.7] Actualización de affected_records_count'

DO $$
DECLARE
    v_breach_id UUID;
    v_count_in_breach INTEGER;
    v_count_in_subjects INTEGER;
    v_is_estimated BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_breach_id := current_setting('test.breach_id')::UUID;

    -- Obtener conteos
    SELECT affected_records_count, affected_records_estimated
    INTO v_count_in_breach, v_is_estimated
    FROM security_breaches
    WHERE id = v_breach_id;

    SELECT COUNT(*)
    INTO v_count_in_subjects
    FROM breach_affected_subjects
    WHERE breach_id = v_breach_id;

    IF v_count_in_breach = v_count_in_subjects AND v_is_estimated = false THEN
        v_status := 'PASS';
        v_details := format('Conteo sincronizado: %s afectados, estimated=%s', v_count_in_breach, v_is_estimated);
    ELSE
        v_status := 'FAIL';
        v_details := format('Desincronización: breach=%s, subjects=%s, estimated=%s',
            v_count_in_breach, v_count_in_subjects, v_is_estimated);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Affected Count Sync', 'Security_Breaches', v_status, v_details);

    RAISE NOTICE '    [%] Affected Count Sync: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Affected Count Sync', 'Security_Breaches', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Affected Count Sync: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 10.8: Notificación a autoridad (notify_authority_breach)
-- ============================================================================

\echo '  [TEST 10.8] Notificación a autoridad (notify_authority_breach)'

DO $$
DECLARE
    v_breach_id UUID;
    v_result JSON;
    v_success BOOLEAN;
    v_within_deadline BOOLEAN;
    v_notification_id UUID;
    v_status TEXT;
    v_details TEXT;
    v_admin_id UUID;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    v_breach_id := current_setting('test.breach_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    -- Notificar a autoridad
    SELECT notify_authority_breach(
        v_breach_id,
        'DPO Test <dpo@test.local> - Tel: +34 600 000 000',
        'Posible uso fraudulento de datos personales de contactos',
        'Revocación de accesos, rotación de credenciales, auditoría de seguridad',
        'AEPD-2025-TEST-001'
    ) INTO v_result;

    v_success := (v_result->>'success')::BOOLEAN;
    v_within_deadline := (v_result->>'within_deadline')::BOOLEAN;
    v_notification_id := (v_result->>'notification_id')::UUID;

    IF v_success = true AND v_within_deadline = true AND v_notification_id IS NOT NULL THEN
        v_status := 'PASS';
        v_details := format('Notificación exitosa: ID=%s, dentro de plazo=%s', v_notification_id, v_within_deadline);
    ELSE
        v_status := 'FAIL';
        v_details := format('Error en notificación: success=%s, deadline=%s, id=%s',
            v_success, v_within_deadline, v_notification_id);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Notify Authority', 'Security_Breaches', v_status, v_details);

    RAISE NOTICE '    [%] Notify Authority: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Notify Authority', 'Security_Breaches', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Notify Authority: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 10.9: Registro de notificación en breach_notifications
-- ============================================================================

\echo '  [TEST 10.9] Registro de notificación en breach_notifications'

DO $$
DECLARE
    v_breach_id UUID;
    v_notification RECORD;
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_breach_id := current_setting('test.breach_id')::UUID;

    SELECT *
    INTO v_notification
    FROM breach_notifications
    WHERE breach_id = v_breach_id
      AND notification_type = 'authority_initial'
    LIMIT 1;

    IF v_notification.id IS NOT NULL
       AND v_notification.includes_nature_of_breach = true
       AND v_notification.includes_dpo_contact = true
       AND v_notification.includes_likely_consequences = true
       AND v_notification.includes_measures_taken = true
    THEN
        v_status := 'PASS';
        v_details := format('Notificación registrada con todos los campos Art. 33.3: nature=%s, dpo=%s, consequences=%s, measures=%s',
            v_notification.includes_nature_of_breach,
            v_notification.includes_dpo_contact,
            v_notification.includes_likely_consequences,
            v_notification.includes_measures_taken);
    ELSE
        v_status := 'FAIL';
        v_details := 'Notificación incompleta o no encontrada';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Notification Record Art33.3', 'Security_Breaches', v_status, v_details);

    RAISE NOTICE '    [%] Notification Record Art33.3: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Notification Record Art33.3', 'Security_Breaches', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Notification Record Art33.3: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 10.10: Actualización de estado a 'authority_notified'
-- ============================================================================

\echo '  [TEST 10.10] Actualización de estado a authority_notified'

DO $$
DECLARE
    v_breach_id UUID;
    v_breach_status TEXT;
    v_authority_notified_at TIMESTAMP WITH TIME ZONE;
    v_authority_ref TEXT;
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_breach_id := current_setting('test.breach_id')::UUID;

    SELECT status, authority_notified_at, authority_notification_reference
    INTO v_breach_status, v_authority_notified_at, v_authority_ref
    FROM security_breaches
    WHERE id = v_breach_id;

    IF v_breach_status = 'authority_notified'
       AND v_authority_notified_at IS NOT NULL
       AND v_authority_ref = 'AEPD-2025-TEST-001'
    THEN
        v_status := 'PASS';
        v_details := format('Estado actualizado: %s, notificado: %s, ref: %s',
            v_breach_status, v_authority_notified_at, v_authority_ref);
    ELSE
        v_status := 'FAIL';
        v_details := format('Estado incorrecto: %s (esperado: authority_notified)', v_breach_status);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Status Update Authority', 'Security_Breaches', v_status, v_details);

    RAISE NOTICE '    [%] Status Update Authority: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Status Update Authority', 'Security_Breaches', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Status Update Authority: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 10.11: Bloqueo de doble notificación a autoridad
-- ============================================================================

\echo '  [TEST 10.11] Bloqueo de doble notificación a autoridad'

DO $$
DECLARE
    v_breach_id UUID;
    v_double_blocked BOOLEAN := false;
    v_status TEXT;
    v_details TEXT;
    v_admin_id UUID;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    v_breach_id := current_setting('test.breach_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    -- Intentar notificar de nuevo (debe fallar)
    BEGIN
        PERFORM notify_authority_breach(
            v_breach_id,
            'DPO Duplicate',
            'Test duplicate',
            'Test measures',
            'AEPD-DUPLICATE'
        );
    EXCEPTION WHEN OTHERS THEN
        v_double_blocked := true;
    END;

    IF v_double_blocked THEN
        v_status := 'PASS';
        v_details := 'Doble notificación correctamente bloqueada';
    ELSE
        v_status := 'FAIL';
        v_details := 'ERROR: Se permitió doble notificación a autoridad';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Double Notification Block', 'Security_Breaches', v_status, v_details);

    RAISE NOTICE '    [%] Double Notification Block: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Double Notification Block', 'Security_Breaches', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Double Notification Block: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 10.12: Función get_pending_breach_notifications()
-- ============================================================================

\echo '  [TEST 10.12] Función get_pending_breach_notifications()'

DO $$
DECLARE
    v_pending_count INTEGER;
    v_has_hours_field BOOLEAN;
    v_status TEXT;
    v_details TEXT;
    v_admin_id UUID;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    -- Contar brechas pendientes (las de test con riesgo alto/bajo)
    SELECT COUNT(*), bool_or(hours_until_deadline IS NOT NULL)
    INTO v_pending_count, v_has_hours_field
    FROM get_pending_breach_notifications();

    IF v_pending_count >= 0 AND v_has_hours_field IS NOT false THEN
        v_status := 'PASS';
        v_details := format('Función ejecutada correctamente: %s brechas pendientes, campo hours_until_deadline presente', v_pending_count);
    ELSE
        v_status := 'FAIL';
        v_details := 'Error ejecutando get_pending_breach_notifications()';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Get Pending Notifications', 'Security_Breaches', v_status, v_details);

    RAISE NOTICE '    [%] Get Pending Notifications: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Get Pending Notifications', 'Security_Breaches', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Get Pending Notifications: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 10.13: Vista v_security_breaches_dashboard
-- ============================================================================

\echo '  [TEST 10.13] Vista v_security_breaches_dashboard'

DO $$
DECLARE
    v_breach_id UUID;
    v_dashboard_record RECORD;
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_breach_id := current_setting('test.breach_id')::UUID;

    SELECT *
    INTO v_dashboard_record
    FROM v_security_breaches_dashboard
    WHERE id = v_breach_id;

    IF v_dashboard_record.id IS NOT NULL
       AND v_dashboard_record.authority_status IS NOT NULL
       AND v_dashboard_record.severity IS NOT NULL
    THEN
        v_status := 'PASS';
        v_details := format('Vista funcional: ref=%s, status=%s, authority_status=%s',
            v_dashboard_record.breach_reference,
            v_dashboard_record.status,
            v_dashboard_record.authority_status);
    ELSE
        v_status := 'FAIL';
        v_details := 'Vista v_security_breaches_dashboard no devuelve datos esperados';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Dashboard View', 'Security_Breaches', v_status, v_details);

    RAISE NOTICE '    [%] Dashboard View: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Dashboard View', 'Security_Breaches', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Dashboard View: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 10.14: Vista v_security_dashboard con métricas de brechas
-- ============================================================================

\echo '  [TEST 10.14] Vista v_security_dashboard con métricas de brechas'

DO $$
DECLARE
    v_dashboard RECORD;
    v_has_breach_fields BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT *
    INTO v_dashboard
    FROM v_security_dashboard
    LIMIT 1;

    -- Verificar que existen los nuevos campos de brechas
    v_has_breach_fields := (
        v_dashboard.active_breaches IS NOT NULL OR
        v_dashboard.overdue_breach_notifications IS NOT NULL OR
        v_dashboard.urgent_breach_notifications IS NOT NULL
    );

    IF v_has_breach_fields THEN
        v_status := 'PASS';
        v_details := format('Métricas de brechas: activas=%s, vencidas=%s, urgentes=%s',
            v_dashboard.active_breaches,
            v_dashboard.overdue_breach_notifications,
            v_dashboard.urgent_breach_notifications);
    ELSE
        v_status := 'FAIL';
        v_details := 'v_security_dashboard no incluye métricas de brechas';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Security Dashboard Metrics', 'Security_Breaches', v_status, v_details);

    RAISE NOTICE '    [%] Security Dashboard Metrics: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Security Dashboard Metrics', 'Security_Breaches', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Security Dashboard Metrics: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 10.15: RLS en tablas de brechas (solo admin/auditor)
-- ============================================================================

\echo '  [TEST 10.15] RLS en tablas de brechas (solo admin/auditor)'

DO $$
DECLARE
    v_rls_enabled_breaches BOOLEAN;
    v_rls_enabled_subjects BOOLEAN;
    v_rls_enabled_notifications BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Verificar RLS habilitado
    SELECT relrowsecurity INTO v_rls_enabled_breaches
    FROM pg_class WHERE relname = 'security_breaches';

    SELECT relrowsecurity INTO v_rls_enabled_subjects
    FROM pg_class WHERE relname = 'breach_affected_subjects';

    SELECT relrowsecurity INTO v_rls_enabled_notifications
    FROM pg_class WHERE relname = 'breach_notifications';

    IF v_rls_enabled_breaches AND v_rls_enabled_subjects AND v_rls_enabled_notifications THEN
        v_status := 'PASS';
        v_details := format('RLS habilitado: breaches=%s, subjects=%s, notifications=%s',
            v_rls_enabled_breaches, v_rls_enabled_subjects, v_rls_enabled_notifications);
    ELSE
        v_status := 'FAIL';
        v_details := format('RLS incompleto: breaches=%s, subjects=%s, notifications=%s',
            v_rls_enabled_breaches, v_rls_enabled_subjects, v_rls_enabled_notifications);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('RLS Enabled', 'Security_Breaches', v_status, v_details);

    RAISE NOTICE '    [%] RLS Enabled: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('RLS Enabled', 'Security_Breaches', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] RLS Enabled: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 10.16: Control de acceso - Usuario no admin rechazado
-- ============================================================================

\echo '  [TEST 10.16] Control de acceso - Usuario no admin rechazado'

DO $$
DECLARE
    v_regular_user_id UUID;
    v_access_denied BOOLEAN := false;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario regular (no admin)
    INSERT INTO users (name, email, password_hash, password_algorithm, role, is_active)
    VALUES (
        'TEST_REGULAR_USER',
        'test_regular_' || gen_random_uuid()::TEXT || '@test.local',
        'test_hash',
        'bcrypt',
        'user',  -- Rol regular, no admin
        true
    )
    RETURNING id INTO v_regular_user_id;

    -- Configurar como usuario actual
    PERFORM set_current_user(v_regular_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Intentar registrar brecha (debe fallar)
    BEGIN
        PERFORM register_security_breach(
            'Unauthorized Breach',
            'Test unauthorized access',
            'confidentiality',
            'low',
            'unlikely',
            CURRENT_TIMESTAMP,
            ARRAY['test'],
            false,
            1
        );
    EXCEPTION WHEN OTHERS THEN
        IF SQLERRM LIKE '%Access denied%' OR SQLERRM LIKE '%only admin%' THEN
            v_access_denied := true;
        END IF;
    END;

    IF v_access_denied THEN
        v_status := 'PASS';
        v_details := 'Acceso denegado correctamente a usuario no admin';
    ELSE
        v_status := 'FAIL';
        v_details := 'ERROR: Usuario no admin pudo registrar brecha';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Non-Admin Access Denied', 'Security_Breaches', v_status, v_details);

    RAISE NOTICE '    [%] Non-Admin Access Denied: %', v_status, v_details;

    -- Restaurar admin
    PERFORM set_current_user(current_setting('test.admin_user_id')::UUID, NULL::UUID, '127.0.0.1'::INET);

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Non-Admin Access Denied', 'Security_Breaches', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Non-Admin Access Denied: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 10.17: Registro en audit_log al crear brecha
-- ============================================================================

\echo '  [TEST 10.17] Registro en audit_log al crear brecha'

DO $$
DECLARE
    v_breach_id UUID;
    v_audit_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_breach_id := current_setting('test.breach_id')::UUID;

    SELECT EXISTS(
        SELECT 1 FROM audit_log
        WHERE entity_type = 'security_breach'
          AND entity_id = v_breach_id
          AND action = 'INSERT'
          AND severity = 'critical'
    ) INTO v_audit_exists;

    IF v_audit_exists THEN
        v_status := 'PASS';
        v_details := 'Brecha registrada en audit_log con severidad critical';
    ELSE
        v_status := 'FAIL';
        v_details := 'Brecha NO registrada en audit_log';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Audit Log Entry', 'Security_Breaches', v_status, v_details);

    RAISE NOTICE '    [%] Audit Log Entry: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Audit Log Entry', 'Security_Breaches', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Audit Log Entry: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 10.18: Índices de rendimiento
-- ============================================================================

\echo '  [TEST 10.18] Índices de rendimiento'

DO $$
DECLARE
    v_index_count INTEGER;
    v_expected_indexes TEXT[] := ARRAY[
        'idx_breaches_status',
        'idx_breaches_deadline',
        'idx_breaches_severity',
        'idx_breaches_reference',
        'idx_breach_subjects_breach',
        'idx_breach_notifications_breach'
    ];
    v_missing_indexes TEXT[];
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT ARRAY_AGG(idx_name)
    INTO v_missing_indexes
    FROM UNNEST(v_expected_indexes) AS idx_name
    WHERE NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = idx_name
    );

    IF v_missing_indexes IS NULL OR array_length(v_missing_indexes, 1) IS NULL THEN
        v_status := 'PASS';
        v_details := 'Todos los índices de rendimiento existen';
    ELSE
        v_status := 'FAIL';
        v_details := 'Índices faltantes: ' || array_to_string(v_missing_indexes, ', ');
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Performance Indexes', 'Security_Breaches', v_status, v_details);

    RAISE NOTICE '    [%] Performance Indexes: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Performance Indexes', 'Security_Breaches', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Performance Indexes: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 10.19: Generación de referencia única (BREACH-YYYY-NNN)
-- ============================================================================

\echo '  [TEST 10.19] Generación de referencia única (BREACH-YYYY-NNN)'

DO $$
DECLARE
    v_result1 JSON;
    v_result2 JSON;
    v_ref1 TEXT;
    v_ref2 TEXT;
    v_admin_id UUID;
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    -- Crear dos brechas más para verificar secuencia
    SELECT register_security_breach(
        'Test Sequence 1', 'Testing reference sequence', 'integrity',
        'low', 'unlikely', CURRENT_TIMESTAMP, ARRAY['test'], false, 1
    ) INTO v_result1;

    SELECT register_security_breach(
        'Test Sequence 2', 'Testing reference sequence', 'integrity',
        'low', 'unlikely', CURRENT_TIMESTAMP, ARRAY['test'], false, 1
    ) INTO v_result2;

    v_ref1 := v_result1->>'breach_reference';
    v_ref2 := v_result2->>'breach_reference';

    IF v_ref1 ~ '^BREACH-\d{4}-\d{3}$'
       AND v_ref2 ~ '^BREACH-\d{4}-\d{3}$'
       AND v_ref1 != v_ref2
    THEN
        v_status := 'PASS';
        v_details := format('Referencias únicas generadas: %s, %s', v_ref1, v_ref2);
    ELSE
        v_status := 'FAIL';
        v_details := format('Referencias inválidas o duplicadas: %s, %s', v_ref1, v_ref2);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Unique Reference Generation', 'Security_Breaches', v_status, v_details);

    RAISE NOTICE '    [%] Unique Reference Generation: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Unique Reference Generation', 'Security_Breaches', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Unique Reference Generation: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 10.20: Categorías especiales requieren notificación (Art. 9 + Art. 34)
-- ============================================================================

\echo '  [TEST 10.20] Categorías especiales requieren notificación (Art. 9 + Art. 34)'

DO $$
DECLARE
    v_result JSON;
    v_requires_notification BOOLEAN;
    v_admin_id UUID;
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    -- Brecha con categorías especiales (Art. 9) pero riesgo bajo
    -- Debe requerir notificación porque special_categories = true
    SELECT register_security_breach(
        'Test Special Categories',
        'Testing Art. 9 data breach',
        'confidentiality',
        'medium',
        'possible',  -- Riesgo NO alto
        CURRENT_TIMESTAMP,
        ARRAY['health', 'biometric'],  -- Categorías especiales
        true,  -- special_categories_affected = true
        10
    ) INTO v_result;

    v_requires_notification := (v_result->>'users_notification_required')::BOOLEAN;

    IF v_requires_notification = true THEN
        v_status := 'PASS';
        v_details := 'Datos sensibles (Art. 9) correctamente fuerzan notificación a interesados';
    ELSE
        v_status := 'FAIL';
        v_details := 'ERROR: Datos sensibles (Art. 9) NO activaron notificación obligatoria';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Special Categories Notification', 'Security_Breaches', v_status, v_details);

    RAISE NOTICE '    [%] Special Categories Notification: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Special Categories Notification', 'Security_Breaches', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Special Categories Notification: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- CLEANUP: Eliminar datos de prueba
-- ============================================================================

\echo ''
\echo '  [CLEANUP] Eliminando datos de prueba...'

DO $$
DECLARE
    v_admin_id UUID;
BEGIN
    v_admin_id := current_setting('test.admin_user_id', true)::UUID;

    IF v_admin_id IS NOT NULL THEN
        -- Eliminar en orden correcto (dependencias primero)
        -- NOTA: audit_log NO se puede borrar (inmutable por RGPD Art. 30)
        DELETE FROM breach_notifications WHERE breach_id IN (
            SELECT id FROM security_breaches WHERE detected_by = v_admin_id
        );
        DELETE FROM breach_affected_subjects WHERE breach_id IN (
            SELECT id FROM security_breaches WHERE detected_by = v_admin_id
        );
        DELETE FROM security_breaches WHERE detected_by = v_admin_id;
        DELETE FROM contacts WHERE user_id = v_admin_id;
        -- NO borrar audit_log - es inmutable por diseño RGPD
        DELETE FROM users WHERE id = v_admin_id;

        -- Eliminar usuarios de test adicionales
        DELETE FROM users WHERE email LIKE 'test_%@test.local';
    END IF;

    RAISE NOTICE '    Datos de prueba eliminados (audit_log preservado por RGPD)';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE '    Error en cleanup: %', SQLERRM;
END $$;

-- ============================================================================
-- RESUMEN DE RESULTADOS
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'RESUMEN DE RESULTADOS - TEST 10: SECURITY BREACHES'
\echo '============================================================================'

SELECT
    '  Total: ' || COUNT(*) || ' tests' AS summary,
    '  Passed: ' || COUNT(*) FILTER (WHERE status = 'PASS') AS passed,
    '  Failed: ' || COUNT(*) FILTER (WHERE status = 'FAIL') AS failed,
    '  Skipped: ' || COUNT(*) FILTER (WHERE status = 'SKIP') AS skipped
FROM test_results
WHERE test_category = 'Security_Breaches';

\echo ''
\echo 'Detalle de tests fallidos:'

SELECT '  - ' || test_name || ': ' || details AS failed_test
FROM test_results
WHERE test_category = 'Security_Breaches' AND status = 'FAIL';

\echo ''
\echo 'Detalle de todos los tests:'

SELECT
    CASE status
        WHEN 'PASS' THEN '  [✓] '
        WHEN 'FAIL' THEN '  [✗] '
        ELSE '  [~] '
    END || test_name || ': ' || COALESCE(LEFT(details, 80), 'N/A') AS test_result
FROM test_results
WHERE test_category = 'Security_Breaches'
ORDER BY test_id;

\echo ''
\echo '============================================================================'
\echo 'FIN TEST 10: SECURITY BREACHES (Art. 33-34 RGPD)'
\echo '============================================================================'

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
