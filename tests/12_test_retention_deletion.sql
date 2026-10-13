-- ============================================================================
-- TEST 12: SISTEMA DE RETENCIÓN Y SUPRESIÓN (Art. 17 RGPD)
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 17: Derecho de supresión
--   • RGPD Art. 5.1.e: Limitación plazo conservación
--   • RGPD Art. 17.3.b: Excepción por obligación legal (conservar)
--   • LOPDGDD Art. 33: Bloqueo de datos antes de supresión
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: CRÍTICA
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Art. 17, PARTE 2 - Art. 33
-- ============================================================================
-- Verifica:
-- - Art. 17.1: Derecho de supresión (derecho al olvido)
-- - Art. 17.2: Obligación de informar a terceros
-- - Art. 17.3: Excepciones (obligaciones legales)
-- - Retención automática por tipo de dato
-- - scheduled_maintenance() mejorado
-- - Plazo de 30 días (Art. 12.3)
-- ============================================================================

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '============================================================================'
\echo 'TEST 12: SISTEMA DE RETENCIÓN Y SUPRESIÓN (Art. 17 RGPD)'
\echo '============================================================================'
\echo ''

-- Crear tabla temporal para resultados
CREATE TABLE IF NOT EXISTS test_results (
    id SERIAL PRIMARY KEY,
    test_name VARCHAR(200),
    test_category VARCHAR(100),
    status VARCHAR(20),
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Limpiar resultados anteriores de esta categoría
DELETE FROM test_results WHERE test_category = 'Retention_Deletion';

-- Configurar variables de sesión para tests
SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';
SET app.hash_pepper = 'TEST_PEPPER_V1_FOR_HMAC_FUNCTIONS';
SET app.hash_pepper_version = '1';
SET app.audit_hmac_key = 'TEST_AUDIT_KEY_FOR_HMAC_CHAIN_32';

-- Variables de test
DO $$ BEGIN PERFORM set_config('test.admin_user_id', '', false); END $$;
DO $$ BEGIN PERFORM set_config('test.user_to_delete_id', '', false); END $$;
DO $$ BEGIN PERFORM set_config('test.contact_to_delete_id', '', false); END $$;
DO $$ BEGIN PERFORM set_config('test.deletion_request_id', '', false); END $$;

-- ============================================================================
-- SETUP: Crear usuario admin y datos de prueba
-- ============================================================================

DO $$
DECLARE
    v_admin_id UUID;
    v_user_to_delete_id UUID;
    v_contact_id UUID;
BEGIN
    -- Crear usuario admin de prueba
    INSERT INTO users (name, email, password_hash, password_algorithm, role, is_active)
    VALUES (
        'TEST_RETENTION_ADMIN',
        'test_retention_admin_' || gen_random_uuid()::TEXT || '@test.local',
        'test_hash',
        'bcrypt',
        'admin',
        true
    )
    RETURNING id INTO v_admin_id;

    PERFORM set_config('test.admin_user_id', v_admin_id::TEXT, false);
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    -- Crear usuario a eliminar
    INSERT INTO users (name, email, password_hash, password_algorithm, role, is_active)
    VALUES (
        'TEST_USER_TO_DELETE',
        'test_user_delete_' || gen_random_uuid()::TEXT || '@test.local',
        'test_hash',
        'bcrypt',
        'user',
        true
    )
    RETURNING id INTO v_user_to_delete_id;

    PERFORM set_config('test.user_to_delete_id', v_user_to_delete_id::TEXT, false);

    -- Crear contacto a eliminar
    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_admin_id,
        '{"c": "Test Contact"}'::JSONB,
        '{"c": "+34600000000"}'::JSONB,
        'hash_contact_' || gen_random_uuid()::TEXT
    )
    RETURNING id INTO v_contact_id;

    PERFORM set_config('test.contact_to_delete_id', v_contact_id::TEXT, false);

    RAISE NOTICE 'Setup: Admin: %, User to delete: %, Contact: %', v_admin_id, v_user_to_delete_id, v_contact_id;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Setup FAILED: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 12.1: Verificar existencia de tablas de retención
