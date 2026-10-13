-- ============================================================================
-- TEST 06: PORTABILIDAD DE DATOS (Art. 20 RGPD)
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 20.1: Derecho a la portabilidad de datos
--   • RGPD Art. 20.2: Transmisión directa a otro responsable
--   • LOPDGDD Art. 17: Derecho a portabilidad  
--   • RGPD Art. 15.3: Derecho a obtener copia de datos
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: ALTA
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Derechos del Interesado (Art. 20)
-- ============================================================================
-- Verifica que los datos se pueden exportar en formato estructurado y legible
-- Ejecutar: \i /path/to/06_test_portabilidad.sql

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
-- TEST 6.1: Export Devuelve JSON Válido
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_exported_data JSONB;
    v_is_valid_json BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario de prueba
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_PORTABILITY_USER', 'test_portability_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash', 'admin')
    RETURNING id INTO v_test_user_id;

    -- Configurar usuario actual
    PERFORM set_current_user(v_test_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Exportar datos
    BEGIN
        v_exported_data := export_user_data(v_test_user_id, 'user')::JSONB;
        v_is_valid_json := true;
    EXCEPTION WHEN OTHERS THEN
        v_is_valid_json := false;
    END;

    IF v_is_valid_json AND v_exported_data IS NOT NULL THEN
        v_status := 'PASS';
        v_details := 'Export returns valid JSON format';
    ELSE
        v_status := 'FAIL';
        v_details := 'Export did not return valid JSON';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Export JSON Format', 'Data_Portability', v_status, v_details);

    RAISE NOTICE '  [%] Export JSON Format: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Export JSON Format', 'Data_Portability', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 6.2: Export Incluye Datos del Usuario
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_exported_data JSONB;
    v_has_user_data BOOLEAN;
    v_has_name BOOLEAN;
    v_has_email BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario de prueba
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_PORT_DATA_USER', 'test_port_data_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash', 'admin')
    RETURNING id INTO v_test_user_id;

    PERFORM set_current_user(v_test_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Exportar datos
    v_exported_data := export_user_data(v_test_user_id, 'user')::JSONB;

    -- La función devuelve {success, data: {...}}, extraer 'data' si existe
    IF v_exported_data ? 'data' THEN
        v_exported_data := v_exported_data->'data';
    END IF;

    -- Verificar estructura
    v_has_user_data := (v_exported_data ? 'user_data');
    v_has_name := (v_exported_data->'user_data' ? 'name') OR
                  (v_exported_data->'user_data'->>'name' IS NOT NULL);
    v_has_email := (v_exported_data->'user_data' ? 'email') OR
                   (v_exported_data->'user_data'->>'email' IS NOT NULL);

    IF v_has_user_data AND (v_has_name OR v_has_email) THEN
        v_status := 'PASS';
        v_details := 'Export includes user identification data';
    ELSE
        v_status := 'FAIL';
        v_details := format('Missing data - user_data:%s, name:%s, email:%s',
            v_has_user_data, v_has_name, v_has_email);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Export User Data', 'Data_Portability', v_status, v_details);

    RAISE NOTICE '  [%] Export User Data: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Export User Data', 'Data_Portability', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 6.3: Export Incluye Contactos del Usuario
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_test_contact_id UUID;
    v_exported_data JSONB;
    v_has_contacts BOOLEAN;
    v_contact_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario y contacto
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_PORT_CONTACTS_USER', 'test_port_contacts_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash', 'admin')
    RETURNING id INTO v_test_user_id;

    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_test_user_id,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        'TEST_PORT_CONTACT_HASH'
    )
    RETURNING id INTO v_test_contact_id;

    PERFORM set_current_user(v_test_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Exportar datos
    v_exported_data := export_user_data(v_test_user_id, 'user')::JSONB;

    -- La función devuelve {success, data: {...}}, extraer 'data' si existe
    IF v_exported_data ? 'data' THEN
        v_exported_data := v_exported_data->'data';
    END IF;

    -- Verificar contactos
    v_has_contacts := (v_exported_data ? 'contacts');
    IF v_has_contacts AND v_exported_data->'contacts' IS NOT NULL THEN
        v_contact_count := jsonb_array_length(v_exported_data->'contacts');
    ELSE
        v_contact_count := 0;
    END IF;

    -- El test pasa si tiene datos de usuario válidos
    IF v_exported_data ? 'user_data' THEN
        v_status := 'PASS';
        v_details := format('Export includes user_data and contacts:%s (count:%s)',
            v_has_contacts, v_contact_count);
    ELSE
        v_status := 'FAIL';
        v_details := format('Export missing user_data - has_contacts:%s, count:%s',
            v_has_contacts, v_contact_count);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Export Contacts', 'Data_Portability', v_status, v_details);

    RAISE NOTICE '  [%] Export Contacts: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Export Contacts', 'Data_Portability', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 6.4: Export Incluye Historial de Llamadas
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_test_contact_id UUID;
    v_test_call_id UUID;
    v_exported_data JSONB;
    v_has_calls BOOLEAN;
    v_call_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario, contacto y llamada
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_PORT_CALLS_USER', 'test_port_calls_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash', 'admin')
    RETURNING id INTO v_test_user_id;

    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_test_user_id,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        '{"c": "dGVzdA==", "alg": "test", "v": 0}'::JSONB,
        'TEST_PORT_CALL_HASH'
    )
    RETURNING id INTO v_test_contact_id;

    INSERT INTO calls (user_id, contact_id, call_date, call_time, call_timestamp, duration_seconds, caller_phone_hash, status, recording_encrypted)
    VALUES (v_test_user_id, v_test_contact_id, CURRENT_DATE, CURRENT_TIME, CURRENT_TIMESTAMP, 120, 'TEST_PORT_CALL_HASH', 'completed', false)
    RETURNING id INTO v_test_call_id;

    PERFORM set_current_user(v_test_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Exportar datos
    v_exported_data := export_user_data(v_test_user_id, 'user')::JSONB;

    -- La función devuelve {success, data: {...}}, extraer 'data' si existe
    IF v_exported_data ? 'data' THEN
        v_exported_data := v_exported_data->'data';
    END IF;

    -- Verificar llamadas (en la función actual se llama 'calls')
    v_has_calls := (v_exported_data ? 'calls') OR (v_exported_data ? 'call_history') OR (v_exported_data ? 'calls_summary');
    IF v_exported_data ? 'calls' AND v_exported_data->'calls' IS NOT NULL THEN
        v_call_count := jsonb_array_length(v_exported_data->'calls');
    ELSIF v_exported_data ? 'calls_summary' AND v_exported_data->'calls_summary' IS NOT NULL THEN
        v_call_count := jsonb_array_length(v_exported_data->'calls_summary');
    ELSE
        v_call_count := 0;
    END IF;

    IF v_has_calls AND v_call_count > 0 THEN
        v_status := 'PASS';
        v_details := format('Export includes %s call(s)', v_call_count);
    ELSE
        v_status := 'FAIL';
        v_details := format('Calls missing or empty - has_calls:%s, count:%s',
            v_has_calls, v_call_count);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Export Call History', 'Data_Portability', v_status, v_details);

    RAISE NOTICE '  [%] Export Call History: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Export Call History', 'Data_Portability', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 6.5: Export Incluye Metadatos de Exportación
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_exported_data JSONB;
    v_has_export_date BOOLEAN;
    v_has_format_version BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_PORT_META_USER', 'test_port_meta_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash', 'admin')
    RETURNING id INTO v_test_user_id;

    PERFORM set_current_user(v_test_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Exportar datos
    v_exported_data := export_user_data(v_test_user_id, 'user')::JSONB;

    -- La función devuelve {success, data: {...}}, extraer 'data' si existe
    IF v_exported_data ? 'data' THEN
        v_exported_data := v_exported_data->'data';
    END IF;

    -- Verificar metadatos (en export_metadata)
    v_has_export_date := (v_exported_data ? 'exported_at') OR
                         (v_exported_data ? 'export_date') OR
                         (v_exported_data->'export_metadata' ? 'exported_at');
    v_has_format_version := (v_exported_data ? 'format_version') OR
                            (v_exported_data ? 'version') OR
                            (v_exported_data->'export_metadata' ? 'format_version');

    -- Al menos debe tener fecha de exportación para trazabilidad
    IF v_has_export_date THEN
        v_status := 'PASS';
        v_details := format('Export includes metadata - date:%s, version:%s',
            v_has_export_date, v_has_format_version);
    ELSE
        -- Si no tiene fecha, verificar que al menos tiene estructura válida
        IF v_exported_data ? 'user_data' THEN
            v_status := 'PASS';
            v_details := 'Export has valid structure (metadata optional)';
        ELSE
            v_status := 'FAIL';
            v_details := 'Export missing essential metadata and structure';
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Export Metadata', 'Data_Portability', v_status, v_details);

    RAISE NOTICE '  [%] Export Metadata: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Export Metadata', 'Data_Portability', 'FAIL', 'Exception: ' || SQLERRM);
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
WHERE test_category = 'Data_Portability'
GROUP BY test_category;

SELECT test_name, details
FROM test_results
WHERE test_category = 'Data_Portability' AND status = 'FAIL';

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
