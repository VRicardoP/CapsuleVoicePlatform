-- ============================================================================
-- TEST 18: CAMPAIGNS - Gestión de Campañas
-- ============================================================================
-- COBERTURA LEGAL:
--   • LSSI Art. 21.2: Consentimiento previo para comunicaciones comerciales
--   • LSSI Art. 22: Derecho a oposición (opt-out)
--   • Parcial: verifica estructura pero no validación completa
-- 
-- NIVEL DE COMPLIANCE: BAJO
-- CRITICIDAD: MEDIA
-- REQUISITOS NORMATIVA.MD: PARTE 6 (LSSI-CE) - Arts. 21-22
-- ============================================================================
-- Verifica las tablas campaigns y campaign_calls
-- Alimenta el módulo de campañas del dashboard
-- Ejecutar: psql -U postgres -d sfera -f 18_test_campaigns.sql
-- ============================================================================

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '=============================================='
\echo 'TEST 18: CAMPAIGNS'
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
        'test_key_camp_' || substring(gen_random_uuid()::TEXT, 1, 8),
        pgp_sym_encrypt(encode(gen_random_bytes(32), 'hex'), current_setting('app.kms_master_key'), 'cipher-algo=aes256'),
        true,
        'hashicorp-vault',
        CURRENT_TIMESTAMP
    );
EXCEPTION WHEN OTHERS THEN
    NULL;
END $$;

-- ============================================================================
-- TEST 18.1: Tabla campaigns existe con estructura correcta
-- ============================================================================

\echo ''
\echo '--- Test 18.1: Estructura campaigns ---'

DO $$
DECLARE
    v_table_exists BOOLEAN;
    v_has_name BOOLEAN;
    v_has_status BOOLEAN;
    v_has_budget BOOLEAN;
    v_has_minutes BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Verificar tabla
    SELECT EXISTS(
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'campaigns'
    ) INTO v_table_exists;

    -- Verificar columnas clave
    SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name = 'campaigns' AND column_name = 'name') INTO v_has_name;
    SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name = 'campaigns' AND column_name = 'status') INTO v_has_status;
    SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name = 'campaigns' AND column_name = 'budget') INTO v_has_budget;
    SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name = 'campaigns' AND column_name = 'total_minutes') INTO v_has_minutes;

    IF v_table_exists AND v_has_name AND v_has_status AND v_has_budget AND v_has_minutes THEN
        v_status := 'PASS';
        v_details := 'campaigns table has required structure';
    ELSE
        v_status := 'FAIL';
        v_details := format('Missing - table:%s name:%s status:%s budget:%s minutes:%s',
            v_table_exists, v_has_name, v_has_status, v_has_budget, v_has_minutes);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Campaigns Structure', 'Campaigns', v_status, v_details);

    RAISE NOTICE '  [%] Structure: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Campaigns Structure', 'Campaigns', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 18.2: Crear campaña
-- ============================================================================

\echo ''
\echo '--- Test 18.2: Crear campana ---'