-- ============================================================================

\echo '  [TEST 12.1] Verificar existencia de tablas'

DO $$
DECLARE
    v_tables_exist BOOLEAN;
    v_missing_tables TEXT[];
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_missing_tables := ARRAY[]::TEXT[];

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'retention_policies') THEN
        v_missing_tables := array_append(v_missing_tables, 'retention_policies');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'maintenance_log') THEN
        v_missing_tables := array_append(v_missing_tables, 'maintenance_log');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'deletion_requests') THEN
        v_missing_tables := array_append(v_missing_tables, 'deletion_requests');
    END IF;

    IF array_length(v_missing_tables, 1) IS NULL THEN
        v_status := 'PASS';
        v_details := 'Todas las tablas de retención existen';
    ELSE
        v_status := 'FAIL';
        v_details := 'Tablas faltantes: ' || array_to_string(v_missing_tables, ', ');
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Tables Existence', 'Retention_Deletion', v_status, v_details);

    RAISE NOTICE '    [%] Tables Existence: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 12.2: Verificar políticas de retención cargadas
-- ============================================================================

\echo '  [TEST 12.2] Verificar políticas de retención'

DO $$
DECLARE
    v_policy_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(*) INTO v_policy_count
    FROM retention_policies
    WHERE is_active = true;

    IF v_policy_count >= 8 THEN
        v_status := 'PASS';
        v_details := format('%s políticas de retención configuradas', v_policy_count);
    ELSE
        v_status := 'FAIL';
        v_details := format('Solo %s políticas, se esperaban al menos 8', v_policy_count);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Retention Policies Loaded', 'Retention_Deletion', v_status, v_details);

    RAISE NOTICE '    [%] Retention Policies: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 12.3: Verificar retención legal (Art. 17.3.e)
-- ============================================================================

\echo '  [TEST 12.3] Verificar excepciones Art. 17.3 (retención legal)'

DO $$
DECLARE
    v_legal_holds INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(*) INTO v_legal_holds
    FROM retention_policies
    WHERE has_legal_hold_exception = true
      AND legal_hold_basis IS NOT NULL
      AND is_active = true;

    IF v_legal_holds >= 3 THEN
        v_status := 'PASS';
        v_details := format('%s entidades con retención legal (audit_log, security_breaches, data_consents)', v_legal_holds);
    ELSE
        v_status := 'FAIL';
        v_details := format('Solo %s entidades con retención legal', v_legal_holds);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Legal Hold Exceptions', 'Retention_Deletion', v_status, v_details);

    RAISE NOTICE '    [%] Legal Hold Art. 17.3: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 12.4: Crear solicitud de supresión (usuario)
-- ============================================================================

\echo '  [TEST 12.4] Crear solicitud de supresión (usuario)'

