-- ============================================================================
-- TEST 24: PERFORMANCE OPTIMIZATION (Punto 5 Auditoría)
-- ============================================================================
-- COBERTURA LEGAL:
--   • No verifica requisitos legales (optimización técnica)
-- 
-- NIVEL DE COMPLIANCE: N/A
-- CRITICIDAD: BAJA (técnico)
-- ============================================================================
-- Verifica índices, configuración de particionamiento y funciones optimizadas
-- ============================================================================

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

DO $$
DECLARE
    v_test_num INTEGER := 0;
    v_passed INTEGER := 0;
    v_failed INTEGER := 0;
    v_status VARCHAR(10);
    v_details TEXT;
    v_count INTEGER;
    v_volatility TEXT;
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'TEST 24: PERFORMANCE OPTIMIZATION';
    RAISE NOTICE '========================================';
    RAISE NOTICE '';

    -- ========================================================================
    -- TEST 24.1: Índice compuesto para dashboard (user_status_date)
    -- ========================================================================
    v_test_num := 1;
    IF EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'idx_calls_user_status_date'
    ) THEN
        v_status := 'PASS';
        v_details := 'Índice idx_calls_user_status_date creado';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Índice idx_calls_user_status_date NO existe';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 24.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 24.2: Índice para reportes por rango de fechas
    -- ========================================================================
    v_test_num := 2;
    IF EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'idx_calls_date_range'
    ) THEN
        v_status := 'PASS';
        v_details := 'Índice idx_calls_date_range creado';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Índice idx_calls_date_range NO existe';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 24.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 24.3: Índice BRIN para audit_log (eficiente para tablas grandes)
    -- ========================================================================
    v_test_num := 3;
    IF EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'idx_audit_brin_date'
    ) THEN
        v_status := 'PASS';
        v_details := 'Índice BRIN idx_audit_brin_date creado';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Índice BRIN idx_audit_brin_date NO existe';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 24.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 24.4: Índice para historial de contactos
    -- ========================================================================
    v_test_num := 4;
    IF EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'idx_calls_contact_date'
    ) THEN
        v_status := 'PASS';
        v_details := 'Índice idx_calls_contact_date creado';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Índice idx_calls_contact_date NO existe';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 24.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 24.5: Índice para conversiones por fecha
    -- ========================================================================
    v_test_num := 5;
    IF EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'idx_conversions_date'
    ) THEN
        v_status := 'PASS';
        v_details := 'Índice idx_conversions_date creado';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Índice idx_conversions_date NO existe';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 24.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 24.6: Tabla partition_config existe
    -- ========================================================================
    v_test_num := 6;
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'partition_config'
    ) THEN
        v_status := 'PASS';
        v_details := 'Tabla partition_config para documentación de particionamiento';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Tabla partition_config NO existe';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 24.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 24.7: Configuración de particionamiento documentada
    -- ========================================================================
    v_test_num := 7;
    SELECT COUNT(*) INTO v_count FROM partition_config
    WHERE table_name IN ('calls', 'audit_log');

    IF v_count >= 2 THEN
        v_status := 'PASS';
        v_details := format('%s tablas con estrategia de particionamiento documentada', v_count);
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Estrategia de particionamiento no documentada';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 24.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 24.8: Tabla connection_pool_config existe
    -- ========================================================================
    v_test_num := 8;
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'connection_pool_config'
    ) THEN
        v_status := 'PASS';
        v_details := 'Tabla connection_pool_config para documentación de pooling';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Tabla connection_pool_config NO existe';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 24.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 24.9: Configuración de pooling por entorno
    -- ========================================================================
    v_test_num := 9;
    SELECT COUNT(*) INTO v_count FROM connection_pool_config
    WHERE environment IN ('development', 'staging', 'production');

    IF v_count >= 3 THEN
        v_status := 'PASS';
        v_details := 'Configuración de pooling para dev/staging/prod documentada';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('Solo %s entornos configurados (esperado 3)', v_count);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 24.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 24.10: Función get_current_user() es STABLE
    -- ========================================================================
    v_test_num := 10;
    SELECT p.provolatile INTO v_volatility
    FROM pg_proc p
    WHERE p.proname = 'get_current_user'
    AND p.proargtypes = '';

    IF v_volatility = 's' THEN
        v_status := 'PASS';
        v_details := 'get_current_user() marcada como STABLE';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('get_current_user() es %s (esperado STABLE)',
            CASE v_volatility WHEN 'i' THEN 'IMMUTABLE' WHEN 'v' THEN 'VOLATILE' ELSE 'UNKNOWN' END);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 24.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 24.11: Función mask_pii() es IMMUTABLE
    -- ========================================================================
    v_test_num := 11;
    SELECT p.provolatile INTO v_volatility
    FROM pg_proc p
    WHERE p.proname = 'mask_pii';

    IF v_volatility = 'i' THEN
        v_status := 'PASS';
        v_details := 'mask_pii() marcada como IMMUTABLE';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('mask_pii() es %s (esperado IMMUTABLE)',
            CASE v_volatility WHEN 's' THEN 'STABLE' WHEN 'v' THEN 'VOLATILE' ELSE 'UNKNOWN' END);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 24.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 24.12: Función format_currency() existe y es IMMUTABLE
    -- ========================================================================
    v_test_num := 12;
    SELECT p.provolatile INTO v_volatility
    FROM pg_proc p
    WHERE p.proname = 'format_currency';

    IF v_volatility = 'i' THEN
        v_status := 'PASS';
        v_details := 'format_currency() existe y es IMMUTABLE';
        v_passed := v_passed + 1;
    ELSIF v_volatility IS NULL THEN
        v_status := 'FAIL';
        v_details := 'format_currency() NO existe';
        v_failed := v_failed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'format_currency() no es IMMUTABLE';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 24.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 24.13: Vista v_index_usage existe
    -- ========================================================================
    v_test_num := 13;
    IF EXISTS (
        SELECT 1 FROM information_schema.views
        WHERE table_name = 'v_index_usage'
    ) THEN
        v_status := 'PASS';
        v_details := 'Vista v_index_usage para monitorización de índices';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Vista v_index_usage NO existe';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 24.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 24.14: Vista v_large_tables existe
    -- ========================================================================
    v_test_num := 14;
    IF EXISTS (
        SELECT 1 FROM information_schema.views
        WHERE table_name = 'v_large_tables'
    ) THEN
        v_status := 'PASS';
        v_details := 'Vista v_large_tables para identificar candidatos a particionamiento';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Vista v_large_tables NO existe';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 24.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 24.15: Función perform_maintenance() existe
    -- ========================================================================
    v_test_num := 15;
    IF EXISTS (
        SELECT 1 FROM pg_proc WHERE proname = 'perform_maintenance'
    ) THEN
        v_status := 'PASS';
        v_details := 'Función perform_maintenance() para mantenimiento programado';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Función perform_maintenance() NO existe';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 24.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 24.16: Total de índices en tablas principales
    -- ========================================================================
    v_test_num := 16;
    SELECT COUNT(*) INTO v_count
    FROM pg_indexes
    WHERE tablename IN ('calls', 'contacts', 'audit_log', 'conversions', 'campaigns');

    IF v_count >= 15 THEN
        v_status := 'PASS';
        v_details := format('%s índices en tablas principales', v_count);
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('Solo %s índices (esperado >= 15)', v_count);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 24.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 24.17: Índices parciales con WHERE deleted_at IS NULL
    -- ========================================================================
    v_test_num := 17;
    SELECT COUNT(*) INTO v_count
    FROM pg_indexes
    WHERE indexdef LIKE '%WHERE%deleted_at IS NULL%';

    IF v_count >= 4 THEN
        v_status := 'PASS';
        v_details := format('%s índices parciales excluyendo soft-deleted', v_count);
        v_passed := v_passed + 1;
    ELSE
        v_status := 'WARN';
        v_details := format('%s índices parciales (recomendado >= 4)', v_count);
        v_passed := v_passed + 1; -- No crítico
    END IF;
    RAISE NOTICE 'Test 24.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 24.18: Función days_since() es IMMUTABLE
    -- ========================================================================
    v_test_num := 18;
    SELECT p.provolatile INTO v_volatility
    FROM pg_proc p
    WHERE p.proname = 'days_since';

    IF v_volatility = 'i' THEN
        v_status := 'PASS';
        v_details := 'days_since() es IMMUTABLE';
        v_passed := v_passed + 1;
    ELSIF v_volatility IS NULL THEN
        v_status := 'FAIL';
        v_details := 'days_since() NO existe';
        v_failed := v_failed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'days_since() no es IMMUTABLE';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 24.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 24.19: Verificar uso de índices (v_index_usage funciona)
    -- ========================================================================
    v_test_num := 19;
    BEGIN
        SELECT COUNT(*) INTO v_count FROM v_index_usage;
        v_status := 'PASS';
        v_details := format('v_index_usage devuelve %s índices', v_count);
        v_passed := v_passed + 1;
    EXCEPTION WHEN OTHERS THEN
        v_status := 'FAIL';
        v_details := 'Error consultando v_index_usage: ' || SQLERRM;
        v_failed := v_failed + 1;
    END;
    RAISE NOTICE 'Test 24.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 24.20: Verificar tablas grandes (v_large_tables funciona)
    -- ========================================================================
    v_test_num := 20;
    BEGIN
        SELECT COUNT(*) INTO v_count FROM v_large_tables;
        v_status := 'PASS';
        v_details := format('v_large_tables analiza %s tablas', v_count);
        v_passed := v_passed + 1;
    EXCEPTION WHEN OTHERS THEN
        v_status := 'FAIL';
        v_details := 'Error consultando v_large_tables: ' || SQLERRM;
        v_failed := v_failed + 1;
    END;
    RAISE NOTICE 'Test 24.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- RESUMEN
    -- ========================================================================
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'RESUMEN TEST 24: %/% tests passed', v_passed, v_passed + v_failed;
    RAISE NOTICE '========================================';

    IF v_failed > 0 THEN
        RAISE NOTICE 'RESULTADO: FAILED (% errores)', v_failed;
    ELSE
        RAISE NOTICE 'RESULTADO: ALL TESTS PASSED';
    END IF;

END $$;

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
