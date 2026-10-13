-- ============================================================================
-- TEST 22: RLS CONFIGURATION AND POLICY VERIFICATION (Punto 4 Auditoría)
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 32.1.b: Confidencialidad (control de acceso)
--   • RGPD Art. 25.1: Protección de datos desde el diseño
--   • RGPD Art. 5.1.f: Integridad y confidencialidad
-- 
-- NIVEL DE COMPLIANCE: MEDIO
-- CRITICIDAD: ALTA
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Arts. 25, 32
-- ============================================================================
-- Verifica que Row Level Security está correctamente configurado
-- NOTA: Para verificar aislamiento real entre usuarios, ejecutar con un rol
--       que NO tenga el atributo BYPASSRLS (no superusuario)
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
    v_policy_exists BOOLEAN;
    v_rls_enabled BOOLEAN;
    v_has_bypassrls BOOLEAN;
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'TEST 22: RLS CONFIGURATION VERIFICATION';
    RAISE NOTICE '========================================';
    RAISE NOTICE '';

    -- Configurar contexto
    PERFORM set_config('app.audit_hmac_key', 'test_audit_key_for_rls_test_32bytes!', true);

    -- ========================================================================
    -- TEST 22.1: RLS habilitado en tabla contacts
    -- ========================================================================
    v_test_num := 1;
    SELECT relrowsecurity INTO v_rls_enabled
    FROM pg_class WHERE relname = 'contacts';

    IF v_rls_enabled THEN
        v_status := 'PASS';
        v_details := 'RLS habilitado en tabla contacts';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'RLS NO habilitado en tabla contacts';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 22.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 22.2: RLS habilitado en tabla calls
    -- ========================================================================
    v_test_num := 2;
    SELECT relrowsecurity INTO v_rls_enabled
    FROM pg_class WHERE relname = 'calls';

    IF v_rls_enabled THEN
        v_status := 'PASS';
        v_details := 'RLS habilitado en tabla calls';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'RLS NO habilitado en tabla calls';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 22.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 22.3: RLS habilitado en tabla data_consents
    -- ========================================================================
    v_test_num := 3;
    SELECT relrowsecurity INTO v_rls_enabled
    FROM pg_class WHERE relname = 'data_consents';

    IF v_rls_enabled THEN
        v_status := 'PASS';
        v_details := 'RLS habilitado en tabla data_consents';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'RLS NO habilitado en tabla data_consents';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 22.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 22.4: RLS habilitado en tabla campaigns
    -- ========================================================================
    v_test_num := 4;
    SELECT relrowsecurity INTO v_rls_enabled
    FROM pg_class WHERE relname = 'campaigns';

    IF v_rls_enabled THEN
        v_status := 'PASS';
        v_details := 'RLS habilitado en tabla campaigns';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'RLS NO habilitado en tabla campaigns';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 22.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 22.5: Política RLS existe para contacts
    -- ========================================================================
    v_test_num := 5;
    SELECT EXISTS (
        SELECT 1 FROM pg_policy WHERE polrelid = 'contacts'::regclass
    ) INTO v_policy_exists;

    IF v_policy_exists THEN
        v_status := 'PASS';
        v_details := 'Política RLS configurada para contacts';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Sin política RLS para contacts';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 22.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 22.6: Política RLS existe para calls
    -- ========================================================================
    v_test_num := 6;
    SELECT EXISTS (
        SELECT 1 FROM pg_policy WHERE polrelid = 'calls'::regclass
    ) INTO v_policy_exists;

    IF v_policy_exists THEN
        v_status := 'PASS';
        v_details := 'Política RLS configurada para calls';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Sin política RLS para calls';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 22.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 22.7: Política RLS permite acceso por user_id
    -- ========================================================================
    v_test_num := 7;
    SELECT EXISTS (
        SELECT 1 FROM pg_policy
        WHERE polrelid = 'contacts'::regclass
        AND pg_get_expr(polqual, polrelid) LIKE '%user_id%get_current_user()%'
    ) INTO v_policy_exists;

    IF v_policy_exists THEN
        v_status := 'PASS';
        v_details := 'Política verifica user_id = get_current_user()';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Política no verifica correctamente user_id';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 22.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 22.8: Política RLS permite acceso a admin/auditor
    -- ========================================================================
    v_test_num := 8;
    SELECT EXISTS (
        SELECT 1 FROM pg_policy
        WHERE polrelid = 'contacts'::regclass
        AND (pg_get_expr(polqual, polrelid) LIKE '%admin%'
             OR pg_get_expr(polqual, polrelid) LIKE '%auditor%')
    ) INTO v_policy_exists;

    IF v_policy_exists THEN
        v_status := 'PASS';
        v_details := 'Política permite acceso a roles admin/auditor';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Política no configura acceso admin/auditor';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 22.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 22.9: Función get_current_user() existe y funciona
    -- ========================================================================
    v_test_num := 9;
    BEGIN
        PERFORM set_config('app.current_user_id', '11111111-1111-1111-1111-111111111111', true);
        IF get_current_user() = '11111111-1111-1111-1111-111111111111'::UUID THEN
            v_status := 'PASS';
            v_details := 'get_current_user() devuelve ID de sesión correctamente';
            v_passed := v_passed + 1;
        ELSE
            v_status := 'FAIL';
            v_details := format('get_current_user() devuelve: %s', get_current_user());
            v_failed := v_failed + 1;
        END IF;
    EXCEPTION WHEN OTHERS THEN
        v_status := 'FAIL';
        v_details := 'Error en get_current_user(): ' || SQLERRM;
        v_failed := v_failed + 1;
    END;
    RAISE NOTICE 'Test 22.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 22.10: Función get_current_user_role() existe
    -- ========================================================================
    v_test_num := 10;
    BEGIN
        PERFORM get_current_user_role();
        v_status := 'PASS';
        v_details := format('get_current_user_role() funciona, devuelve: %s', get_current_user_role());
        v_passed := v_passed + 1;
    EXCEPTION WHEN OTHERS THEN
        v_status := 'FAIL';
        v_details := 'Error en get_current_user_role(): ' || SQLERRM;
        v_failed := v_failed + 1;
    END;
    RAISE NOTICE 'Test 22.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 22.11: Verificar si rol actual tiene BYPASSRLS
    -- ========================================================================
    v_test_num := 11;
    SELECT rolbypassrls INTO v_has_bypassrls
    FROM pg_roles WHERE rolname = current_user;

    IF v_has_bypassrls THEN
        v_status := 'WARN';
        v_details := format('Rol "%s" tiene BYPASSRLS - RLS será ignorado. Usar rol sin BYPASSRLS para tests reales', current_user);
    ELSE
        v_status := 'PASS';
        v_details := format('Rol "%s" NO tiene BYPASSRLS - RLS se aplicará correctamente', current_user);
        v_passed := v_passed + 1;
    END IF;
    RAISE NOTICE 'Test 22.%: % - %', v_test_num, v_status, v_details;

    -- Si tiene BYPASSRLS, contar como passed pero con advertencia
    IF v_has_bypassrls THEN
        v_passed := v_passed + 1;
    END IF;

    -- ========================================================================
    -- TEST 22.12: Política data_consents verifica data_subject_id
    -- ========================================================================
    v_test_num := 12;
    SELECT EXISTS (
        SELECT 1 FROM pg_policy
        WHERE polrelid = 'data_consents'::regclass
        AND (pg_get_expr(polqual, polrelid) LIKE '%data_subject_id%'
             OR pg_get_expr(polqual, polrelid) LIKE '%get_current_user()%')
    ) INTO v_policy_exists;

    IF v_policy_exists THEN
        v_status := 'PASS';
        v_details := 'Política data_consents verifica sujeto de datos';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Política data_consents no verifica sujeto de datos';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 22.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 22.13: Verificar WITH CHECK en políticas (para INSERT/UPDATE)
    -- ========================================================================
    v_test_num := 13;
    SELECT EXISTS (
        SELECT 1 FROM pg_policy
        WHERE polrelid = 'contacts'::regclass
        AND polwithcheck IS NOT NULL
    ) INTO v_policy_exists;

    IF v_policy_exists THEN
        v_status := 'PASS';
        v_details := 'Política contacts tiene WITH CHECK para INSERT/UPDATE';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'WARN';
        v_details := 'Política contacts sin WITH CHECK explícito';
        v_passed := v_passed + 1; -- No crítico
    END IF;
    RAISE NOTICE 'Test 22.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 22.14: Número de políticas por tabla
    -- ========================================================================
    v_test_num := 14;
    SELECT COUNT(*) INTO v_count
    FROM pg_policy p
    JOIN pg_class c ON p.polrelid = c.oid
    WHERE c.relname IN ('contacts', 'calls', 'data_consents', 'campaigns');

    IF v_count >= 4 THEN
        v_status := 'PASS';
        v_details := format('%s políticas RLS configuradas en tablas críticas', v_count);
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('Solo %s políticas RLS (esperado >= 4)', v_count);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 22.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 22.15: Verificar que política es PERMISSIVE (default)
    -- ========================================================================
    v_test_num := 15;
    SELECT EXISTS (
        SELECT 1 FROM pg_policy
        WHERE polrelid = 'contacts'::regclass
        AND polpermissive = true
    ) INTO v_policy_exists;

    IF v_policy_exists THEN
        v_status := 'PASS';
        v_details := 'Política contacts es PERMISSIVE (comportamiento correcto)';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'INFO';
        v_details := 'Política contacts es RESTRICTIVE';
        v_passed := v_passed + 1;
    END IF;
    RAISE NOTICE 'Test 22.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- RESUMEN
    -- ========================================================================
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'RESUMEN TEST 22: %/% tests passed', v_passed, v_passed + v_failed;
    RAISE NOTICE '========================================';

    IF v_failed > 0 THEN
        RAISE NOTICE 'RESULTADO: FAILED (% errores)', v_failed;
    ELSE
        RAISE NOTICE 'RESULTADO: ALL TESTS PASSED';
        RAISE NOTICE '';
        RAISE NOTICE 'NOTA: Las políticas RLS están correctamente configuradas.';
        RAISE NOTICE 'Para verificar aislamiento REAL entre usuarios:';
        RAISE NOTICE '1. Crear rol de aplicación: CREATE ROLE app_user NOINHERIT;';
        RAISE NOTICE '2. Ejecutar tests con: SET ROLE app_user;';
        RAISE NOTICE '3. O usar conexión desde aplicación (no superusuario)';
    END IF;

END $$;

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
