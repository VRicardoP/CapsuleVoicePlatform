-- ============================================================================
-- TEST 23: PII MASKING (Punto 4 Auditoría)
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 32.1.a: Seudonimización
--   • RGPD Art. 25.1: Protección desde el diseño
-- 
-- NIVEL DE COMPLIANCE: BAJO (verifica estructura, no efectividad)
-- CRITICIDAD: MEDIA
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Arts. 25, 32
-- ============================================================================
-- Verifica la función mask_pii() para enmascaramiento de datos personales
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
    v_result TEXT;
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'TEST 23: PII MASKING VERIFICATION';
    RAISE NOTICE '========================================';
    RAISE NOTICE '';

    -- ========================================================================
    -- TEST 23.1: Función mask_pii existe
    -- ========================================================================
    v_test_num := 1;
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'mask_pii') THEN
        v_status := 'PASS';
        v_details := 'Función mask_pii() existe';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Función mask_pii() NO existe';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 23.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 23.2: Enmascaramiento de email
    -- ========================================================================
    v_test_num := 2;
    v_result := mask_pii('usuario@dominio.com', 'email');
    IF v_result LIKE 'us%@dominio.com' AND v_result LIKE '%*%' THEN
        v_status := 'PASS';
        v_details := format('Email: usuario@dominio.com -> %s', v_result);
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('Email mal enmascarado: %s', v_result);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 23.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 23.3: Enmascaramiento de teléfono
    -- ========================================================================
    v_test_num := 3;
    v_result := mask_pii('612345678', 'phone');
    IF v_result = '*****5678' THEN
        v_status := 'PASS';
        v_details := format('Teléfono: 612345678 -> %s', v_result);
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('Teléfono mal enmascarado: %s (esperado *****5678)', v_result);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 23.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 23.4: Enmascaramiento de teléfono con prefijo internacional
    -- ========================================================================
    v_test_num := 4;
    v_result := mask_pii('+34612345678', 'phone');
    IF v_result LIKE '%5678' AND v_result LIKE '%*%' THEN
        v_status := 'PASS';
        v_details := format('Teléfono intl: +34612345678 -> %s', v_result);
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('Teléfono intl mal enmascarado: %s', v_result);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 23.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 23.5: Enmascaramiento de DNI/NIF
    -- ========================================================================
    v_test_num := 5;
    v_result := mask_pii('12345678X', 'dni');
    IF v_result = '12*****8X' THEN
        v_status := 'PASS';
        v_details := format('DNI: 12345678X -> %s', v_result);
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('DNI mal enmascarado: %s (esperado 12*****8X)', v_result);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 23.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 23.6: Enmascaramiento de IP
    -- ========================================================================
    v_test_num := 6;
    v_result := mask_pii('192.168.1.100', 'ip');
    IF v_result = '192.168.***.***' THEN
        v_status := 'PASS';
        v_details := format('IP: 192.168.1.100 -> %s', v_result);
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('IP mal enmascarada: %s (esperado 192.168.***.***)', v_result);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 23.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 23.7: Enmascaramiento de nombre
    -- ========================================================================
    v_test_num := 7;
    v_result := mask_pii('Juan García', 'name');
    IF v_result LIKE 'J%' AND v_result LIKE '%*%' THEN
        v_status := 'PASS';
        v_details := format('Nombre: Juan García -> %s', v_result);
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('Nombre mal enmascarado: %s', v_result);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 23.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 23.8: Enmascaramiento de tarjeta de crédito
    -- ========================================================================
    v_test_num := 8;
    v_result := mask_pii('4111111111111111', 'credit_card');
    IF v_result = '************1111' THEN
        v_status := 'PASS';
        v_details := format('Tarjeta: 4111111111111111 -> %s', v_result);
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('Tarjeta mal enmascarada: %s (esperado ************1111)', v_result);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 23.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 23.9: Enmascaramiento de IBAN
    -- ========================================================================
    v_test_num := 9;
    v_result := mask_pii('ES9121000418450200051332', 'iban');
    IF v_result LIKE 'ES%' AND v_result LIKE '%1332' AND v_result LIKE '%*%' THEN
        v_status := 'PASS';
        v_details := format('IBAN: ES91...1332 -> %s', v_result);
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('IBAN mal enmascarado: %s', v_result);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 23.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 23.10: Enmascaramiento genérico
    -- ========================================================================
    v_test_num := 10;
    v_result := mask_pii('DatoSecreto123', 'generic');
    IF v_result LIKE 'D%' AND v_result LIKE '%3' AND v_result LIKE '%*%' THEN
        v_status := 'PASS';
        v_details := format('Genérico: DatoSecreto123 -> %s', v_result);
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('Genérico mal enmascarado: %s', v_result);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 23.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 23.11: NULL handling
    -- ========================================================================
    v_test_num := 11;
    v_result := mask_pii(NULL, 'email');
    IF v_result IS NULL THEN
        v_status := 'PASS';
        v_details := 'NULL se mantiene como NULL';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('NULL no se maneja correctamente: %s', v_result);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 23.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 23.12: String vacío
    -- ========================================================================
    v_test_num := 12;
    v_result := mask_pii('', 'phone');
    IF v_result = '' OR v_result IS NULL THEN
        v_status := 'PASS';
        v_details := 'String vacío se mantiene vacío';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('String vacío no se maneja correctamente: %s', v_result);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 23.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 23.13: Email corto (2 caracteres local)
    -- ========================================================================
    v_test_num := 13;
    v_result := mask_pii('ab@x.com', 'email');
    IF v_result LIKE '%@x.com' AND v_result LIKE '%*%' THEN
        v_status := 'PASS';
        v_details := format('Email corto: ab@x.com -> %s', v_result);
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('Email corto mal enmascarado: %s', v_result);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 23.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 23.14: Teléfono corto (4 dígitos)
    -- ========================================================================
    v_test_num := 14;
    v_result := mask_pii('1234', 'phone');
    IF v_result = '1234' THEN
        v_status := 'PASS';
        v_details := format('Teléfono corto: 1234 -> %s (sin enmascarar, muy corto)', v_result);
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('Teléfono corto: %s', v_result);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 23.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 23.15: Función decrypt_and_mask_pii existe
    -- ========================================================================
    v_test_num := 15;
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'decrypt_and_mask_pii') THEN
        v_status := 'PASS';
        v_details := 'Función decrypt_and_mask_pii() existe para datos cifrados';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'INFO';
        v_details := 'Función decrypt_and_mask_pii() no existe (opcional)';
        v_passed := v_passed + 1;
    END IF;
    RAISE NOTICE 'Test 23.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- RESUMEN
    -- ========================================================================
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'RESUMEN TEST 23: %/% tests passed', v_passed, v_passed + v_failed;
    RAISE NOTICE '========================================';

    IF v_failed > 0 THEN
        RAISE NOTICE 'RESULTADO: FAILED (% errores)', v_failed;
    ELSE
        RAISE NOTICE 'RESULTADO: ALL TESTS PASSED';
        RAISE NOTICE '';
        RAISE NOTICE 'Tipos de enmascaramiento disponibles:';
        RAISE NOTICE '  - email: us*****@domain.com';
        RAISE NOTICE '  - phone: *****5678';
        RAISE NOTICE '  - dni/nif: 12*****8X';
        RAISE NOTICE '  - ip: 192.168.***.***';
        RAISE NOTICE '  - name: J**********';
        RAISE NOTICE '  - credit_card: ************1234';
        RAISE NOTICE '  - iban: ES**************1234';
        RAISE NOTICE '  - address: C/ **********5';
        RAISE NOTICE '  - generic: D*********3 (25%% visible)';
    END IF;

END $$;

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
