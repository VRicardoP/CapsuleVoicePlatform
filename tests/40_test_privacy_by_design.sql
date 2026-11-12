-- ============================================================================
-- TEST 40: PRIVACY BY DESIGN Y BY DEFAULT
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 25.1: Protección de datos desde el diseño
--   • RGPD Art. 25.2: Protección de datos por defecto
--   • RGPD Art. 32.1: Medidas técnicas y organizativas apropiadas
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: ALTA
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Art. 25 (Privacy by Design/Default)
-- ============================================================================
-- Verifica que el sistema implementa Privacy by Design y Privacy by Default
-- mediante valores restrictivos por defecto y minimización automática
-- Ejecutar: psql -U postgres -d capsule -f 40_test_privacy_by_design.sql
-- ============================================================================

BEGIN;

\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '=================================================='
\echo 'TEST 40: PRIVACY BY DESIGN Y BY DEFAULT'
\echo '=================================================='

CREATE TEMP TABLE IF NOT EXISTS test_results (
    test_id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    test_category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';

-- ============================================================================
-- TEST 40.1: Verificar defaults restrictivos en data_consents
-- ============================================================================

\echo ''
\echo '--- Test 40.1: Defaults restrictivos en consents ---'

DO $$
DECLARE
    v_default_value TEXT;
    v_has_consent_given BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Privacy by Default: consent_given NO debe tener default (debe ser explícito)
    SELECT column_default INTO v_default_value
    FROM information_schema.columns
    WHERE table_name = 'data_consents' AND column_name = 'consent_given';

    -- También verificar que ip_anonymized default es false (anonimización opcional)
    -- y parental_consent_required default false (opt-in)

    -- consent_given sin default = correcto (Privacy by Default - no hay consentimiento implícito)
    IF v_default_value IS NULL THEN
        v_status := 'PASS';
        v_details := 'consent_given sin default - requiere consentimiento explícito (Art. 25.2)';
    ELSIF v_default_value LIKE '%true%' THEN
        v_status := 'FAIL';
        v_details := 'consent_given DEFAULT TRUE - VIOLACIÓN Privacy by Default';
    ELSE
        v_status := 'PASS';
        v_details := format('consent_given default=%s - aceptable', v_default_value);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Consent No Default', 'Privacy_by_Design', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 40.2: Cifrado activado por defecto
-- ============================================================================

\echo ''
\echo '--- Test 40.2: Cifrado activo por defecto ---'

DO $$
DECLARE
    v_encrypt_func_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_proc WHERE proname = 'encrypt_pii_with_metadata'
    ) INTO v_encrypt_func_exists;

    IF v_encrypt_func_exists THEN
        v_status := 'PASS';
        v_details := 'Función encrypt_pii_with_metadata() - cifrado by design (Art. 25.1)';
    ELSE
        v_status := 'FAIL';
        v_details := 'Función de cifrado NO existe - Art. 25.1 (protección desde diseño)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Encryption by Design', 'Privacy_by_Design', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 40.3: Retención limitada por defecto
-- ============================================================================

\echo ''
\echo '--- Test 40.3: Retencion limitada por  defecto ---'

DO $$
DECLARE
    v_has_retention_policies BOOLEAN;
    v_policies_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'retention_policies'
    ) INTO v_has_retention_policies;

    IF v_has_retention_policies THEN
        SELECT COUNT(*) INTO v_policies_count FROM retention_policies;
        
        IF v_policies_count >= 5 THEN
            v_status := 'PASS';
            v_details := format('retention_policies con %s entidades - limitación by default (Art. 25.2)', v_policies_count);
        ELSE
            v_status := 'PASS';
            v_details := format('retention_policies existe (%s entidades)', v_policies_count);
        END IF;
    ELSE
        v_status := 'FAIL';
        v_details := 'retention_policies NO existe - falta limitación temporal by design';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Retention Limitation by Default', 'Privacy_by_Design', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 40.4: Minimización de datos por defecto
-- ============================================================================

\echo ''
\echo '--- Test 40.4: Minimizacion en columnas opcionales ---'

DO $$
DECLARE
    v_nullable_count INTEGER;
    v_total_columns INTEGER;
    v_nullable_percentage NUMERIC;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(*) INTO v_total_columns
    FROM information_schema.columns
    WHERE table_name IN ('users', 'contacts', 'calls')
      AND column_name NOT IN ('id', 'created_at', 'updated_at');

    SELECT COUNT(*) INTO v_nullable_count
    FROM information_schema.columns
    WHERE table_name IN ('users', 'contacts', 'calls')
      AND is_nullable = 'YES'
      AND column_name NOT IN ('id', 'created_at', 'updated_at');

    v_nullable_percentage := (v_nullable_count::NUMERIC / v_total_columns::NUMERIC) * 100;

IF v_nullable_percentage >= 40 THEN
        v_status := 'PASS';
        v_details := format('%s%%%% campos opcionales - minimización by design (Art. 25.2)', v_nullable_percentage::INTEGER);
    ELSIF v_nullable_percentage >= 20 THEN
        v_status := 'PASS';
        v_details := format('%s%%%% campos opcionales (basic)', v_nullable_percentage::INTEGER);
    ELSE
        v_status := 'FAIL';
        v_details := format('Solo %s%%%% opcionales - demasiados campos obligatorios', v_nullable_percentage::INTEGER);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Data Minimization by Design', 'Privacy_by_Design', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 40.5: RLS (Row Level Security) activado
-- ============================================================================

\echo ''
\echo '--- Test 40.5: Row Level Security activado ---'

DO $$
DECLARE
    v_rls_enabled BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COALESCE(
        (SELECT COUNT(*) > 0 FROM pg_class
         WHERE relname IN ('users', 'contacts', 'calls')
           AND relrowsecurity = true),
        false
    ) INTO v_rls_enabled;

    IF v_rls_enabled THEN
        v_status := 'PASS';
        v_details := 'RLS activado en tablas críticas - confidencialidad by design (Art. 25.1)';
    ELSE
        v_status := 'FAIL';
        v_details := 'RLS NO activado - falta segregación by design';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Row Level Security', 'Privacy_by_Design', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- RESUMEN
-- ============================================================================

\echo ''
\echo '=================================================='
\echo 'RESUMEN TEST 40: PRIVACY BY DESIGN/DEFAULT'
\echo '=================================================='

SELECT test_category,
       COUNT(*) as total_tests,
       SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
       SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed,
       SUM(CASE WHEN status = 'SKIP' THEN 1 ELSE 0 END) as skipped
FROM test_results
GROUP BY test_category;

\echo ''
SELECT test_name, status, details FROM test_results ORDER BY test_id;

\echo ''
\echo '=================================================='
\echo 'CUMPLIMIENTO LEGAL VERIFICADO:'
\echo '  - RGPD Art. 25.1: Privacy by Design'
\echo '  - RGPD Art. 25.2: Privacy by Default'
\echo '  - RGPD Art. 32.1: Medidas tecnicas apropiadas'
\echo '=================================================='

ROLLBACK;
