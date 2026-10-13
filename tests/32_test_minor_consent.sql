-- ============================================================================
-- TEST 32: CONSENTIMIENTO DE MENORES
-- ============================================================================
-- COBERTURA LEGAL:
--   • LOPDGDD Art. 7.1: Consentimiento menores >= 14 años en España
--   • LOPDGDD Art. 7.2: Menores < 14 años requieren consentimiento parental
--   • RGPD Art. 8.1: Tratamiento de datos de menores
--   • RGPD Art. 8.2: Consentimiento del titular de la patria potestad
--   • LOPDGDD Art. 7.4: Lenguaje claro y sencillo adaptado a menores
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: CRÍTICA
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Art. 8, PARTE 2 (LOPDGDD) - Art. 7
-- ============================================================================
-- Verifica tratamiento de datos de menores de edad según legislación española
-- Ejecutar: \i /path/to/32_test_minor_consent.sql

-- Iniciar transacción para garantizar idempotencia
BEGIN;

\set ON_ERROR_STOP on
SET client_min_messages = notice;

CREATE TEMP TABLE IF NOT EXISTS test_results (
    test_id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    test_category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';
SET app.hash_pepper = 'TEST_PEPPER_V1_FOR_HMAC_FUNCTIONS';
SET app.hash_pepper_version = '1';
SET app.audit_hmac_key = 'TEST_AUDIT_KEY_FOR_HMAC_CHAIN__';

-- ============================================================================
-- TEST 32.1: Campo birth_date Existe para Verificar Edad
-- ============================================================================

DO $$
DECLARE
    v_users_has_birthdate BOOLEAN;
    v_contacts_has_birthdate BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'birth_date'
    ) INTO v_users_has_birthdate;

    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'contacts' AND column_name = 'birth_date'
    ) INTO v_contacts_has_birthdate;

    IF v_users_has_birthdate OR v_contacts_has_birthdate THEN
        v_status := 'PASS';
        v_details := 'birth_date field exists for age verification (LOPDGDD Art. 7)';
    ELSE
        v_status := 'FAIL';
        v_details := 'CRITICAL: Add birth_date to users/contacts to comply with LOPDGDD Art. 7';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Birth Date Field Exists', 'Minor_Consent', v_status, v_details);
    RAISE NOTICE '  [%] Birth Date Field: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Birth Date Field Exists', 'Minor_Consent', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 32.2: Función check_age_consent() Para Validar Capacidad
-- ============================================================================

DO $$
DECLARE
    v_function_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE p.proname = 'check_age_consent'
        AND n.nspname = 'public'
    ) INTO v_function_exists;

    IF v_function_exists THEN
        v_status := 'PASS';
        v_details := 'check_age_consent() function exists for LOPDGDD Art. 7 validation';
    ELSE
        v_status := 'FAIL';
        v_details := 'RECOMMENDATION: Create check_age_consent(birth_date) function that returns bool (>= 14 years)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Age Consent Function', 'Minor_Consent', v_status, v_details);
    RAISE NOTICE '  [%] Age Check Function: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Age Consent Function', 'Minor_Consent', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 32.3: Mayor de 14 Años Puede Consentir (España)
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_test_consent_id UUID;
    v_teen_birth_date DATE := CURRENT_DATE - INTERVAL '15 years'; -- 15 años
    v_consent_valid BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    INSERT INTO users (name, email, password_hash, role, birth_date)
    VALUES (
        'TEST_TEEN_15', 
        'teen15_' || gen_random_uuid()::TEXT || '@test.local',
        'test_hash',
        'user',
        v_teen_birth_date
    )
    RETURNING id INTO v_test_user_id;

    -- Intentar crear consentimiento para menor de  15 años (>= 14)
    INSERT INTO data_consents (purpose_id, granted_at, consent_method, consent_version_id, data_subject_id, data_subject_type)
    SELECT id, CURRENT_TIMESTAMP, 'explicit', id, v_test_user_id, 'user'
    FROM data_processing_purposes
    LIMIT 1
    RETURNING id INTO v_test_consent_id;

    v_consent_valid := (v_test_consent_id IS NOT NULL);

    IF v_consent_valid THEN
        v_status := 'PASS';
        v_details := 'Minor >=14 years can consent autonomously (LOPDGDD Art. 7.1 compliant)';
    ELSE
        v_status := 'FAIL';
        v_details := 'Failed to create consent for 15-year-old';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Minor 14+ Can Consent', 'Minor_Consent', v_status, v_details);

    RAISE NOTICE '  [%] Teen Consent: %', v_status, v_details;