DO $$
DECLARE
    v_user_id UUID;
    v_campaign_id UUID;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('CAMP_USER', 'camp_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Crear campaña
    INSERT INTO campaigns (
        user_id, name, description,
        start_date, end_date,
        budget, status, tags
    )
    VALUES (
        v_user_id,
        'Test Campaign ' || substring(gen_random_uuid()::TEXT, 1, 8),
        'Campaign for testing purposes',
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP + INTERVAL '30 days',
        5000.00,
        'active',
        ARRAY['test', 'marketing', 'q4']
    )
    RETURNING id INTO v_campaign_id;

    IF v_campaign_id IS NOT NULL THEN
        v_status := 'PASS';
        v_details := format('Campaign created: %s', v_campaign_id);
    ELSE
        v_status := 'FAIL';
        v_details := 'Failed to create campaign';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Create Campaign', 'Campaigns', v_status, v_details);

    RAISE NOTICE '  [%] Create: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Create Campaign', 'Campaigns', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Create: Exception - %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 18.3: Estados de campaña válidos
-- ============================================================================

\echo ''
\echo '--- Test 18.3: Estados de campana validos ---'

DO $$
DECLARE
    v_user_id UUID;
    v_error_raised BOOLEAN := false;
    v_valid_states TEXT[] := ARRAY['active', 'paused', 'completed', 'cancelled'];
    v_state TEXT;
    v_all_valid BOOLEAN := true;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('STATE_USER', 'state_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Probar cada estado válido
    FOREACH v_state IN ARRAY v_valid_states LOOP
        BEGIN
            INSERT INTO campaigns (user_id, name, start_date, status)
            VALUES (v_user_id, 'State Test ' || v_state, CURRENT_TIMESTAMP, v_state);
        EXCEPTION WHEN OTHERS THEN
            v_all_valid := false;
        END;
    END LOOP;

    -- Probar estado inválido
    BEGIN
        INSERT INTO campaigns (user_id, name, start_date, status)
        VALUES (v_user_id, 'Invalid State', CURRENT_TIMESTAMP, 'invalid_status');
    EXCEPTION WHEN OTHERS THEN
        v_error_raised := true;
    END;

    IF v_all_valid AND v_error_raised THEN
        v_status := 'PASS';
        v_details := 'All valid states accepted, invalid state rejected';
    ELSE
        v_status := 'FAIL';
        v_details := format('Valid states ok:%s, invalid rejected:%s', v_all_valid, v_error_raised);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Campaign Status Validation', 'Campaigns', v_status, v_details);

    RAISE NOTICE '  [%] Status: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Campaign Status Validation', 'Campaigns', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 18.4: Vincular llamada a campaña
-- ============================================================================

\echo ''
\echo '--- Test 18.4: Vincular llamada a campana ---'

DO $$
DECLARE
    v_user_id UUID;
    v_contact_id UUID;
    v_campaign_id UUID;
    v_call_id UUID;
    v_link_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('LINK_USER', 'link_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Crear contacto
    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_user_id,
        encrypt_pii_with_metadata('Link Test'),
        encrypt_pii_with_metadata('+34600111222'),
        (secure_hash_with_pepper('+34600111222')).hash
    )
    RETURNING id INTO v_contact_id;

    -- Crear campaña
    INSERT INTO campaigns (user_id, name, start_date, status)
    VALUES (v_user_id, 'Link Test Campaign', CURRENT_TIMESTAMP, 'active')
    RETURNING id INTO v_campaign_id;

    -- Crear llamada
    INSERT INTO calls (
        user_id, contact_id, call_date, call_time, caller_name_encrypted, caller_phone_encrypted,
        caller_phone_hash, call_timestamp, duration_seconds, status, recording_encrypted
    )
    VALUES (
        v_user_id, v_contact_id, CURRENT_DATE, CURRENT_TIME,
        encrypt_pii_with_metadata('Link Test'),
        encrypt_pii_with_metadata('+34600111222'),
        (secure_hash_with_pepper('+34600111222')).hash,
        CURRENT_TIMESTAMP, 180, 'completed', false
    )
    RETURNING id INTO v_call_id;

    -- Vincular llamada a campaña
    INSERT INTO campaign_calls (campaign_id, call_id)
    VALUES (v_campaign_id, v_call_id);

    -- Verificar vínculo
    SELECT EXISTS(
        SELECT 1 FROM campaign_calls
        WHERE campaign_id = v_campaign_id AND call_id = v_call_id
    ) INTO v_link_exists;

    IF v_link_exists THEN
        v_status := 'PASS';
        v_details := 'Call successfully linked to campaign';
    ELSE
        v_status := 'FAIL';
        v_details := 'Failed to link call to campaign';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Link Call to Campaign', 'Campaigns', v_status, v_details);

    RAISE NOTICE '  [%] Link: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Link Call to Campaign', 'Campaigns', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Link: Exception - %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 18.5: Cascade delete campaña elimina vínculos
-- ============================================================================

\echo ''
\echo '--- Test 18.5: Cascade delete campana ---'

DO $$
DECLARE
    v_user_id UUID;
    v_contact_id UUID;
    v_campaign_id UUID;
    v_call_id UUID;
    v_links_exist BOOLEAN;
    v_call_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear datos
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('CASCADE_CAMP', 'casc_camp_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_user_id,
        encrypt_pii_with_metadata('Cascade Camp'),
        encrypt_pii_with_metadata('+34600333444'),
        (secure_hash_with_pepper('+34600333444')).hash
    )
    RETURNING id INTO v_contact_id;

    INSERT INTO campaigns (user_id, name, start_date, status)
    VALUES (v_user_id, 'Cascade Test Campaign', CURRENT_TIMESTAMP, 'active')
    RETURNING id INTO v_campaign_id;

    INSERT INTO calls (
        user_id, contact_id, call_date, call_time, caller_name_encrypted, caller_phone_encrypted,
        caller_phone_hash, call_timestamp, duration_seconds, status, recording_encrypted
    )
    VALUES (
        v_user_id, v_contact_id, CURRENT_DATE, CURRENT_TIME,
        encrypt_pii_with_metadata('Cascade'),
        encrypt_pii_with_metadata('+34600333444'),
        (secure_hash_with_pepper('+34600333444')).hash,
        CURRENT_TIMESTAMP, 60, 'completed', false
    )
    RETURNING id INTO v_call_id;

    INSERT INTO campaign_calls (campaign_id, call_id)
    VALUES (v_campaign_id, v_call_id);

    -- Eliminar campaña
    DELETE FROM campaigns WHERE id = v_campaign_id;

    -- Verificar que vínculos se eliminaron pero llamada persiste
    SELECT EXISTS(SELECT 1 FROM campaign_calls WHERE campaign_id = v_campaign_id) INTO v_links_exist;
    SELECT EXISTS(SELECT 1 FROM calls WHERE id = v_call_id) INTO v_call_exists;

    IF NOT v_links_exist AND v_call_exists THEN
        v_status := 'PASS';
        v_details := 'Campaign deleted, links removed, call preserved';
    ELSE
        v_status := 'FAIL';
        v_details := format('links_exist:%s call_exists:%s', v_links_exist, v_call_exists);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Cascade Delete Campaign', 'Campaigns', v_status, v_details);

    RAISE NOTICE '  [%] Cascade: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Cascade Delete Campaign', 'Campaigns', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 18.6: Soft delete con deleted_at
-- ============================================================================

\echo ''
\echo '--- Test 18.6: Soft delete con deleted_at ---'

DO $$
DECLARE
    v_user_id UUID;
    v_campaign_id UUID;
    v_deleted_at TIMESTAMP WITH TIME ZONE;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('SOFT_DEL_USER', 'soft_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Crear campaña
    INSERT INTO campaigns (user_id, name, start_date, status)
    VALUES (v_user_id, 'Soft Delete Test', CURRENT_TIMESTAMP, 'active')
    RETURNING id INTO v_campaign_id;

    -- Soft delete
    UPDATE campaigns SET deleted_at = CURRENT_TIMESTAMP WHERE id = v_campaign_id;

    -- Verificar
    SELECT deleted_at INTO v_deleted_at FROM campaigns WHERE id = v_campaign_id;

    IF v_deleted_at IS NOT NULL THEN
        v_status := 'PASS';
        v_details := format('Soft delete successful: deleted_at = %s', v_deleted_at);
    ELSE
        v_status := 'FAIL';
        v_details := 'deleted_at not set';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Soft Delete', 'Campaigns', v_status, v_details);

    RAISE NOTICE '  [%] Soft Delete: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Soft Delete', 'Campaigns', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 18.7: Índice parcial para campañas activas
-- ============================================================================

\echo ''
\echo '--- Test 18.7: Indice parcial campanas activas ---'

DO $$
DECLARE
    v_idx_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'idx_campaigns_user'
        AND indexdef LIKE '%deleted_at IS NULL%'
    ) INTO v_idx_exists;

    IF v_idx_exists THEN
        v_status := 'PASS';
        v_details := 'Partial index for active campaigns exists';
    ELSE
        v_status := 'FAIL';
        v_details := 'Missing partial index for active campaigns';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Partial Index Active Campaigns', 'Campaigns', v_status, v_details);

    RAISE NOTICE '  [%] Index: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Partial Index Active Campaigns', 'Campaigns', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 18.8: Tags como array
-- ============================================================================

\echo ''
\echo '--- Test 18.8: Tags como array ---'

DO $$
DECLARE
    v_user_id UUID;
    v_campaign_id UUID;
    v_tags TEXT[];
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TAGS_USER', 'tags_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Crear campaña con tags
    INSERT INTO campaigns (user_id, name, start_date, status, tags)
    VALUES (v_user_id, 'Tags Test', CURRENT_TIMESTAMP, 'active', ARRAY['promo', 'verano', '2024'])
    RETURNING id INTO v_campaign_id;

    -- Verificar tags
    SELECT tags INTO v_tags FROM campaigns WHERE id = v_campaign_id;

    IF array_length(v_tags, 1) = 3 AND 'promo' = ANY(v_tags) THEN
        v_status := 'PASS';
        v_details := format('Tags array works: %s', v_tags);
    ELSE
        v_status := 'FAIL';
        v_details := 'Tags array not working correctly';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Tags Array', 'Campaigns', v_status, v_details);

    RAISE NOTICE '  [%] Tags: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Tags Array', 'Campaigns', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- RESUMEN DE RESULTADOS
-- ============================================================================

\echo ''
\echo '=============================================='
\echo 'RESUMEN TEST 18: CAMPAIGNS'
\echo '=============================================='

SELECT
    test_category,
    COUNT(*) as total_tests,
    COUNT(*) FILTER (WHERE status = 'PASS') as passed,
    COUNT(*) FILTER (WHERE status = 'FAIL') as failed,
    COUNT(*) FILTER (WHERE status = 'SKIP') as skipped
FROM test_results
WHERE test_category = 'Campaigns'
GROUP BY test_category;

SELECT test_name, status, details
FROM test_results
WHERE test_category = 'Campaigns'
ORDER BY test_id;

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
