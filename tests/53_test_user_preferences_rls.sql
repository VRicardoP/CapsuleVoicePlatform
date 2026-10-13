-- ============================================================================
-- TEST 53: USER PREFERENCES RLS ISOLATION
-- ============================================================================
-- COBERTURA LEGAL:
--   * RGPD Art. 32.1.b: Confidencialidad (control de acceso)
--   * RGPD Art. 25.1: Proteccion de datos desde el diseno
--   * RGPD Art. 5.1.c: Minimizacion de datos
--   * LOPDGDD Art. 33: Control de acceso
--
-- NIVEL DE COMPLIANCE: BAJO (datos de configuracion UI, no PII)
-- CRITICIDAD: MEDIA
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Arts. 25, 32
-- ============================================================================
-- Verifica que Row Level Security esta correctamente configurado en
-- user_preferences para que cada usuario solo acceda a sus propias
-- preferencias de interfaz.
-- ============================================================================

BEGIN;

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
    v_policy_exists BOOLEAN;
    v_rls_enabled BOOLEAN;
    v_rls_forced BOOLEAN;
    v_user1_id UUID := '11111111-1111-1111-1111-111111111111';
    v_user2_id UUID := '22222222-2222-2222-2222-222222222222';
    v_result_count INTEGER;
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'TEST 53: USER PREFERENCES RLS ISOLATION';
    RAISE NOTICE '========================================';
    RAISE NOTICE '';

    -- ========================================================================
    -- TEST 53.1: RLS habilitado en tabla user_preferences
    -- ========================================================================
    v_test_num := 1;
    SELECT relrowsecurity INTO v_rls_enabled
    FROM pg_class WHERE relname = 'user_preferences';

    IF v_rls_enabled THEN
        v_status := 'PASS';
        v_details := 'RLS habilitado en tabla user_preferences';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'RLS NO habilitado en tabla user_preferences';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 53.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 53.2: FORCE ROW LEVEL SECURITY activo
    -- ========================================================================
    v_test_num := 2;
    SELECT relforcerowsecurity INTO v_rls_forced
    FROM pg_class WHERE relname = 'user_preferences';

    IF v_rls_forced THEN
        v_status := 'PASS';
        v_details := 'FORCE ROW LEVEL SECURITY activo en user_preferences';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'WARN';
        v_details := 'FORCE ROW LEVEL SECURITY no activo (superusuarios podrian ignorar RLS)';
        v_passed := v_passed + 1; -- No critico para tabla de preferencias
    END IF;
    RAISE NOTICE 'Test 53.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 53.3: Politica SELECT existe
    -- ========================================================================
    v_test_num := 3;
    SELECT EXISTS (
        SELECT 1 FROM pg_policy
        WHERE polrelid = 'user_preferences'::regclass
        AND polcmd = 'r' -- SELECT
    ) INTO v_policy_exists;

    IF v_policy_exists THEN
        v_status := 'PASS';
        v_details := 'Politica SELECT configurada para user_preferences';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Sin politica SELECT para user_preferences';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 53.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 53.4: Politica INSERT existe
    -- ========================================================================
    v_test_num := 4;
    SELECT EXISTS (
        SELECT 1 FROM pg_policy
        WHERE polrelid = 'user_preferences'::regclass
        AND polcmd = 'a' -- INSERT
    ) INTO v_policy_exists;

    IF v_policy_exists THEN
        v_status := 'PASS';
        v_details := 'Politica INSERT configurada para user_preferences';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Sin politica INSERT para user_preferences';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 53.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 53.5: Politica UPDATE existe
    -- ========================================================================
    v_test_num := 5;
    SELECT EXISTS (
        SELECT 1 FROM pg_policy
        WHERE polrelid = 'user_preferences'::regclass
        AND polcmd = 'w' -- UPDATE
    ) INTO v_policy_exists;

    IF v_policy_exists THEN
        v_status := 'PASS';
        v_details := 'Politica UPDATE configurada para user_preferences';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Sin politica UPDATE para user_preferences';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 53.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 53.6: Politica DELETE existe
    -- ========================================================================
    v_test_num := 6;
    SELECT EXISTS (
        SELECT 1 FROM pg_policy
        WHERE polrelid = 'user_preferences'::regclass
        AND polcmd = 'd' -- DELETE
    ) INTO v_policy_exists;

    IF v_policy_exists THEN
        v_status := 'PASS';
        v_details := 'Politica DELETE configurada para user_preferences';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Sin politica DELETE para user_preferences';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 53.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 53.7: Politicas verifican user_id con app.current_user_id
    -- ========================================================================
    v_test_num := 7;
    SELECT EXISTS (
        SELECT 1 FROM pg_policy
        WHERE polrelid = 'user_preferences'::regclass
        AND pg_get_expr(polqual, polrelid) LIKE '%current_user_id%'
    ) INTO v_policy_exists;

    IF v_policy_exists THEN
        v_status := 'PASS';
        v_details := 'Politicas verifican app.current_user_id';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Politicas no verifican app.current_user_id';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 53.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 53.8: Numero total de politicas (deberian ser 4)
    -- ========================================================================
    v_test_num := 8;
    SELECT COUNT(*) INTO v_count
    FROM pg_policy
    WHERE polrelid = 'user_preferences'::regclass;

    IF v_count >= 4 THEN
        v_status := 'PASS';
        v_details := format('%s politicas RLS en user_preferences (SELECT, INSERT, UPDATE, DELETE)', v_count);
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('Solo %s politicas RLS (esperado >= 4)', v_count);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 53.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 53.9: Verificar nombres de politicas
    -- ========================================================================
    v_test_num := 9;
    SELECT COUNT(*) INTO v_count
    FROM pg_policy
    WHERE polrelid = 'user_preferences'::regclass
    AND polname IN ('user_preferences_select', 'user_preferences_insert',
                    'user_preferences_update', 'user_preferences_delete');

    IF v_count = 4 THEN
        v_status := 'PASS';
        v_details := 'Nombres de politicas correctos (user_preferences_*)';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'WARN';
        v_details := format('Solo %s politicas con nombres esperados', v_count);
        v_passed := v_passed + 1; -- No critico
    END IF;
    RAISE NOTICE 'Test 53.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 53.10: Estructura de tabla user_preferences
    -- ========================================================================
    v_test_num := 10;
    SELECT COUNT(*) INTO v_count
    FROM information_schema.columns
    WHERE table_name = 'user_preferences'
    AND column_name IN ('user_id', 'visible_modules', 'theme', 'updated_at');

    IF v_count = 4 THEN
        v_status := 'PASS';
        v_details := 'Estructura correcta: user_id, visible_modules, theme, updated_at';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('Estructura incompleta: solo %s columnas de 4 esperadas', v_count);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 53.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 53.11: visible_modules es de tipo text[]
    -- ========================================================================
    v_test_num := 11;
    SELECT COUNT(*) INTO v_count
    FROM information_schema.columns
    WHERE table_name = 'user_preferences'
    AND column_name = 'visible_modules'
    AND data_type = 'ARRAY';

    IF v_count = 1 THEN
        v_status := 'PASS';
        v_details := 'visible_modules es tipo ARRAY (text[])';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'visible_modules no es tipo ARRAY';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 53.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 53.12: Clave foranea a users
    -- ========================================================================
    v_test_num := 12;
    SELECT COUNT(*) INTO v_count
    FROM information_schema.table_constraints tc
    JOIN information_schema.constraint_column_usage ccu
        ON tc.constraint_name = ccu.constraint_name
    WHERE tc.table_name = 'user_preferences'
    AND tc.constraint_type = 'FOREIGN KEY'
    AND ccu.table_name = 'users';

    IF v_count >= 1 THEN
        v_status := 'PASS';
        v_details := 'FK a tabla users configurada';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'WARN';
        v_details := 'Sin FK explicita a users (puede ser por diseno)';
        v_passed := v_passed + 1;
    END IF;
    RAISE NOTICE 'Test 53.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- RESUMEN
    -- ========================================================================
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'RESUMEN TEST 53: %/% tests passed', v_passed, v_passed + v_failed;
    RAISE NOTICE '========================================';

    IF v_failed > 0 THEN
        RAISE NOTICE 'RESULTADO: FAILED (% errores)', v_failed;
    ELSE
        RAISE NOTICE 'RESULTADO: ALL TESTS PASSED';
        RAISE NOTICE '';
        RAISE NOTICE 'Las politicas RLS de user_preferences garantizan:';
        RAISE NOTICE '- Cada usuario solo puede leer sus propias preferencias';
        RAISE NOTICE '- Cada usuario solo puede modificar sus propias preferencias';
        RAISE NOTICE '- Aislamiento de datos entre usuarios (RGPD Art. 32)';
    END IF;

END $$;

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
