-- ============================================================================
-- TEST 21: RGPD/LOPDGDD COMPLIANCE (Punto 3 Auditoría)
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD (verificación general superficial)
--   • Verifica existencia de estructuras, no funcionalidad profunda
-- 
-- NIVEL DE COMPLIANCE: BAJO (superficial)
-- CRITICIDAD: MEDIA
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Vista general
-- ============================================================================
-- Verifica implementación de Art. 12/13/14, 5.1.d, 44-49 y enmascaramiento PII
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
    v_user_id UUID;
    v_contact_id UUID;
    v_delivery_id UUID;
    v_transfer_id UUID;
    v_masked_value TEXT;
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'TEST 21: RGPD/LOPDGDD COMPLIANCE';
    RAISE NOTICE '========================================';

    -- ========================================================================
    -- TEST 21.1: Tabla information_delivery existe (Art. 12/13/14)
    -- ========================================================================
    v_test_num := 1;
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'information_delivery'
    ) THEN
        v_status := 'PASS';
        v_details := 'Tabla information_delivery creada correctamente';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Tabla information_delivery NO existe';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 21.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 21.2: Campos obligatorios en information_delivery
    -- ========================================================================
    v_test_num := 2;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'information_delivery'
        AND column_name IN ('information_type', 'delivery_channel', 'content_delivered')
        GROUP BY table_name
        HAVING COUNT(*) = 3
    ) THEN
        v_status := 'PASS';
        v_details := 'Campos information_type, delivery_channel, content_delivered presentes';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Faltan campos obligatorios en information_delivery';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 21.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 21.3: Campos de exactitud en contacts (Art. 5.1.d)
    -- ========================================================================
    v_test_num := 3;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'contacts'
        AND column_name IN ('accuracy_flag', 'data_verified_at', 'verification_method')
        GROUP BY table_name
        HAVING COUNT(*) = 3
    ) THEN
        v_status := 'PASS';
        v_details := 'Campos de exactitud (accuracy_flag, data_verified_at, verification_method) presentes';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Faltan campos de exactitud en contacts';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 21.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 21.4: Tabla international_transfers existe (Art. 44-49)
    -- ========================================================================
    v_test_num := 4;
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'international_transfers'
    ) THEN
        v_status := 'PASS';
        v_details := 'Tabla international_transfers creada correctamente';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Tabla international_transfers NO existe';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 21.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 21.5: Bases legales de transferencia correctas
    -- ========================================================================
    v_test_num := 5;
    BEGIN
        -- Verificar que el CHECK constraint incluye las bases legales del RGPD
        IF EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conrelid = 'international_transfers'::regclass
            AND pg_get_constraintdef(oid) LIKE '%adequacy_decision%'
            AND pg_get_constraintdef(oid) LIKE '%standard_clauses%'
            AND pg_get_constraintdef(oid) LIKE '%binding_corporate_rules%'
        ) THEN
            v_status := 'PASS';
            v_details := 'Bases legales Art. 44-49 configuradas correctamente';
            v_passed := v_passed + 1;
        ELSE
            v_status := 'FAIL';
            v_details := 'Faltan bases legales de transferencia';
            v_failed := v_failed + 1;
        END IF;
    EXCEPTION WHEN OTHERS THEN
        v_status := 'FAIL';
        v_details := 'Error verificando bases legales: ' || SQLERRM;
        v_failed := v_failed + 1;
    END;
    RAISE NOTICE 'Test 21.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 21.6: Función mask_pii existe
    -- ========================================================================
    v_test_num := 6;
    IF EXISTS (
        SELECT 1 FROM pg_proc WHERE proname = 'mask_pii'
    ) THEN
        v_status := 'PASS';
        v_details := 'Función mask_pii creada correctamente';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Función mask_pii NO existe';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 21.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 21.7: mask_pii enmascara email correctamente
    -- ========================================================================
    v_test_num := 7;
    v_masked_value := mask_pii('usuario@dominio.com', 'email');
    IF v_masked_value LIKE 'us%@dominio.com' AND v_masked_value LIKE '%*%' THEN
        v_status := 'PASS';
        v_details := format('Email enmascarado: %s', v_masked_value);
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('Email mal enmascarado: %s', v_masked_value);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 21.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 21.8: mask_pii enmascara teléfono correctamente
    -- ========================================================================
    v_test_num := 8;
    v_masked_value := mask_pii('612345678', 'phone');
    IF v_masked_value = '*****5678' THEN
        v_status := 'PASS';
        v_details := format('Teléfono enmascarado: %s', v_masked_value);
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('Teléfono mal enmascarado: %s (esperado *****5678)', v_masked_value);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 21.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 21.9: mask_pii enmascara IP correctamente
    -- ========================================================================
    v_test_num := 9;
    v_masked_value := mask_pii('192.168.1.100', 'ip');
    IF v_masked_value = '192.168.***.***' THEN
        v_status := 'PASS';
        v_details := format('IP enmascarada: %s', v_masked_value);
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := format('IP mal enmascarada: %s (esperado 192.168.***.***)', v_masked_value);
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 21.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 21.10: Política de retención de IP documentada
    -- ========================================================================
    v_test_num := 10;
    IF EXISTS (
        SELECT 1 FROM retention_policies
        WHERE entity_table = 'audit_log'
        AND retention_days = 90
        AND action_on_expiry = 'anonymize'
    ) THEN
        v_status := 'PASS';
        v_details := 'Política de retención IP (90 días, anonimización) documentada';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Política de retención IP no configurada correctamente';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 21.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 21.11: Columnas de retención IP en audit_log
    -- ========================================================================
    v_test_num := 11;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'audit_log'
        AND column_name IN ('ip_retention_justification', 'ip_anonymization_date')
        GROUP BY table_name
        HAVING COUNT(*) = 2
    ) THEN
        v_status := 'PASS';
        v_details := 'Campos ip_retention_justification e ip_anonymization_date en audit_log';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Faltan campos de retención IP en audit_log';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 21.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 21.12: Tabla transfer_log existe
    -- ========================================================================
    v_test_num := 12;
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'transfer_log'
    ) THEN
        v_status := 'PASS';
        v_details := 'Tabla transfer_log para registro de transferencias';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Tabla transfer_log NO existe';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 21.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 21.13: Función anonymize_old_audit_ips existe
    -- ========================================================================
    v_test_num := 13;
    IF EXISTS (
        SELECT 1 FROM pg_proc WHERE proname = 'anonymize_old_audit_ips'
    ) THEN
        v_status := 'PASS';
        v_details := 'Función de anonimización automática de IPs existe';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Función anonymize_old_audit_ips NO existe';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 21.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 21.14: Vista v_rgpd_compliance_check existe
    -- ========================================================================
    v_test_num := 14;
    IF EXISTS (
        SELECT 1 FROM information_schema.views
        WHERE table_name = 'v_rgpd_compliance_check'
    ) THEN
        v_status := 'PASS';
        v_details := 'Vista de verificación RGPD disponible';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Vista v_rgpd_compliance_check NO existe';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 21.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- TEST 21.15: Campo data_source en contacts (Art. 14)
    -- ========================================================================
    v_test_num := 15;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'contacts' AND column_name = 'data_source'
    ) THEN
        v_status := 'PASS';
        v_details := 'Campo data_source para origen de datos (Art. 14)';
        v_passed := v_passed + 1;
    ELSE
        v_status := 'FAIL';
        v_details := 'Campo data_source NO existe en contacts';
        v_failed := v_failed + 1;
    END IF;
    RAISE NOTICE 'Test 21.%: % - %', v_test_num, v_status, v_details;

    -- ========================================================================
    -- RESUMEN
    -- ========================================================================
    RAISE NOTICE '========================================';
    RAISE NOTICE 'RESUMEN TEST 21: %/% tests passed', v_passed, v_passed + v_failed;
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
