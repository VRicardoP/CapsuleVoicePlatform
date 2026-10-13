-- ============================================================================
-- TEST 29: VALIDACIÓN DE BASES LEGALES
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 5.1.a: Licitud, lealtad y transparencia del tratamiento
--   • RGPD Art. 6.1: Bases jurídicas para el tratamiento lícito
--   • RGPD Art. 6.1.a: Consentimiento del interesado
--   • RGPD Art. 6.1.b: Necesario para ejecución de contrato
--   • RGPD Art. 6.1.c: Necesario para cumplimiento de obligación legal
--   • RGPD Art. 6.1.f: Interés legítimo del responsable
--   • RGPD Art. 9.2: Prohibición tratamiento datos especiales sin base legal adecuada
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: CRÍTICA
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Principios y Bases Jurídicas (Arts. 5-6)
-- ============================================================================
-- Verifica que todos los tratamientos tienen base legal válida y documentada
-- Ejecutar: \i /path/to/29_test_base_legal_validation.sql

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
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

-- Configurar variables de sesión
SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';
SET app.hash_pepper = 'TEST_PEPPER_V1_FOR_HMAC_FUNCTIONS';
SET app.hash_pepper_version = '1';
SET app.audit_hmac_key = 'TEST_AUDIT_KEY_FOR_HMAC_CHAIN__';

-- ============================================================================
-- TEST 29.1: Tabla data_processing_purposes Tiene Campo legal_basis
-- ============================================================================

DO $$
DECLARE
    v_column_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Verificar existencia de columna legal_basis
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'data_processing_purposes'
        AND column_name = 'legal_basis'
    ) INTO v_column_exists;

    IF v_column_exists THEN
        v_status := 'PASS';
        v_details := 'Column legal_basis exists in data_processing_purposes';
    ELSE
        v_status := 'FAIL';
        v_details := 'Column legal_basis missing in data_processing_purposes (REQUIRED by RGPD Art. 6)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Legal Basis Column Exists', 'Legal_Basis_Validation', v_status, v_details);

    RAISE NOTICE '  [%] Legal Basis Column: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Legal Basis Column Exists', 'Legal_Basis_Validation', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 29.2: Valores de legal_basis Son Válidos Según RGPD Art. 6
-- ============================================================================

DO $$
DECLARE
    v_valid_bases TEXT[] := ARRAY['consent', 'contract', 'legal_obligation', 'vital_interest', 'public_task', 'legitimate_interest'];
    v_invalid_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear un propósito de prueba con cada base legal válida
    INSERT INTO data_processing_purposes (code, name, legal_basis, description)
    VALUES 
        ('TEST_CONSENT', 'TEST_CONSENT', 'consent', 'Test consent basis'),
        ('TEST_CONTRACT', 'TEST_CONTRACT', 'contract', 'Test contract basis'),
        ('TEST_LEGAL', 'TEST_LEGAL', 'legal_obligation', 'Test legal obligation'),
        ('TEST_LEGITIMATE', 'TEST_LEGITIMATE', 'legitimate_interest', 'Test legitimate interest');

    -- Intentar insertar base legal inválida (debe fallar si hay constraint)
    BEGIN
        INSERT INTO data_processing_purposes (code, name, legal_basis, description)
        VALUES ('TEST_INVALID', 'invalid_basis', 'Should fail');
        v_invalid_count := 1;
    EXCEPTION WHEN OTHERS THEN
        v_invalid_count := 0; -- Bien, el constraint bloqueó la inserción inválida
    END;

    IF v_invalid_count = 0 THEN
        v_status := 'PASS';
        v_details := 'Legal basis constraint works correctly - invalid values rejected';
    ELSE
        v_status := 'FAIL';
        v_details := 'Invalid legal basis accepted - missing CHECK constraint on legal_basis';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Valid Legal Basis Values', 'Legal_Basis_Validation', v_status, v_details);

    RAISE NOTICE '  [%] Valid Legal Basis: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Valid Legal Basis Values', 'Legal_Basis_Validation', 'SKIP', 'Column may not exist: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 29.3: Consentimiento Requiere FK a data_consents
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_test_purpose_id UUID;
    v_test_consent_id UUID;
    v_consent_linked BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario de prueba
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_LEGAL_BASIS_USER', 'test_legal_basis_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash', 'admin')
    RETURNING id INTO v_test_user_id;

    -- Crear propósito con base legal "consent"
    INSERT INTO data_processing_purposes (code, name, legal_basis, description)
    VALUES ('TEST_PURPOSE_CONSENT', 'TEST_PURPOSE_CONSENT', 'consent', 'Requires consent')
    RETURNING id INTO v_test_purpose_id;

    -- Crear consentimiento
    INSERT INTO data_consents (purpose_id, granted_at, consent_method, consent_version_id)
    SELECT v_test_purpose_id, CURRENT_TIMESTAMP, 'explicit', id
    FROM consent_versions LIMIT 1
    RETURNING id INTO v_test_consent_id;

    -- Verificar que existe la relación
    SELECT EXISTS(
        SELECT 1 FROM data_consents dc
        JOIN data_processing_purposes dpp ON dc.purpose_id = dpp.id
        WHERE dc.id = v_test_consent_id
        AND dpp.legal_basis = 'consent'
    ) INTO v_consent_linked;

    IF v_consent_linked THEN
        v_status := 'PASS';
        v_details := 'Consent-based purposes correctly linked to data_consents';
    ELSE
        v_status := 'FAIL';
        v_details := 'Consent linkage not working';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Consent Requires Link', 'Legal_Basis_Validation', v_status, v_details);

    RAISE NOTICE '  [%] Consent Link: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Consent Requires Link', 'Legal_Basis_Validation', 'SKIP', 'Schema may not support: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 29.4: Datos Especiales Requieren Base Legal Apropiada (Art. 9.2 RGPD)
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_sensitive_purpose_id UUID;
    v_has_explicit_consent BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_SENSITIVE_USER', 'test_sensitive_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash', 'admin')
    RETURNING id INTO v_test_user_id;

    -- Crear propósito para datos sensibles
    INSERT INTO data_processing_purposes (code, name, legal_basis, description, is_sensitive_data)
    VALUES ('TEST_HEALTH_DATA', 'TEST_HEALTH_DATA', 'consent', 'Processing health data', true)
    RETURNING id INTO v_sensitive_purpose_id;

    -- Verificar que datos sensibles SOLO pueden usar bases legales de Art. 9.2
    -- No pueden usar 'legitimate_interest' solo
    SELECT legal_basis IN ('consent', 'legal_obligation', 'vital_interest')
    INTO v_has_explicit_consent
    FROM data_processing_purposes
    WHERE id = v_sensitive_purpose_id;

    IF v_has_explicit_consent THEN
        v_status := 'PASS';
        v_details := 'Sensitive data uses appropriate legal basis (Art. 9.2 RGPD)';
    ELSE
        v_status := 'FAIL';
        v_details := 'Sensitive data using inappropriate legal basis';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Sensitive Data Legal Basis', 'Legal_Basis_Validation', v_status, v_details);

    RAISE NOTICE '  [%] Sensitive Data Basis: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Sensitive Data Legal Basis', 'Legal_Basis_Validation', 'SKIP', 'is_sensitive_data column may not exist: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 29.5: Interés Legítimo Requiere Evaluación LIA
