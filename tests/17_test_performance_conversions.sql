-- ============================================================================
-- TEST 17: PERFORMANCE METRICS Y CONVERSIONS
-- ============================================================================
-- COBERTURA LEGAL:
--   • No verifica requisitos legales directos (métricas de negocio)
-- 
-- NIVEL DE COMPLIANCE: N/A
-- CRITICIDAD: BAJA (técnico)
-- ============================================================================
-- Verifica las tablas de métricas de rendimiento y conversiones
-- Alimentan los gráficos del dashboard (radar, conversión trends)
-- Ejecutar: psql -U postgres -d sfera -f 17_test_performance_conversions.sql
-- ============================================================================

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '=============================================='
\echo 'TEST 17: PERFORMANCE METRICS & CONVERSIONS'
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

-- Crear clave de cifrado temporal para tests
DO $$
BEGIN
    INSERT INTO encryption_keys (key_id, encrypted_key, is_active, kms_provider, activated_at)
    VALUES (
        'test_key_perf_' || substring(gen_random_uuid()::TEXT, 1, 8),
        pgp_sym_encrypt(encode(gen_random_bytes(32), 'hex'), current_setting('app.kms_master_key'), 'cipher-algo=aes256'),
        true,
        'hashicorp-vault',
        CURRENT_TIMESTAMP
    );
EXCEPTION WHEN OTHERS THEN
    NULL;
END $$;

-- ============================================================================
-- TEST 17.1: Tabla performance_metrics existe con estructura correcta
-- ============================================================================

\echo ''
\echo '--- Test 17.1: Estructura performance_metrics ---'

DO $$
DECLARE
    v_table_exists BOOLEAN;
    v_has_fcr BOOLEAN;
    v_has_satisfaction BOOLEAN;
    v_has_response BOOLEAN;
    v_has_accuracy BOOLEAN;
    v_has_conversion BOOLEAN;
    v_has_handle_time BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Verificar tabla
    SELECT EXISTS(
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'performance_metrics'
    ) INTO v_table_exists;

    -- Verificar columnas
    SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name = 'performance_metrics' AND column_name = 'first_call_resolution') INTO v_has_fcr;
    SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name = 'performance_metrics' AND column_name = 'satisfaction_score') INTO v_has_satisfaction;
    SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name = 'performance_metrics' AND column_name = 'response_time_score') INTO v_has_response;
    SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name = 'performance_metrics' AND column_name = 'ai_accuracy_score') INTO v_has_accuracy;
    SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name = 'performance_metrics' AND column_name = 'conversion_rate') INTO v_has_conversion;
    SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name = 'performance_metrics' AND column_name = 'avg_handle_time_score') INTO v_has_handle_time;

    IF v_table_exists AND v_has_fcr AND v_has_satisfaction AND v_has_response AND v_has_accuracy AND v_has_conversion AND v_has_handle_time THEN
        v_status := 'PASS';
        v_details := 'performance_metrics has all required columns';
    ELSE
        v_status := 'FAIL';
        v_details := format('Missing - table:%s fcr:%s sat:%s resp:%s acc:%s conv:%s handle:%s',
            v_table_exists, v_has_fcr, v_has_satisfaction, v_has_response, v_has_accuracy, v_has_conversion, v_has_handle_time);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Performance Metrics Structure', 'Performance', v_status, v_details);

    RAISE NOTICE '  [%] Structure: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Performance Metrics Structure', 'Performance', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 17.2: Insertar métricas de rendimiento
-- ============================================================================

\echo ''
\echo '--- Test 17.2: Insertar metricas de rendimiento ---'