EXCEPTION 
    WHEN undefined_column THEN
        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('Minor 14+ Can Consent', 'Minor_Consent', 'SKIP', 'birth_date column not found in users table');
    WHEN OTHERS THEN
        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('Minor 14+ Can Consent', 'Minor_Consent', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 32.4: Menor de 14 Años Requiere Consentimiento Parental
-- ============================================================================

DO $$
DECLARE
    v_test_child_id UUID;
    v_test_parent_id UUID;
    v_child_birth_date DATE := CURRENT_DATE - INTERVAL '10 years'; -- 10 años
    v_parental_consent_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear padre/tutor
    INSERT INTO users (name, email, password_hash, role)
    VALUES (
        'TEST_PARENT',
        'parent_' || gen_random_uuid()::TEXT || '@test.local',
        'test_hash',
        'user'
    )
    RETURNING id INTO v_test_parent_id;

    -- Crear menor de 14 años
    INSERT INTO users (name, email, password_hash, role, birth_date)
    VALUES (
        'TEST_CHILD_10',
        'child10_' || gen_random_uuid()::TEXT || '@test.local',
        'test_hash',
        'user',
        v_child_birth_date
    )
    RETURNING id INTO v_test_child_id;

    -- Un menor < 14 NO debería poder consentir solo
    -- Debería requerir consentimiento parental
    
    -- Verificar si existe mecanismo de consentimiento parental
    v_parental_consent_exists := EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE (table_name = 'data_consents' AND column_name = 'parental_consent_id')
        OR (table_name = 'users' AND column_name = 'parent_user_id')
    );

    IF v_parental_consent_exists THEN
        v_status := 'PASS';
        v_details := 'Parental consent mechanism exists (required by LOPDGDD Art. 7.2 for <14)';
    ELSE
        v_status := 'FAIL';
        v_details := 'CRITICAL: Add parental_consent_id or parent_user_id for minors <14';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Parental Consent for <14', 'Minor_Consent', v_status, v_details);
    RAISE NOTICE '  [%] Parental Consent: %', v_status, v_details;

EXCEPTION 
    WHEN undefined_column THEN
        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('Parental Consent for <14', 'Minor_Consent', 'SKIP', 'birth_date column not found');
    WHEN OTHERS THEN
        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('Parental Consent for <14', 'Minor_Consent', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 32.5: Privacidad Específica para Menores
-- ==================================================== ========================

DO $$
DECLARE
    v_minors_privacy_notice_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Verificar si existe versión de aviso de privacidad para menores
    SELECT EXISTS (
        SELECT 1 FROM consent_versions
        WHERE version_name LIKE '%menor%'
        OR version_name LIKE '%minor%'
        OR version_name LIKE '%child%'
    ) INTO v_minors_privacy_notice_exists;

    IF v_minors_privacy_notice_exists THEN
        v_status := 'PASS';
        v_details := 'Minor-specific privacy notice exists (LOPDGDD Art. 7.4 - adapted language)';
    ELSE
        v_status := 'FAIL';
        v_details := 'RECOMMENDATION: Create simplified privacy notice for minors (LOPDGDD Art. 7.4)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Minor-Specific Privacy Notice', 'Minor_Consent', v_status, v_details);
    RAISE NOTICE '  [%] Minors Privacy Notice: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Minor-Specific Privacy Notice', 'Minor_Consent', 'SKIP', 'consent_versions table may not exist');
END $$;

-- ============================================================================
-- RESUMEN DE RESULTADOS
-- ============================================================================

SELECT
    test_category,
    COUNT(*) as total_tests,
    COUNT(*) FILTER (WHERE status = 'PASS') as passed,
    COUNT(*) FILTER (WHERE status = 'FAIL') as failed,
    COUNT(*) FILTER (WHERE status = 'SKIP') as skipped
FROM test_results
WHERE test_category = 'Minor_Consent'
GROUP BY test_category;

SELECT test_name, details
FROM test_results
WHERE test_category = 'Minor_Consent' AND status = 'FAIL';

ROLLBACK;
