-- ============================================================================
-- TEST 28: LISTA ROBINSON - Orden ETD/1286/2022
-- ============================================================================
-- COBERTURA LEGAL:
--   • Lista Robinson Orden ETD/1286/2022 Art. 4.1: Consulta obligatoria
--   • Orden ETD/1286/2022 Art. 4.2: Máximo 30 días antes de comunicación
--   • Orden ETD/1286/2022 Art. 6: Documentar consultas
--   • LSSI Art. 21.1: Prohibición spam
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: CRÍTICA
-- REQUISITOS NORMATIVA.MD: PARTE 10 (Guías AEPD) - Lista Robinson
-- ============================================================================
-- Verifica el cumplimiento de la normativa de Lista Robinson para marketing
-- Ejecutar: psql -U postgres -d capsule -f 28_test_p3_robinson.sql
-- ============================================================================

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo ''
\echo '=============================================='
\echo 'TEST 28: LISTA ROBINSON (P3)'
\echo 'Orden ETD/1286/2022'
\echo '=============================================='
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

-- Limpiar resultados anteriores
DELETE FROM test_results WHERE test_category = 'P3_Robinson';

-- Configurar variables de sesión
SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';
SET app.hash_pepper = 'TEST_PEPPER_V1_FOR_HMAC_FUNCTIONS';
SET app.hash_pepper_version = '1';
SET app.audit_hmac_key = 'TEST_AUDIT_KEY_FOR_HMAC_CHAIN__';

-- ============================================================================
-- TEST 28.1: Verificar existencia de tabla robinson_checks
-- ============================================================================

\echo ''
\echo '--- Test 28.1: Verificar tabla robinson_checks ---'

DO $$
DECLARE
    v_table_exists BOOLEAN;
    v_column_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'robinson_checks' AND table_schema = 'public'
    ) INTO v_table_exists;

    SELECT COUNT(*) INTO v_column_count
    FROM information_schema.columns
    WHERE table_name = 'robinson_checks' AND table_schema = 'public';

    IF v_table_exists AND v_column_count >= 10 THEN
        v_status := 'PASS';
        v_details := format('Tabla robinson_checks existe con %s columnas', v_column_count);
    ELSE
        v_status := 'FAIL';
        v_details := format('Tabla robinson_checks: exists=%s, columns=%s', v_table_exists, v_column_count);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Table Existence', 'P3_Robinson', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 28.2: Verificar columnas requeridas
-- ============================================================================

\echo ''
\echo '--- Test 28.2: Verificar columnas requeridas ---'

DO $$
DECLARE
    v_required_columns TEXT[] := ARRAY[
        'phone_hash', 'is_registered', 'channel_checked',
        'valid_until', 'checked_by', 'check_timestamp'
    ];
    v_missing_columns TEXT[] := ARRAY[]::TEXT[];
    v_col TEXT;
    v_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    FOREACH v_col IN ARRAY v_required_columns LOOP
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'robinson_checks' AND column_name = v_col
        ) INTO v_exists;

        IF NOT v_exists THEN
            v_missing_columns := array_append(v_missing_columns, v_col);
        END IF;
    END LOOP;

    IF array_length(v_missing_columns, 1) IS NULL THEN
        v_status := 'PASS';
        v_details := 'Todas las columnas requeridas existen';
    ELSE
        v_status := 'FAIL';
        v_details := 'Columnas faltantes: ' || array_to_string(v_missing_columns, ', ');
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Required Columns', 'P3_Robinson', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 28.3: Verificar existencia de funciones
-- ============================================================================

\echo ''
\echo '--- Test 28.3: Verificar funciones Robinson ---'

DO $$
DECLARE
    v_func1 BOOLEAN;
    v_func2 BOOLEAN;
    v_func3 BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'check_robinson_status') INTO v_func1;
    SELECT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'register_robinson_check') INTO v_func2;
    SELECT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'can_add_to_marketing_campaign') INTO v_func3;

    IF v_func1 AND v_func2 AND v_func3 THEN
        v_status := 'PASS';
        v_details := 'Todas las funciones Robinson existen';
    ELSE
        v_status := 'FAIL';
        v_details := format('Funciones: check=%s, register=%s, can_add=%s', v_func1, v_func2, v_func3);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Functions Exist', 'P3_Robinson', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 28.4: Verificar trigger de valid_until
-- ============================================================================

\echo ''
\echo '--- Test 28.4: Verificar trigger valid_until ---'

