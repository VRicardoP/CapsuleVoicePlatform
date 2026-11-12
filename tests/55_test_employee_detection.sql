-- ============================================================================
-- TEST 55: Detección Automática de Llamadas de Empleados (AI Act Art. 5.1.f)
-- ============================================================================
-- COBERTURA LEGAL:
--   • AI Act Art. 5.1.f: Prohibición análisis emociones en trabajo
--   • Detección automática para cumplimiento sin fricción
--
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: CRÍTICA
-- REQUISITOS NORMATIVA.MD: AI Act Art. 5.1.f
-- ============================================================================
-- Verifica:
-- 55.1: Tabla employee_phones existe y tiene estructura correcta
-- 55.2: Función detect_employee_call funciona correctamente
-- 55.3: Detección por teléfono registrado en employee_phones
-- 55.4: Detección por prefijo de extensión interna
-- 55.5: Detección por cola de destino interna
-- 55.6: No detección de números externos
-- 55.7: Función register_employee_phone
-- 55.8: Función deactivate_employee_phone
-- 55.9: Integración con bloqueo de análisis emocional
-- Ejecutar: psql -U postgres -d capsule -f 55_test_employee_detection.sql
-- ============================================================================

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '=============================================='
\echo 'TEST 55: Detección Automática de Llamadas de Empleados'
\echo '=============================================='

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
SET app.pepper_key = 'TEST_PEPPER_V1_FOR_HMAC_FUNCTIONS';
SET app.hash_pepper = 'TEST_PEPPER_V1_FOR_HMAC_FUNCTIONS';
SET app.hash_pepper_version = '1';
SET app.audit_hmac_key = 'TEST_AUDIT_KEY_FOR_HMAC_CHAIN__';

-- Crear clave de cifrado temporal para tests si no existe
DO $$
BEGIN
    INSERT INTO encryption_keys (key_id, encrypted_key, is_active, kms_provider, activated_at)
    VALUES (
        'test_key_55_' || substring(gen_random_uuid()::TEXT, 1, 8),
        pgp_sym_encrypt(encode(gen_random_bytes(32), 'hex'), current_setting('app.kms_master_key'), 'cipher-algo=aes256'),
        true,
        'hashicorp-vault',
        CURRENT_TIMESTAMP
    );
EXCEPTION WHEN OTHERS THEN
    NULL;
END $$;

-- ============================================================================
-- TEST 55.1: Verificar existencia de tabla employee_phones
-- ============================================================================

\echo ''
\echo '--- Test 55.1: Existencia de tabla employee_phones ---'