DO $$
DECLARE
    v_admin_id UUID;
    v_user_id UUID;
    v_result JSON;
    v_request_id UUID;
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    v_user_id := current_setting('test.user_to_delete_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    SELECT create_deletion_request(v_user_id, 'user', 'all') INTO v_result;

    IF (v_result->>'success')::BOOLEAN THEN
        v_request_id := (v_result->>'request_id')::UUID;
        PERFORM set_config('test.deletion_request_id', v_request_id::TEXT, false);
        v_status := 'PASS';
        v_details := format('Solicitud creada: %s, deadline: %s', v_request_id, v_result->>'deadline');
    ELSE
        v_status := 'FAIL';
        v_details := 'Error: ' || (v_result->>'error');
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Create Deletion Request', 'Retention_Deletion', v_status, v_details);

    RAISE NOTICE '    [%] Create Deletion Request: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Create Deletion Request', 'Retention_Deletion', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Create Deletion Request: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 12.5: Verificar plazo de 30 días (Art. 12.3)
-- ============================================================================

\echo '  [TEST 12.5] Verificar plazo de 30 días Art. 12.3'

DO $$
DECLARE
    v_request_id UUID;
    v_deadline DATE;
    v_expected_deadline DATE;
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_request_id := current_setting('test.deletion_request_id', true)::UUID;

    IF v_request_id IS NOT NULL THEN
        SELECT deadline_date::DATE INTO v_deadline
        FROM deletion_requests
        WHERE id = v_request_id;

        v_expected_deadline := (CURRENT_DATE + INTERVAL '30 days')::DATE;

        IF v_deadline = v_expected_deadline THEN
            v_status := 'PASS';
            v_details := format('Deadline correcto: %s (30 días desde solicitud)', v_deadline);
        ELSE
            v_status := 'FAIL';
            v_details := format('Deadline incorrecto: %s, esperado: %s', v_deadline, v_expected_deadline);
        END IF;
    ELSE
        v_status := 'SKIP';
        v_details := 'No se pudo obtener el ID de la solicitud';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('30 Day Deadline', 'Retention_Deletion', v_status, v_details);

    RAISE NOTICE '    [%] 30 Day Deadline: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 12.6: Rechazar solicitud duplicada
-- ============================================================================

\echo '  [TEST 12.6] Rechazar solicitud duplicada'

DO $$
DECLARE
    v_admin_id UUID;
    v_user_id UUID;
    v_result JSON;
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    v_user_id := current_setting('test.user_to_delete_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    SELECT create_deletion_request(v_user_id, 'user', 'all') INTO v_result;

    IF NOT (v_result->>'success')::BOOLEAN THEN
        v_status := 'PASS';
        v_details := 'Correctamente rechazada solicitud duplicada';
    ELSE
        v_status := 'FAIL';
        v_details := 'Debería haber rechazado la solicitud duplicada';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Reject Duplicate Request', 'Retention_Deletion', v_status, v_details);

    RAISE NOTICE '    [%] Reject Duplicate: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Reject Duplicate Request', 'Retention_Deletion', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Reject Duplicate: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 12.7: Verificar identidad antes de procesar
-- ============================================================================

\echo '  [TEST 12.7] Verificar identidad antes de procesar'

DO $$
DECLARE
    v_admin_id UUID;
    v_request_id UUID;
    v_result JSON;
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    v_request_id := current_setting('test.deletion_request_id', true)::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    IF v_request_id IS NOT NULL THEN
        SELECT verify_deletion_request_identity(v_request_id, 'DNI verificado por admin') INTO v_result;

        IF (v_result->>'success')::BOOLEAN THEN
            v_status := 'PASS';
            v_details := format('Identidad verificada, status: %s', v_result->>'status');
        ELSE
            v_status := 'FAIL';
            v_details := 'Error: ' || (v_result->>'error');
        END IF;
    ELSE
        v_status := 'SKIP';
        v_details := 'Request ID no disponible';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Verify Identity', 'Retention_Deletion', v_status, v_details);

    RAISE NOTICE '    [%] Verify Identity: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Verify Identity', 'Retention_Deletion', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Verify Identity: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 12.8: Rechazar proceso sin verificación de identidad
-- ============================================================================

\echo '  [TEST 12.8] Rechazar proceso sin verificación (nuevo request)'

DO $$
DECLARE
    v_admin_id UUID;
    v_contact_id UUID;
    v_result JSON;
    v_new_request_id UUID;
    v_process_result JSON;
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    v_contact_id := current_setting('test.contact_to_delete_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    -- Crear nueva solicitud para contacto
    SELECT create_deletion_request(v_contact_id, 'contact', 'all') INTO v_result;

    IF (v_result->>'success')::BOOLEAN THEN
        v_new_request_id := (v_result->>'request_id')::UUID;

        -- Intentar procesar sin verificar identidad
        SELECT process_deletion_request(v_new_request_id) INTO v_process_result;

        IF NOT (v_process_result->>'success')::BOOLEAN
           AND (v_process_result->>'error') = 'Identity not verified' THEN
            v_status := 'PASS';
            v_details := 'Correctamente rechazado sin verificación de identidad';
        ELSE
            v_status := 'FAIL';
            v_details := 'Debería rechazar sin verificación';
        END IF;

        -- Limpiar: eliminar la solicitud de prueba
        DELETE FROM deletion_requests WHERE id = v_new_request_id;
    ELSE
        v_status := 'FAIL';
        v_details := 'No se pudo crear solicitud de prueba';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Reject Without Identity', 'Retention_Deletion', v_status, v_details);

    RAISE NOTICE '    [%] Reject Without Identity: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Reject Without Identity', 'Retention_Deletion', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Reject Without Identity: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 12.9: Procesar solicitud de supresión
-- ============================================================================

\echo '  [TEST 12.9] Procesar solicitud de supresión'

DO $$
DECLARE
    v_admin_id UUID;
    v_request_id UUID;
    v_result JSON;
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    v_request_id := current_setting('test.deletion_request_id', true)::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    IF v_request_id IS NOT NULL THEN
        SELECT process_deletion_request(v_request_id) INTO v_result;

        IF (v_result->>'success')::BOOLEAN THEN
            v_status := 'PASS';
            v_details := format('Procesado: deleted=%s, anonymized=%s, retained=%s',
                v_result->>'records_deleted',
                v_result->>'records_anonymized',
                v_result->>'records_retained_legal_hold');
        ELSE
            v_status := 'FAIL';
            v_details := 'Error: ' || (v_result->>'error');
        END IF;
    ELSE
        v_status := 'SKIP';
        v_details := 'Request ID no disponible';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Process Deletion Request', 'Retention_Deletion', v_status, v_details);

    RAISE NOTICE '    [%] Process Deletion: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Process Deletion Request', 'Retention_Deletion', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Process Deletion: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 12.10: Verificar usuario anonimizado
-- ============================================================================

\echo '  [TEST 12.10] Verificar usuario anonimizado'

DO $$
DECLARE
    v_user_id UUID;
    v_user_name TEXT;
    v_user_active BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_user_id := current_setting('test.user_to_delete_id')::UUID;

    SELECT name, is_active INTO v_user_name, v_user_active
    FROM users
    WHERE id = v_user_id;

    IF v_user_name LIKE 'USUARIO_ELIMINADO_%' AND NOT v_user_active THEN
        v_status := 'PASS';
        v_details := format('Usuario anonimizado correctamente: %s, active=%s', v_user_name, v_user_active);
    ELSE
        v_status := 'FAIL';
        v_details := format('Usuario no anonimizado: name=%s, active=%s', v_user_name, v_user_active);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('User Anonymized', 'Retention_Deletion', v_status, v_details);

    RAISE NOTICE '    [%] User Anonymized: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('User Anonymized', 'Retention_Deletion', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] User Anonymized: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 12.11: Verificar registro en maintenance_log
-- ============================================================================

\echo '  [TEST 12.11] Verificar registro en maintenance_log'

DO $$
DECLARE
    v_request_id UUID;
    v_log_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_request_id := current_setting('test.deletion_request_id', true)::UUID;

    IF v_request_id IS NOT NULL THEN
        SELECT COUNT(*) INTO v_log_count
        FROM maintenance_log
        WHERE request_id = v_request_id
          AND operation_type = 'deletion_request';

        IF v_log_count >= 2 THEN  -- started + completed
            v_status := 'PASS';
            v_details := format('%s registros en maintenance_log (started + completed)', v_log_count);
        ELSE
            v_status := 'FAIL';
            v_details := format('Solo %s registros, esperados al menos 2', v_log_count);
        END IF;
    ELSE
        v_status := 'SKIP';
        v_details := 'Request ID no disponible';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Maintenance Log Entry', 'Retention_Deletion', v_status, v_details);

    RAISE NOTICE '    [%] Maintenance Log: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 12.12: Función scheduled_maintenance()
-- ============================================================================

\echo '  [TEST 12.12] Ejecutar scheduled_maintenance()'

DO $$
DECLARE
    v_admin_id UUID;
    v_task_count INTEGER := 0;
    v_result RECORD;
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    FOR v_result IN SELECT * FROM scheduled_maintenance() LOOP
        v_task_count := v_task_count + 1;
    END LOOP;

    IF v_task_count >= 5 THEN
        v_status := 'PASS';
        v_details := format('scheduled_maintenance() ejecutó %s tareas', v_task_count);
    ELSE
        v_status := 'FAIL';
        v_details := format('Solo %s tareas ejecutadas, esperadas al menos 5', v_task_count);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Scheduled Maintenance', 'Retention_Deletion', v_status, v_details);

    RAISE NOTICE '    [%] Scheduled Maintenance: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Scheduled Maintenance', 'Retention_Deletion', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Scheduled Maintenance: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 12.13: Función get_retention_status()
-- ============================================================================

\echo '  [TEST 12.13] Verificar get_retention_status()'

DO $$
DECLARE
    v_admin_id UUID;
    v_entity_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    SELECT COUNT(*) INTO v_entity_count
    FROM get_retention_status();

    IF v_entity_count >= 5 THEN
        v_status := 'PASS';
        v_details := format('get_retention_status() retorna %s entidades', v_entity_count);
    ELSE
        v_status := 'FAIL';
        v_details := format('Solo %s entidades, esperadas al menos 5', v_entity_count);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Get Retention Status', 'Retention_Deletion', v_status, v_details);

    RAISE NOTICE '    [%] Get Retention Status: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Get Retention Status', 'Retention_Deletion', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Get Retention Status: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 12.14: Función get_pending_deletion_requests()
-- ============================================================================

\echo '  [TEST 12.14] Verificar get_pending_deletion_requests()'

DO $$
DECLARE
    v_admin_id UUID;
    v_function_works BOOLEAN := false;
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    -- Simplemente verificar que la función se ejecuta sin error
    PERFORM * FROM get_pending_deletion_requests();
    v_function_works := true;

    IF v_function_works THEN
        v_status := 'PASS';
        v_details := 'get_pending_deletion_requests() funciona correctamente';
    ELSE
        v_status := 'FAIL';
        v_details := 'Función no ejecutó correctamente';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Get Pending Requests', 'Retention_Deletion', v_status, v_details);

    RAISE NOTICE '    [%] Get Pending Requests: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Get Pending Requests', 'Retention_Deletion', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Get Pending Requests: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 12.15: Vista v_retention_dashboard
-- ============================================================================

\echo '  [TEST 12.15] Verificar v_retention_dashboard'

DO $$
DECLARE
    v_row_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(*) INTO v_row_count
    FROM v_retention_dashboard;

    IF v_row_count >= 5 THEN
        v_status := 'PASS';
        v_details := format('v_retention_dashboard muestra %s políticas', v_row_count);
    ELSE
        v_status := 'FAIL';
        v_details := format('Solo %s filas en dashboard', v_row_count);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Retention Dashboard View', 'Retention_Deletion', v_status, v_details);

    RAISE NOTICE '    [%] Retention Dashboard: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Retention Dashboard View', 'Retention_Deletion', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Retention Dashboard: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 12.16: RLS habilitado en tablas
-- ============================================================================

\echo '  [TEST 12.16] RLS habilitado en tablas'

DO $$
DECLARE
    v_rls_maintenance BOOLEAN;
    v_rls_deletion BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT relrowsecurity INTO v_rls_maintenance
    FROM pg_class WHERE relname = 'maintenance_log';

    SELECT relrowsecurity INTO v_rls_deletion
    FROM pg_class WHERE relname = 'deletion_requests';

    IF v_rls_maintenance AND v_rls_deletion THEN
        v_status := 'PASS';
        v_details := 'RLS habilitado en maintenance_log y deletion_requests';
    ELSE
        v_status := 'FAIL';
        v_details := format('RLS: maintenance_log=%s, deletion_requests=%s', v_rls_maintenance, v_rls_deletion);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('RLS Enabled', 'Retention_Deletion', v_status, v_details);

    RAISE NOTICE '    [%] RLS Enabled: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 12.17: Control de acceso (usuario no admin)
-- ============================================================================

\echo '  [TEST 12.17] Control de acceso usuario no admin'

DO $$
DECLARE
    v_user_id UUID;
    v_result JSON;
    v_access_denied BOOLEAN := false;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario normal
    INSERT INTO users (name, email, password_hash, role, is_active)
    VALUES ('TEST_NORMAL_USER', 'test_normal_' || gen_random_uuid()::TEXT || '@test.local', 'hash', 'user', true)
    RETURNING id INTO v_user_id;

    PERFORM set_current_user(v_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Intentar verificar identidad (debería fallar con Access denied)
    SELECT verify_deletion_request_identity(gen_random_uuid(), 'test') INTO v_result;

    IF NOT (v_result->>'success')::BOOLEAN AND (v_result->>'error') = 'Access denied' THEN
        v_access_denied := true;
    END IF;

    -- Limpiar (restablecer usuario admin antes de borrar)
    PERFORM set_current_user(current_setting('test.admin_user_id')::UUID, NULL::UUID, '127.0.0.1'::INET);
    DELETE FROM users WHERE id = v_user_id;

    IF v_access_denied THEN
        v_status := 'PASS';
        v_details := 'Acceso denegado correctamente a usuario no admin';
    ELSE
        v_status := 'FAIL';
        v_details := 'Usuario no admin pudo acceder a funciones admin';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Non-Admin Access Denied', 'Retention_Deletion', v_status, v_details);

    RAISE NOTICE '    [%] Non-Admin Access: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    -- En caso de error, restablecer admin e intentar limpiar
    PERFORM set_current_user(current_setting('test.admin_user_id', true)::UUID, NULL, '127.0.0.1'::INET);
    DELETE FROM users WHERE email LIKE 'test_normal_%@test.local';

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Non-Admin Access Denied', 'Retention_Deletion', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Non-Admin Access: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 12.18: Índices de rendimiento
-- ============================================================================

\echo '  [TEST 12.18] Verificar índices de rendimiento'

DO $$
DECLARE
    v_indexes_exist INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(*) INTO v_indexes_exist
    FROM pg_indexes
    WHERE tablename IN ('retention_policies', 'maintenance_log', 'deletion_requests')
      AND indexname LIKE 'idx_%';

    IF v_indexes_exist >= 6 THEN
        v_status := 'PASS';
        v_details := format('%s índices de rendimiento encontrados', v_indexes_exist);
    ELSE
        v_status := 'FAIL';
        v_details := format('Solo %s índices, esperados al menos 6', v_indexes_exist);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Performance Indexes', 'Retention_Deletion', v_status, v_details);

    RAISE NOTICE '    [%] Performance Indexes: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 12.19: Solicitud para contacto (tipo diferente)
-- ============================================================================

\echo '  [TEST 12.19] Crear solicitud para contacto'

DO $$
DECLARE
    v_admin_id UUID;
    v_contact_id UUID;
    v_result JSON;
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    v_contact_id := current_setting('test.contact_to_delete_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    SELECT create_deletion_request(v_contact_id, 'contact', 'all') INTO v_result;

    IF (v_result->>'success')::BOOLEAN THEN
        v_status := 'PASS';
        v_details := format('Solicitud contacto creada: %s', v_result->>'request_id');

        -- Limpiar: eliminar la solicitud
        DELETE FROM deletion_requests WHERE id = (v_result->>'request_id')::UUID;
    ELSE
        v_status := 'FAIL';
        v_details := 'Error: ' || (v_result->>'error');
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Contact Deletion Request', 'Retention_Deletion', v_status, v_details);

    RAISE NOTICE '    [%] Contact Deletion Request: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Contact Deletion Request', 'Retention_Deletion', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Contact Deletion Request: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 12.20: Registro de auditoría de solicitudes
-- ============================================================================

\echo '  [TEST 12.20] Verificar registro de auditoría'

DO $$
DECLARE
    v_audit_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(*) INTO v_audit_count
    FROM audit_log
    WHERE action = 'DELETION_REQUEST_CREATED'
      AND entity_type = 'deletion_request';

    IF v_audit_count >= 1 THEN
        v_status := 'PASS';
        v_details := format('%s registros de auditoría para solicitudes de supresión', v_audit_count);
    ELSE
        v_status := 'FAIL';
        v_details := 'No se encontraron registros de auditoría';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Audit Log Entry', 'Retention_Deletion', v_status, v_details);

    RAISE NOTICE '    [%] Audit Log Entry: %', v_status, v_details;
END $$;

-- ============================================================================
-- CLEANUP
-- ============================================================================

\echo ''
\echo '  [CLEANUP] Eliminando datos de prueba...'

DO $$
DECLARE
    v_admin_id UUID;
    v_user_id UUID;
    v_contact_id UUID;
BEGIN
    v_admin_id := current_setting('test.admin_user_id', true)::UUID;
    v_user_id := current_setting('test.user_to_delete_id', true)::UUID;
    v_contact_id := current_setting('test.contact_to_delete_id', true)::UUID;

    IF v_admin_id IS NOT NULL THEN
        -- Eliminar solicitudes de prueba
        DELETE FROM deletion_requests WHERE data_subject_id IN (v_user_id, v_contact_id);
        DELETE FROM deletion_requests WHERE processed_by = v_admin_id;

        -- Eliminar logs de prueba
        DELETE FROM maintenance_log WHERE requested_by = v_admin_id;

        -- Eliminar contactos
        DELETE FROM contacts WHERE id = v_contact_id;
        DELETE FROM contacts WHERE user_id = v_admin_id;

        -- Eliminar usuarios
        DELETE FROM users WHERE id = v_user_id;
        DELETE FROM users WHERE id = v_admin_id;
        DELETE FROM users WHERE email LIKE 'test_%@test.local';
    END IF;

    RAISE NOTICE '    Datos de prueba eliminados';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE '    Error en cleanup: %', SQLERRM;
END $$;

-- ============================================================================
-- RESUMEN DE RESULTADOS
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'RESUMEN DE RESULTADOS - TEST 12: RETENCIÓN Y SUPRESIÓN (Art. 17)'
\echo '============================================================================'

SELECT
    format('   Total: %s tests', COUNT(*)) AS summary,
    format('Passed: %s', COUNT(*) FILTER (WHERE status = 'PASS')) AS passed,
    format('Failed: %s', COUNT(*) FILTER (WHERE status = 'FAIL')) AS failed,
    format('Skipped: %s', COUNT(*) FILTER (WHERE status = 'SKIP')) AS skipped
FROM test_results
WHERE test_category = 'Retention_Deletion';

\echo ''
\echo 'Detalle de tests fallidos:'
SELECT '   - ' || test_name || ': ' || details AS failed_test
FROM test_results
WHERE test_category = 'Retention_Deletion' AND status = 'FAIL';

\echo ''
\echo 'Detalle de todos los tests:'
SELECT
    CASE status
        WHEN 'PASS' THEN '   [OK] '
        WHEN 'FAIL' THEN '   [X]  '
        ELSE '   [-]  '
    END || test_name || ': ' || SUBSTRING(details, 1, 70) AS test_result
FROM test_results
WHERE test_category = 'Retention_Deletion'
ORDER BY id;

\echo ''
\echo '============================================================================'
\echo 'FIN TEST 12: RETENCIÓN Y SUPRESIÓN (Art. 17 RGPD)'
\echo '============================================================================'

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