DO $$
DECLARE
    v_trigger_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_robinson_valid_until'
    ) INTO v_trigger_exists;

    IF v_trigger_exists THEN
        v_status := 'PASS';
        v_details := 'Trigger trg_robinson_valid_until existe';
    ELSE
        v_status := 'FAIL';
        v_details := 'Trigger trg_robinson_valid_until no encontrado';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Valid Until Trigger', 'P3_Robinson', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 28.5: Test funcional - Registrar consulta Robinson (NO registrado)
-- ============================================================================

\echo ''
\echo '--- Test 28.5: Registrar consulta Robinson (NO en lista) ---'

DO $$
DECLARE
    v_user_id UUID;
    v_check_id UUID;
    v_valid_until TIMESTAMP WITH TIME ZONE;
    v_expected_valid TIMESTAMP WITH TIME ZONE;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario de test
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_ROBINSON_USER', 'robinson_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    PERFORM set_current_user(v_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Registrar consulta: teléfono NO está en Lista Robinson
    v_check_id := register_robinson_check(
        '+34600111222',
        false,  -- NO está en Lista Robinson
        'phone',
        NULL,
        NULL,
        '200',
        '{"status": "not_registered", "timestamp": "2025-12-03T12:00:00Z"}'
    );

    -- Verificar que se creó y valid_until es correcto (30 días)
    SELECT valid_until INTO v_valid_until FROM robinson_checks WHERE id = v_check_id;
    v_expected_valid := CURRENT_TIMESTAMP + INTERVAL '30 days';

    IF v_check_id IS NOT NULL AND v_valid_until IS NOT NULL
       AND v_valid_until BETWEEN v_expected_valid - INTERVAL '1 minute' AND v_expected_valid + INTERVAL '1 minute' THEN
        v_status := 'PASS';
        v_details := format('Consulta registrada: %s, válida hasta: %s', v_check_id, v_valid_until);
    ELSE
        v_status := 'FAIL';
        v_details := format('Error: check_id=%s, valid_until=%s', v_check_id, v_valid_until);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Register Check Not Listed', 'P3_Robinson', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;

    -- Guardar para siguiente test
    PERFORM set_config('test.robinson_check_id', v_check_id::TEXT, false);
    PERFORM set_config('test.robinson_user_id', v_user_id::TEXT, false);

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Register Check Not Listed', 'P3_Robinson', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 28.6: Test funcional - Verificar estado Robinson (puede contactar)
-- ============================================================================

\echo ''
\echo '--- Test 28.6: Verificar estado Robinson (puede contactar) ---'

DO $$
DECLARE
    v_result JSON;
    v_can_contact BOOLEAN;
    v_needs_check BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Verificar el teléfono registrado en test anterior
    v_result := check_robinson_status('+34600111222', 'phone', NULL);

    v_can_contact := (v_result->>'can_contact')::BOOLEAN;
    v_needs_check := (v_result->>'needs_new_check')::BOOLEAN;

    IF v_can_contact = true AND v_needs_check = false THEN
        v_status := 'PASS';
        v_details := format('Puede contactar: %s, Mensaje: %s', v_can_contact, v_result->>'message');
    ELSE
        v_status := 'FAIL';
        v_details := format('Resultado inesperado: %s', v_result::TEXT);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Check Status Can Contact', 'P3_Robinson', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Check Status Can Contact', 'P3_Robinson', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 28.7: Test funcional - Registrar teléfono EN Lista Robinson
-- ============================================================================

\echo ''
\echo '--- Test 28.7: Registrar teléfono EN Lista Robinson ---'

DO $$
DECLARE
    v_user_id UUID;
    v_check_id UUID;
    v_status TEXT;
    v_details TEXT;
BEGIN
    v_user_id := current_setting('test.robinson_user_id', true)::UUID;
    PERFORM set_current_user(v_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Registrar consulta: teléfono SÍ está en Lista Robinson
    v_check_id := register_robinson_check(
        '+34600999888',
        true,  -- SÍ está en Lista Robinson (BLOQUEADO)
        'phone',
        NULL,
        NULL,
        '200',
        '{"status": "registered", "timestamp": "2025-12-03T12:00:00Z"}'
    );

    IF v_check_id IS NOT NULL THEN
        v_status := 'PASS';
        v_details := format('Teléfono bloqueado registrado: %s', v_check_id);
    ELSE
        v_status := 'FAIL';
        v_details := 'No se pudo registrar consulta';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Register Check Listed', 'P3_Robinson', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Register Check Listed', 'P3_Robinson', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 28.8: Test funcional - Verificar bloqueo por Lista Robinson
-- ============================================================================

\echo ''
\echo '--- Test 28.8: Verificar bloqueo por Lista Robinson ---'

DO $$
DECLARE
    v_result JSON;
    v_can_contact BOOLEAN;
    v_is_in_robinson BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Verificar el teléfono bloqueado
    v_result := check_robinson_status('+34600999888', 'phone', NULL);

    v_can_contact := (v_result->>'can_contact')::BOOLEAN;
    v_is_in_robinson := (v_result->>'is_in_robinson')::BOOLEAN;

    IF v_can_contact = false AND v_is_in_robinson = true THEN
        v_status := 'PASS';
        v_details := format('BLOQUEADO correctamente: %s', v_result->>'message');
    ELSE
        v_status := 'FAIL';
        v_details := format('Debería estar bloqueado: %s', v_result::TEXT);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Check Status Blocked', 'P3_Robinson', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Check Status Blocked', 'P3_Robinson', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 28.9: Test funcional - Teléfono sin consulta previa
-- ============================================================================

\echo ''
\echo '--- Test 28.9: Teléfono sin consulta previa ---'

DO $$
DECLARE
    v_result JSON;
    v_needs_check BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Verificar teléfono nunca consultado
    v_result := check_robinson_status('+34611222333', 'phone', NULL);

    v_needs_check := (v_result->>'needs_new_check')::BOOLEAN;

    IF v_needs_check = true THEN
        v_status := 'PASS';
        v_details := format('Requiere verificación correctamente: %s', v_result->>'message');
    ELSE
        v_status := 'FAIL';
        v_details := format('Debería requerir verificación: %s', v_result::TEXT);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Check Needs Verification', 'P3_Robinson', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Check Needs Verification', 'P3_Robinson', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 28.10: Verificar índices de rendimiento
-- ============================================================================

\echo ''
\echo '--- Test 28.10: Verificar índices ---'

DO $$
DECLARE
    v_idx_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(*) INTO v_idx_count
    FROM pg_indexes
    WHERE tablename = 'robinson_checks' AND indexname LIKE 'idx_robinson%';

    IF v_idx_count >= 5 THEN
        v_status := 'PASS';
        v_details := format('%s índices de rendimiento encontrados', v_idx_count);
    ELSE
        v_status := 'FAIL';
        v_details := format('Solo %s índices (mínimo 5)', v_idx_count);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Performance Indexes', 'P3_Robinson', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 28.11: Verificar vista de compliance
-- ============================================================================

\echo ''
\echo '--- Test 28.11: Verificar vista de compliance ---'

DO $$
DECLARE
    v_view_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.views
        WHERE table_name = 'v_robinson_compliance_summary'
    ) INTO v_view_exists;

    IF v_view_exists THEN
        v_status := 'PASS';
        v_details := 'Vista v_robinson_compliance_summary existe';
    ELSE
        v_status := 'FAIL';
        v_details := 'Vista v_robinson_compliance_summary no encontrada';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Compliance View', 'P3_Robinson', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 28.12: Verificar registro en audit_log
-- ============================================================================

\echo ''
\echo '--- Test 28.12: Verificar registro en audit_log ---'

DO $$
DECLARE
    v_audit_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(*) INTO v_audit_count
    FROM audit_log
    WHERE action = 'ROBINSON_CHECK'
    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '5 minutes';

    IF v_audit_count >= 2 THEN
        v_status := 'PASS';
        v_details := format('%s registros de auditoría ROBINSON_CHECK encontrados', v_audit_count);
    ELSE
        v_status := 'FAIL';
        v_details := format('Solo %s registros (esperados al menos 2)', v_audit_count);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Audit Log Entries', 'P3_Robinson', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- RESUMEN
-- ============================================================================

\echo ''
\echo '=============================================='
\echo 'RESUMEN TEST 28: LISTA ROBINSON (P3)'
\echo '=============================================='

SELECT
    test_category,
    COUNT(*) as total_tests,
    SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
    SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed,
    SUM(CASE WHEN status = 'SKIP' THEN 1 ELSE 0 END) as skipped
FROM test_results
WHERE test_category = 'P3_Robinson'
GROUP BY test_category;

\echo ''
\echo 'Detalle de tests:'

SELECT test_name, status, details
FROM test_results
WHERE test_category = 'P3_Robinson'
ORDER BY test_id;

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
