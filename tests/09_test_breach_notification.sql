-- ============================================================================
-- TEST 09: NOTIFICACION DE BRECHAS (Art. 33-34 RGPD)
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 33.1: Notificación brechas a autoridad en 72 horas
--   • RGPD Art. 33.3: Contenido de la notificación de brecha
--   • RGPD Art. 33.5: Documentar todas las brechas
--   • RGPD Art. 32: Seguridad del tratamiento (prevención)
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: CRÍTICA
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Brechas de Seguridad (Arts. 32-34)
-- ============================================================================
-- Verifica el sistema de registro y notificación de incidentes de seguridad
-- Ejecutar: \i /path/to/09_test_breach_notification.sql

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
-- TEST 9.1: Eventos de Seguridad se Registran en Audit Log
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_audit_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario de prueba
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_BREACH_USER', 'test_breach_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash', 'admin')
    RETURNING id INTO v_test_user_id;

    -- Configurar usuario actual
    PERFORM set_current_user(v_test_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Registrar evento de seguridad (usando acción válida del constraint)
    INSERT INTO audit_log (
        user_id, action, entity_type, entity_id,
        change_summary, ip_address, severity
    )
    VALUES (
        v_test_user_id,
        'FAILED_LOGIN',
        'security',
        v_test_user_id,
        'Failed login attempt detected',
        '192.168.1.100'::INET,
        'warning'
    );

    -- Verificar registro
    SELECT COUNT(*) INTO v_audit_count
    FROM audit_log
    WHERE action = 'FAILED_LOGIN'
    AND user_id = v_test_user_id;

    IF v_audit_count > 0 THEN
        v_status := 'PASS';
        v_details := format('Security event logged successfully (%s entries)', v_audit_count);
    ELSE
        v_status := 'FAIL';
        v_details := 'Security event not found in audit log';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Security Event Logging', 'Breach_Notification', v_status, v_details);

    RAISE NOTICE '  [%] Security Event Logging: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Security Event Logging', 'Breach_Notification', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 9.2: Severidad de Eventos (info, warning, error, critical)
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_severity_types TEXT[];
    v_all_severities_valid BOOLEAN := true;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_SEVERITY_USER', 'test_severity_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash', 'admin')
    RETURNING id INTO v_test_user_id;

    PERFORM set_current_user(v_test_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Registrar eventos con diferentes severidades (usando acciones válidas)
    BEGIN
        INSERT INTO audit_log (user_id, action, entity_type, entity_id, change_summary, ip_address, severity)
        VALUES (v_test_user_id, 'LOGIN', 'test', v_test_user_id, 'Info test', '127.0.0.1'::INET, 'info');

        INSERT INTO audit_log (user_id, action, entity_type, entity_id, change_summary, ip_address, severity)
        VALUES (v_test_user_id, 'FAILED_LOGIN', 'test', v_test_user_id, 'Warning test', '127.0.0.1'::INET, 'warning');

        INSERT INTO audit_log (user_id, action, entity_type, entity_id, change_summary, ip_address, severity)
        VALUES (v_test_user_id, 'RATE_LIMIT_EXCEEDED', 'test', v_test_user_id, 'Error test', '127.0.0.1'::INET, 'error');

        INSERT INTO audit_log (user_id, action, entity_type, entity_id, change_summary, ip_address, severity)
        VALUES (v_test_user_id, 'DATA_DELETE', 'test', v_test_user_id, 'Critical test', '127.0.0.1'::INET, 'critical');
    EXCEPTION WHEN OTHERS THEN
        v_all_severities_valid := false;
    END;

    -- Verificar severidades
    SELECT ARRAY_AGG(DISTINCT severity) INTO v_severity_types
    FROM audit_log
    WHERE user_id = v_test_user_id
    AND action IN ('LOGIN', 'FAILED_LOGIN', 'RATE_LIMIT_EXCEEDED', 'DATA_DELETE');

    IF v_all_severities_valid AND array_length(v_severity_types, 1) = 4 THEN
        v_status := 'PASS';
        v_details := format('All severity levels supported: %s', array_to_string(v_severity_types, ', '));
    ELSE
        v_status := 'FAIL';
        v_details := format('Missing severity levels. Found: %s', array_to_string(v_severity_types, ', '));
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Severity Levels', 'Breach_Notification', v_status, v_details);

    RAISE NOTICE '  [%] Severity Levels: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Severity Levels', 'Breach_Notification', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 9.3: Registro de IP en Eventos de Seguridad
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_audit_id UUID;
    v_recorded_ip INET;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_IP_LOG_USER', 'test_ip_log_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash', 'admin')
    RETURNING id INTO v_test_user_id;

    PERFORM set_current_user(v_test_user_id, NULL::UUID, '192.168.100.50'::INET);

    -- Registrar evento con IP específica (usando acción válida)
    INSERT INTO audit_log (
        user_id, action, entity_type, entity_id,
        change_summary, ip_address, severity
    )
    VALUES (
        v_test_user_id,
        'LOGIN',
        'security',
        v_test_user_id,
        'Testing IP logging',
        '192.168.100.50'::INET,
        'info'
    )
    RETURNING id INTO v_audit_id;

    -- Verificar IP registrada
    SELECT ip_address INTO v_recorded_ip
    FROM audit_log WHERE id = v_audit_id;

    IF v_recorded_ip IS NOT NULL AND v_recorded_ip = '192.168.100.50'::INET THEN
        v_status := 'PASS';
        v_details := format('IP address correctly logged: %s', v_recorded_ip);
    ELSE
        v_status := 'FAIL';
        v_details := format('IP logging failed - expected 192.168.100.50, got: %s', v_recorded_ip);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('IP Address Logging', 'Breach_Notification', v_status, v_details);

    RAISE NOTICE '  [%] IP Address Logging: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('IP Address Logging', 'Breach_Notification', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 9.4: Timestamp de Eventos para Cumplir 72 Horas
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_audit_id UUID;
    v_event_timestamp TIMESTAMP WITH TIME ZONE;
    v_time_diff INTERVAL;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_TIMESTAMP_USER', 'test_timestamp_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash', 'admin')
    RETURNING id INTO v_test_user_id;

    PERFORM set_current_user(v_test_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Registrar evento (usando acción válida)
    INSERT INTO audit_log (
        user_id, action, entity_type, entity_id,
        change_summary, ip_address, severity
    )
    VALUES (
        v_test_user_id,
        'FAILED_LOGIN',
        'security',
        v_test_user_id,
        'Testing timestamp precision',
        '127.0.0.1'::INET,
        'warning'
    )
    RETURNING id, created_at INTO v_audit_id, v_event_timestamp;

    -- Verificar que el timestamp es preciso (con timezone)
    v_time_diff := CURRENT_TIMESTAMP - v_event_timestamp;

    IF v_event_timestamp IS NOT NULL AND v_time_diff < INTERVAL '1 minute' THEN
        v_status := 'PASS';
        v_details := format('Timestamp recorded accurately: %s (diff: %s)', v_event_timestamp, v_time_diff);
    ELSE
        v_status := 'FAIL';
        v_details := format('Timestamp issue - recorded: %s, diff: %s', v_event_timestamp, v_time_diff);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Event Timestamp Precision', 'Breach_Notification', v_status, v_details);

    RAISE NOTICE '  [%] Event Timestamp Precision: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Event Timestamp Precision', 'Breach_Notification', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 9.5: Consulta de Eventos por Rango de Fechas (para reportes)
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_event_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_RANGE_USER', 'test_range_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash', 'admin')
    RETURNING id INTO v_test_user_id;

    PERFORM set_current_user(v_test_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Crear varios eventos (usando acciones válidas)
    INSERT INTO audit_log (user_id, action, entity_type, entity_id, change_summary, ip_address, severity)
    VALUES
        (v_test_user_id, 'INSERT', 'security', v_test_user_id, 'Range Test 1', '127.0.0.1'::INET, 'info'),
        (v_test_user_id, 'UPDATE', 'security', v_test_user_id, 'Range Test 2', '127.0.0.1'::INET, 'warning'),
        (v_test_user_id, 'DELETE', 'security', v_test_user_id, 'Range Test 3', '127.0.0.1'::INET, 'error');

    -- Consultar eventos en rango de fechas (últimas 72 horas - requerimiento RGPD)
    SELECT COUNT(*) INTO v_event_count
    FROM audit_log
    WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '72 hours'
    AND change_summary LIKE 'Range Test%'
    AND user_id = v_test_user_id;

    IF v_event_count = 3 THEN
        v_status := 'PASS';
        v_details := format('Date range query works correctly (%s events in last 72h)', v_event_count);
    ELSE
        v_status := 'FAIL';
        v_details := format('Date range query failed - expected 3, got %s', v_event_count);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Date Range Query', 'Breach_Notification', v_status, v_details);

    RAISE NOTICE '  [%] Date Range Query: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Date Range Query', 'Breach_Notification', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 9.6: Eventos Críticos Incluyen Información de Afectados
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_audit_id UUID;
    v_has_entity_info BOOLEAN;
    v_has_change_details BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_CRITICAL_USER', 'test_critical_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash', 'admin')
    RETURNING id INTO v_test_user_id;

    PERFORM set_current_user(v_test_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Registrar evento crítico con información de afectados (usando acción válida)
    INSERT INTO audit_log (
        user_id, action, entity_type, entity_id,
        change_summary, ip_address, severity
    )
    VALUES (
        v_test_user_id,
        'DATA_DELETE',
        'user',
        v_test_user_id,
        'Potential data breach: 150 user records potentially affected. Categories: email, phone.',
        '10.0.0.1'::INET,
        'critical'
    )
    RETURNING id INTO v_audit_id;

    -- Verificar información completa
    SELECT
        entity_id IS NOT NULL,
        change_summary IS NOT NULL AND length(change_summary) > 20
    INTO v_has_entity_info, v_has_change_details
    FROM audit_log WHERE id = v_audit_id;

    IF v_has_entity_info AND v_has_change_details THEN
        v_status := 'PASS';
        v_details := 'Critical event includes affected entity and detailed summary';
    ELSE
        v_status := 'FAIL';
        v_details := format('Missing info - entity:%s, details:%s', v_has_entity_info, v_has_change_details);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Critical Event Details', 'Breach_Notification', v_status, v_details);

    RAISE NOTICE '  [%] Critical Event Details: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Critical Event Details', 'Breach_Notification', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 9.7: Integridad de Audit Log (No Modificable)
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_audit_id UUID;
    v_update_blocked BOOLEAN := false;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_INTEGRITY_USER', 'test_integrity_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash', 'admin')
    RETURNING id INTO v_test_user_id;

    PERFORM set_current_user(v_test_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Crear evento (usando acción válida)
    INSERT INTO audit_log (
        user_id, action, entity_type, entity_id,
        change_summary, ip_address, severity
    )
    VALUES (
        v_test_user_id,
        'INSERT',
        'security',
        v_test_user_id,
        'Original message',
        '127.0.0.1'::INET,
        'info'
    )
    RETURNING id INTO v_audit_id;

    -- Intentar modificar (debe fallar)
    BEGIN
        UPDATE audit_log
        SET change_summary = 'TAMPERED!'
        WHERE id = v_audit_id;
        v_update_blocked := false;
    EXCEPTION WHEN OTHERS THEN
        v_update_blocked := true;
    END;

    IF v_update_blocked THEN
        v_status := 'PASS';
        v_details := 'Audit log modification correctly blocked (immutable)';
    ELSE
        -- NOTA: El schema actual NO tiene trigger para bloquear UPDATE
        -- Esto es una RECOMENDACIÓN de seguridad
        v_status := 'FAIL';
        v_details := 'Audit log was modified - RECOMENDACIÓN: agregar trigger para bloquear modificaciones';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Audit Immutability', 'Breach_Notification', v_status, v_details);

    RAISE NOTICE '  [%] Audit Immutability: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Audit Immutability', 'Breach_Notification', 'FAIL', 'Exception: ' || SQLERRM);
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
WHERE test_category = 'Breach_Notification'
GROUP BY test_category;

SELECT test_name, details
FROM test_results
WHERE test_category = 'Breach_Notification' AND status = 'FAIL';

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