DO $$
DECLARE
    v_user_id UUID;
    v_metric_id UUID;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('PERF_METRICS_USER', 'perf_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Insertar métricas
    INSERT INTO performance_metrics (
        user_id, metric_date,
        first_call_resolution, satisfaction_score, response_time_score,
        ai_accuracy_score, conversion_rate, avg_handle_time_score
    )
    VALUES (
        v_user_id, CURRENT_DATE,
        85, 92, 78, 95, 45, 88
    )
    RETURNING id INTO v_metric_id;

    IF v_metric_id IS NOT NULL THEN
        v_status := 'PASS';
        v_details := format('Performance metrics inserted: %s', v_metric_id);
    ELSE
        v_status := 'FAIL';
        v_details := 'Failed to insert performance metrics';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Insert Performance Metrics', 'Performance', v_status, v_details);

    RAISE NOTICE '  [%] Insert: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Insert Performance Metrics', 'Performance', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Insert: Exception - %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 17.3: Validación de rangos (0-100)
-- ============================================================================

\echo ''
\echo '--- Test 17.3: Validacion de rangos 0-100 ---'

DO $$
DECLARE
    v_user_id UUID;
    v_error_raised BOOLEAN := false;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('RANGE_TEST_USER', 'range_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Intentar insertar valor fuera de rango (>100)
    BEGIN
        INSERT INTO performance_metrics (
            user_id, metric_date, satisfaction_score
        )
        VALUES (v_user_id, CURRENT_DATE - INTERVAL '1 day', 150);
    EXCEPTION WHEN OTHERS THEN
        v_error_raised := true;
    END;

    IF v_error_raised THEN
        v_status := 'PASS';
        v_details := 'CHECK constraint correctly rejects values > 100';
    ELSE
        v_status := 'FAIL';
        v_details := 'CHECK constraint did not reject value > 100';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Range Validation', 'Performance', v_status, v_details);

    RAISE NOTICE '  [%] Range: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Range Validation', 'Performance', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 17.4: Unicidad por usuario y fecha
-- ============================================================================

\echo ''
\echo '--- Test 17.4: Unicidad usuario-fecha ---'

DO $$
DECLARE
    v_user_id UUID;
    v_error_raised BOOLEAN := false;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('UNIQUE_TEST_USER', 'unique_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Primera inserción
    INSERT INTO performance_metrics (user_id, metric_date, satisfaction_score)
    VALUES (v_user_id, CURRENT_DATE - INTERVAL '5 days', 80);

    -- Segunda inserción misma fecha (debe fallar)
    BEGIN
        INSERT INTO performance_metrics (user_id, metric_date, satisfaction_score)
        VALUES (v_user_id, CURRENT_DATE - INTERVAL '5 days', 90);
    EXCEPTION WHEN OTHERS THEN
        v_error_raised := true;
    END;

    IF v_error_raised THEN
        v_status := 'PASS';
        v_details := 'UNIQUE constraint prevents duplicate user-date entries';
    ELSE
        v_status := 'FAIL';
        v_details := 'UNIQUE constraint did not prevent duplicate';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('User-Date Uniqueness', 'Performance', v_status, v_details);

    RAISE NOTICE '  [%] Unique: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('User-Date Uniqueness', 'Performance', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 17.5: Tabla conversions existe
-- ============================================================================

\echo ''
\echo '--- Test 17.5: Estructura conversions ---'

DO $$
DECLARE
    v_table_exists BOOLEAN;
    v_has_call_id BOOLEAN;
    v_has_value BOOLEAN;
    v_has_type BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Verificar tabla
    SELECT EXISTS(
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'conversions'
    ) INTO v_table_exists;

    -- Verificar columnas clave
    SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name = 'conversions' AND column_name = 'call_id') INTO v_has_call_id;
    SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name = 'conversions' AND column_name = 'conversion_value') INTO v_has_value;
    SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name = 'conversions' AND column_name = 'conversion_type') INTO v_has_type;

    IF v_table_exists AND v_has_call_id AND v_has_value AND v_has_type THEN
        v_status := 'PASS';
        v_details := 'conversions table has required structure';
    ELSE
        v_status := 'FAIL';
        v_details := format('Missing - table:%s call_id:%s value:%s type:%s',
            v_table_exists, v_has_call_id, v_has_value, v_has_type);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Conversions Structure', 'Performance', v_status, v_details);

    RAISE NOTICE '  [%] Conv Structure: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Conversions Structure', 'Performance', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 17.6: Insertar conversión
-- ============================================================================

\echo ''
\echo '--- Test 17.6: Insertar conversion ---'

DO $$
DECLARE
    v_user_id UUID;
    v_contact_id UUID;
    v_call_id UUID;
    v_conversion_id UUID;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('CONV_USER', 'conv_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Crear contacto
    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_user_id,
        encrypt_pii_with_metadata('Conv Test'),
        encrypt_pii_with_metadata('+34600123456'),
        (secure_hash_with_pepper('+34600123456')).hash
    )
    RETURNING id INTO v_contact_id;

    -- Crear llamada
    INSERT INTO calls (
        user_id, contact_id, call_date, call_time, caller_name_encrypted, caller_phone_encrypted,
        caller_phone_hash, call_timestamp, duration_seconds, status, recording_encrypted
    )
    VALUES (
        v_user_id, v_contact_id, CURRENT_DATE, CURRENT_TIME,
        encrypt_pii_with_metadata('Conv Test'),
        encrypt_pii_with_metadata('+34600123456'),
        (secure_hash_with_pepper('+34600123456')).hash,
        CURRENT_TIMESTAMP, 300, 'completed', false
    )
    RETURNING id INTO v_call_id;

    -- Insertar conversión
    INSERT INTO conversions (
        call_id, user_id, conversion_date,
        conversion_value, conversion_type, product_category
    )
    VALUES (
        v_call_id, v_user_id, CURRENT_DATE,
        1500.00, 'sale', 'Premium Package'
    )
    RETURNING id INTO v_conversion_id;

    IF v_conversion_id IS NOT NULL THEN
        v_status := 'PASS';
        v_details := format('Conversion inserted: %s (value: 1500.00)', v_conversion_id);
    ELSE
        v_status := 'FAIL';
        v_details := 'Failed to insert conversion';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Insert Conversion', 'Performance', v_status, v_details);

    RAISE NOTICE '  [%] Conv Insert: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Insert Conversion', 'Performance', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Conv Insert: Exception - %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 17.7: Tipos de conversión válidos
-- ============================================================================

\echo ''
\echo '--- Test 17.7: Tipos de conversion validos ---'