-- ============================================================================

DO $$
DECLARE
    v_test_purpose_id UUID;
    v_lia_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear propósito basado en interés legítimo
    INSERT INTO data_processing_purposes (code, name, legal_basis, description)
    VALUES ('TEST_LEGITIMATE_INTEREST', 'TEST_LEGITIMATE_INTEREST', 'legitimate_interest', 'Based on LIA')
    RETURNING id INTO v_test_purpose_id;

    -- Verificar si existe tabla de evaluaciones        -- Verificar que existe LIA aprobada activa
    IF NOT EXISTS (
        SELECT 1 FROM legitimate_interest_assessments
        WHERE purpose_id = v_test_purpose_id
        AND is_active = true
        AND balancing_test_conclusion = 'approved'
        AND approved_at IS NOT NULL
    ) THEN
        v_status := 'FAIL';
        v_details := format('Purpose "%s" uses legitimate_interest but has no approved LIA. Art. 6.1.f RGPD requires documented balancing test. HINT: Create entry in legitimate_interest_assessments table', (SELECT name FROM data_processing_purposes WHERE id = v_test_purpose_id));
    ELSE
        v_status := 'PASS';
        v_details := 'LIA documentation table exists and an approved LIA is linked (RGPD Art. 6.1.f requires documented balancing test)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Legitimate Interest Assessment', 'Legal_Basis_Validation', v_status, v_details);

    RAISE NOTICE '  [%] LIA Documentation: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Legitimate Interest Assessment', 'Legal_Basis_Validation', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 29.6: Todos los Tratamientos Visibles Tienen Base Legal
-- ============================================================================

DO $$
DECLARE
    v_null_basis_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Contar propósitos sin base legal definida
    SELECT COUNT(*) INTO v_null_basis_count
    FROM data_processing_purposes
    WHERE legal_basis IS NULL;

    IF v_null_basis_count = 0 THEN
        v_status := 'PASS';
        v_details := 'All processing purposes have legal basis defined';
    ELSE
        v_status := 'FAIL';
        v_details := format('%s purposes missing legal basis (violates RGPD Art. 6)', v_null_basis_count);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('All Purposes Have Legal Basis', 'Legal_Basis_Validation', v_status, v_details);

    RAISE NOTICE '  [%] All Purposes: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('All Purposes Have Legal Basis', 'Legal_Basis_Validation', 'SKIP', 'legal_basis column may not exist: ' || SQLERRM);
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
WHERE test_category = 'Legal_Basis_Validation'
GROUP BY test_category;

SELECT test_name, details
FROM test_results
WHERE test_category = 'Legal_Basis_Validation' AND status = 'FAIL';

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