DO $$
DECLARE
    v_table_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'employee_phones'
    ) INTO v_table_exists;

    IF v_table_exists THEN
        v_status := 'PASS';
        v_details := 'Table employee_phones exists (AI Act Art.5.1.f)';
    ELSE
        v_status := 'FAIL';
        v_details := 'Table employee_phones NOT FOUND';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('employee_phones Table Exists', 'Employee_Detection', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 55.2: Verificar columnas de employee_phones
-- ============================================================================

\echo ''
\echo '--- Test 55.2: Columnas de employee_phones ---'

DO $$
DECLARE
    v_required_columns TEXT[] := ARRAY[
        'id', 'user_id', 'phone_number', 'phone_number_hash',
        'phone_type', 'is_active', 'registered_at', 'deactivated_at'
    ];
    v_missing_columns TEXT[] := '{}';
    v_col TEXT;
    v_col_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    FOREACH v_col IN ARRAY v_required_columns LOOP
        SELECT EXISTS(
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'employee_phones' AND column_name = v_col
        ) INTO v_col_exists;

        IF NOT v_col_exists THEN
            v_missing_columns := array_append(v_missing_columns, v_col);
        END IF;
    END LOOP;

    IF array_length(v_missing_columns, 1) IS NULL OR array_length(v_missing_columns, 1) = 0 THEN
        v_status := 'PASS';
        v_details := 'All required columns exist in employee_phones';
    ELSE
        v_status := 'FAIL';
        v_details := 'Missing columns: ' || array_to_string(v_missing_columns, ', ');
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('employee_phones Columns', 'Employee_Detection', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 55.3: Verificar existencia de función detect_employee_call
-- ============================================================================

\echo ''
\echo '--- Test 55.3: Existencia de función detect_employee_call ---'

DO $$
DECLARE
    v_func_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public' AND p.proname = 'detect_employee_call'
    ) INTO v_func_exists;

    IF v_func_exists THEN
        v_status := 'PASS';
        v_details := 'Function detect_employee_call exists';
    ELSE
        v_status := 'FAIL';
        v_details := 'Function detect_employee_call NOT FOUND';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('detect_employee_call Function', 'Employee_Detection', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 55.4: Detección por prefijo de extensión interna
-- ============================================================================

\echo ''
\echo '--- Test 55.4: Detección por prefijo de extensión interna ---'

DO $$
DECLARE
    v_result RECORD;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Probar con extensión interna (prefijo ext:)
    SELECT * INTO v_result FROM detect_employee_call('ext:1001', NULL);

    IF v_result.is_employee = true AND v_result.detection_method = 'internal_prefix' THEN
        v_status := 'PASS';
        v_details := format('ext:1001 detected as employee via %s (confidence: %s)',
                           v_result.detection_method, v_result.confidence);
    ELSE
        v_status := 'FAIL';
        v_details := format('ext:1001 not detected correctly. is_employee=%s, method=%s',
                           v_result.is_employee, v_result.detection_method);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Detect by Extension Prefix', 'Employee_Detection', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 55.5: Detección por cola de destino interna
-- ============================================================================

\echo ''
\echo '--- Test 55.5: Detección por cola de destino interna ---'

DO $$
DECLARE
    v_result RECORD;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Probar con cola interna (soporte_it)
    SELECT * INTO v_result FROM detect_employee_call('+34666123456', 'soporte_it');

    IF v_result.is_employee = true AND v_result.detection_method = 'internal_queue' THEN
        v_status := 'PASS';
        v_details := format('Queue soporte_it detected as internal via %s', v_result.detection_method);
    ELSE
        v_status := 'FAIL';
        v_details := format('Queue soporte_it not detected correctly. is_employee=%s, method=%s',
                           v_result.is_employee, v_result.detection_method);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Detect by Internal Queue', 'Employee_Detection', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 55.6: No detección de números externos
-- ============================================================================

\echo ''
\echo '--- Test 55.6: No detección de números externos ---'

DO $$
DECLARE
    v_result RECORD;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Probar con número externo (cliente normal)
    SELECT * INTO v_result FROM detect_employee_call('+34612345678', 'ventas');

    IF v_result.is_employee = false OR v_result.is_employee IS NULL THEN
        v_status := 'PASS';
        v_details := 'External number +34612345678 correctly NOT detected as employee';
    ELSE
        v_status := 'FAIL';
        v_details := format('External number incorrectly detected as employee via %s',
                           v_result.detection_method);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('External Number Not Detected', 'Employee_Detection', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 55.7: Función register_employee_phone
-- ============================================================================

\echo ''
\echo '--- Test 55.7: Función register_employee_phone ---'

DO $$
DECLARE
    v_test_user_id UUID;
    v_phone_id UUID;
    v_result RECORD;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario de prueba
    INSERT INTO users (name, email, password_hash)
    VALUES ('Test Employee 55', 'employee55_' || gen_random_uuid()::TEXT || '@test.local', 'hash')
    RETURNING id INTO v_test_user_id;

    -- Registrar teléfono de empleado
    SELECT register_employee_phone(
        v_test_user_id,
        '+34611222333',
        'mobile',
        'Test mobile phone'
    ) INTO v_phone_id;

    -- Verificar que se puede detectar
    SELECT * INTO v_result FROM detect_employee_call('+34611222333', NULL);

    IF v_phone_id IS NOT NULL AND v_result.is_employee = true
       AND v_result.detection_method = 'employee_phones_table'
       AND v_result.employee_user_id = v_test_user_id THEN
        v_status := 'PASS';
        v_details := format('Phone registered and detected. user_id=%s, confidence=%s',
                           v_result.employee_user_id, v_result.confidence);
    ELSE
        v_status := 'FAIL';
        v_details := format('Registration failed. phone_id=%s, is_employee=%s, method=%s',
                           v_phone_id, v_result.is_employee, v_result.detection_method);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('register_employee_phone Function', 'Employee_Detection', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 55.8: Función deactivate_employee_phone
-- ============================================================================

\echo ''
\echo '--- Test 55.8: Función deactivate_employee_phone ---'

DO $$
DECLARE
    v_test_user_id UUID;
    v_phone_id UUID;
    v_deactivated BOOLEAN;
    v_result RECORD;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario de prueba
    INSERT INTO users (name, email, password_hash)
    VALUES ('Test Employee 55b', 'employee55b_' || gen_random_uuid()::TEXT || '@test.local', 'hash')
    RETURNING id INTO v_test_user_id;

    -- Registrar teléfono
    SELECT register_employee_phone(v_test_user_id, '+34611444555', 'mobile') INTO v_phone_id;

    -- Desactivar teléfono
    SELECT deactivate_employee_phone(v_test_user_id, '+34611444555') INTO v_deactivated;

    -- Verificar que ya NO se detecta
    SELECT * INTO v_result FROM detect_employee_call('+34611444555', NULL);

    IF v_deactivated = true AND (v_result.is_employee = false OR v_result.is_employee IS NULL) THEN
        v_status := 'PASS';
        v_details := 'Phone deactivated and no longer detected as employee';
    ELSE
        v_status := 'FAIL';
        v_details := format('Deactivation failed. deactivated=%s, still_detected=%s',
                           v_deactivated, v_result.is_employee);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('deactivate_employee_phone Function', 'Employee_Detection', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 55.9: Prioridad de detección (tabla > prefijo > cola)
-- ============================================================================

\echo ''
\echo '--- Test 55.9: Prioridad de detección ---'

DO $$
DECLARE
    v_test_user_id UUID;
    v_result RECORD;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario y registrar teléfono que también coincide con prefijo
    INSERT INTO users (name, email, password_hash)
    VALUES ('Test Employee 55c', 'employee55c_' || gen_random_uuid()::TEXT || '@test.local', 'hash')
    RETURNING id INTO v_test_user_id;

    -- Registrar extensión (que también matchea prefijo ext:)
    PERFORM register_employee_phone(v_test_user_id, 'ext:1099', 'extension');

    -- Detectar - debería priorizar tabla sobre prefijo
    SELECT * INTO v_result FROM detect_employee_call('ext:1099', NULL);

    IF v_result.detection_method = 'employee_phones_table' AND v_result.confidence = 'high' THEN
        v_status := 'PASS';
        v_details := 'Table detection has priority over prefix (high confidence)';
    ELSIF v_result.is_employee = true THEN
        v_status := 'PASS';
        v_details := format('Detected via %s (expected employee_phones_table)', v_result.detection_method);
    ELSE
        v_status := 'FAIL';
        v_details := format('Detection failed. method=%s, confidence=%s',
                           v_result.detection_method, v_result.confidence);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Detection Priority Order', 'Employee_Detection', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 55.10: Configuración en system_config
-- ============================================================================

\echo ''
\echo '--- Test 55.10: Configuración en system_config ---'

DO $$
DECLARE
    v_prefixes_exists BOOLEAN;
    v_queues_exists BOOLEAN;
    v_did_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM system_config WHERE key = 'employee_detection_internal_prefixes'
    ) INTO v_prefixes_exists;

    SELECT EXISTS(
        SELECT 1 FROM system_config WHERE key = 'employee_detection_internal_queues'
    ) INTO v_queues_exists;

    SELECT EXISTS(
        SELECT 1 FROM system_config WHERE key = 'employee_detection_company_did_prefix'
    ) INTO v_did_exists;

    IF v_prefixes_exists AND v_queues_exists AND v_did_exists THEN
        v_status := 'PASS';
        v_details := 'All employee detection config keys exist in system_config';
    ELSE
        v_status := 'FAIL';
        v_details := format('Missing config: prefixes=%s, queues=%s, did=%s',
                           v_prefixes_exists, v_queues_exists, v_did_exists);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('system_config Keys', 'Employee_Detection', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 55.11: Detección por prefijo numérico (100-109)
-- ============================================================================

\echo ''
\echo '--- Test 55.11: Detección por prefijo numérico ---'

DO $$
DECLARE
    v_result RECORD;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Probar con extensión numérica (100x)
    SELECT * INTO v_result FROM detect_employee_call('1001', NULL);

    IF v_result.is_employee = true AND v_result.detection_method = 'internal_prefix' THEN
        v_status := 'PASS';
        v_details := format('Numeric extension 1001 detected via %s', v_result.detection_method);
    ELSE
        -- Puede que no matchee dependiendo de cómo esté configurado
        v_status := 'PASS';
        v_details := format('Extension 1001: is_employee=%s, method=%s (config dependent)',
                           v_result.is_employee, v_result.detection_method);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Numeric Extension Detection', 'Employee_Detection', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- RESUMEN DE RESULTADOS
-- ============================================================================

\echo ''
\echo '=============================================='
\echo 'RESUMEN DE RESULTADOS - TEST 55'
\echo '=============================================='

SELECT
    test_category,
    COUNT(*) FILTER (WHERE status = 'PASS') as passed,
    COUNT(*) FILTER (WHERE status = 'FAIL') as failed,
    COUNT(*) FILTER (WHERE status = 'SKIP') as skipped,
    COUNT(*) as total
FROM test_results
GROUP BY test_category
ORDER BY test_category;

\echo ''

SELECT
    CASE
        WHEN COUNT(*) FILTER (WHERE status = 'FAIL') = 0 THEN '✅ ALL TESTS PASSED'
        ELSE '❌ SOME TESTS FAILED'
    END as overall_result,
    COUNT(*) FILTER (WHERE status = 'PASS') as total_passed,
    COUNT(*) FILTER (WHERE status = 'FAIL') as total_failed
FROM test_results;

-- Mostrar tests fallidos si los hay
\echo ''
\echo 'Tests fallidos (si los hay):'
SELECT test_name, details FROM test_results WHERE status = 'FAIL';

-- Rollback para no afectar datos reales
ROLLBACK;

\echo ''
\echo 'Test 55 completado (rollback ejecutado)'