DO $$
DECLARE
    v_user_id UUID;
    v_contact_id UUID;
    v_call_id UUID;
    v_error_raised BOOLEAN := false;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear datos de prueba
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TYPE_TEST', 'type_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_user_id,
        encrypt_pii_with_metadata('Type Test'),
        encrypt_pii_with_metadata('+34600999888'),
        (secure_hash_with_pepper('+34600999888')).hash
    )
    RETURNING id INTO v_contact_id;

    INSERT INTO calls (
        user_id, contact_id, call_date, call_time, caller_name_encrypted, caller_phone_encrypted,
        caller_phone_hash, call_timestamp, duration_seconds, status, recording_encrypted
    )
    VALUES (
        v_user_id, v_contact_id, CURRENT_DATE, CURRENT_TIME,
        encrypt_pii_with_metadata('Type Test'),
        encrypt_pii_with_metadata('+34600999888'),
        (secure_hash_with_pepper('+34600999888')).hash,
        CURRENT_TIMESTAMP, 60, 'completed', false
    )
    RETURNING id INTO v_call_id;

    -- Intentar tipo inválido
    BEGIN
        INSERT INTO conversions (call_id, user_id, conversion_date, conversion_value, conversion_type)
        VALUES (v_call_id, v_user_id, CURRENT_DATE, 100.00, 'invalid_type');
    EXCEPTION WHEN OTHERS THEN
        v_error_raised := true;
    END;

    IF v_error_raised THEN
        v_status := 'PASS';
        v_details := 'CHECK constraint rejects invalid conversion_type';
    ELSE
        v_status := 'FAIL';
        v_details := 'Invalid conversion_type was accepted';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Conversion Type Validation', 'Performance', v_status, v_details);

    RAISE NOTICE '  [%] Type: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Conversion Type Validation', 'Performance', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 17.8: Cascade delete desde calls a conversions
-- ============================================================================

\echo ''
\echo '--- Test 17.8: Cascade delete calls->conversions ---'

DO $$
DECLARE
    v_user_id UUID;
    v_contact_id UUID;
    v_call_id UUID;
    v_conversion_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear datos
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('CASCADE_CONV', 'casc_conv_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_user_id,
        encrypt_pii_with_metadata('Cascade Conv'),
        encrypt_pii_with_metadata('+34600777666'),
        (secure_hash_with_pepper('+34600777666')).hash
    )
    RETURNING id INTO v_contact_id;

    INSERT INTO calls (
        user_id, contact_id, call_date, call_time, caller_name_encrypted, caller_phone_encrypted,
        caller_phone_hash, call_timestamp, duration_seconds, status, recording_encrypted
    )
    VALUES (
        v_user_id, v_contact_id, CURRENT_DATE, CURRENT_TIME,
        encrypt_pii_with_metadata('Cascade'),
        encrypt_pii_with_metadata('+34600777666'),
        (secure_hash_with_pepper('+34600777666')).hash,
        CURRENT_TIMESTAMP, 120, 'completed', false
    )
    RETURNING id INTO v_call_id;

    INSERT INTO conversions (call_id, user_id, conversion_date, conversion_value, conversion_type)
    VALUES (v_call_id, v_user_id, CURRENT_DATE, 500.00, 'lead');

    -- Eliminar llamada
    DELETE FROM calls WHERE id = v_call_id;

    -- Verificar que conversión se eliminó
    SELECT EXISTS(SELECT 1 FROM conversions WHERE call_id = v_call_id) INTO v_conversion_exists;

    IF NOT v_conversion_exists THEN
        v_status := 'PASS';
        v_details := 'Conversion correctly deleted on call deletion';
    ELSE
        v_status := 'FAIL';
        v_details := 'Conversion orphaned after call deletion';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Cascade Delete Conversion', 'Performance', v_status, v_details);

    RAISE NOTICE '  [%] Cascade: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Cascade Delete Conversion', 'Performance', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 17.9: Indice de rendimiento
-- ============================================================================

\echo ''
\echo '--- Test 17.9: Indice de rendimiento ---'

DO $$
DECLARE
    v_idx_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_performance_user_date'
    ) INTO v_idx_exists;

    IF v_idx_exists THEN
        v_status := 'PASS';
        v_details := 'Performance index idx_performance_user_date exists';
    ELSE
        v_status := 'FAIL';
        v_details := 'Missing performance index';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Performance Index', 'Performance', v_status, v_details);

    RAISE NOTICE '  [%] Index: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Performance Index', 'Performance', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- RESUMEN DE RESULTADOS
-- ============================================================================

\echo ''
\echo '=============================================='
\echo 'RESUMEN TEST 17: PERFORMANCE & CONVERSIONS'
\echo '=============================================='

SELECT
    test_category,
    COUNT(*) as total_tests,
    COUNT(*) FILTER (WHERE status = 'PASS') as passed,
    COUNT(*) FILTER (WHERE status = 'FAIL') as failed,
    COUNT(*) FILTER (WHERE status = 'SKIP') as skipped
FROM test_results
WHERE test_category = 'Performance'
GROUP BY test_category;

SELECT test_name, status, details
FROM test_results
WHERE test_category = 'Performance'
ORDER BY test_id;

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
