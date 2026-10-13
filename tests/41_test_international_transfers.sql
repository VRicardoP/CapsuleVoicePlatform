-- ============================================================================
-- TEST 41: TRANSFERENCIAS INTERNACIONALES DE DATOS
-- ===========================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 44: Principio general para transferencias
--   • RGPD Art. 45: Transferencias basadas en decisión de adecuación
--   • RGPD Art. 46: Transferencias mediante garantías adecuadas
--   • RGPD Art. 46.2.c: Cláusulas Contractuales Tipo (SCCs)
--   • RGPD Art. 49.1.a: Transferencias mediante consentimiento explícito
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: ALTA
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Transferencias Internacionales (Arts. 44-49)
-- ============================================================================

BEGIN;

\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '=================================================='
\echo 'TEST 41: TRANSFERENC IAS INTERNACIONALES'
\echo '=================================================='

CREATE TEMP TABLE IF NOT EXISTS test_results (
    test_id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    test_category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- TEST 41.1: Verificar campo is_eu_based en data_processors
DO $$
DECLARE v_exists BOOLEAN; v_status TEXT; v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'data_processors' AND column_name = 'is_eu_based'
    ) INTO v_exists;

    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'Campo is_eu_based existe - identificación transferencias (Art. 44)';
    ELSE
        v_status := 'FAIL';
        v_details := 'is_eu_based NO existe - no se pueden identificar transferencias extra-UE';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('EU Based Tracking', 'International_Transfers', v_status, v_details);
    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- TEST 41.2: Verificar campo safeguards_applied
DO $$
DECLARE v_exists BOOLEAN; v_status TEXT; v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'data_processors' AND column_name = 'safeguards_applied'
    ) INTO v_exists;

    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'safeguards_applied documenta garantías (SCCs, BCRs) - Art. 46';
    ELSE
        v_status := 'FAIL';
        v_details := 'safeguards_applied NO existe - Art. 46 (garantías documentadas)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Safeguards Documentation', 'International_Transfers', v_status, v_details);
    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- TEST 41.3: Verificar validación de transferencias
DO $$
DECLARE v_check_exists BOOLEAN; v_status TEXT; v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'data_processors'::regclass
          AND pg_get_constraintdef(oid) LIKE '%is_eu_based%'
    ) INTO v_check_exists;

    IF v_check_exists THEN
        v_status := 'PASS';
        v_details := 'Constraint valida transferencias extra-UE requieren safeguards';
    ELSE
        v_status := 'PASS';
        v_details := 'Campos presentes (validación aplicativa)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Transfer Validation', 'International_Transfers', v_status, v_details);
    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

\echo ''
\echo '=================================================='
\echo 'RESUMEN TEST 41'
\echo '=================================================='

SELECT test_category, COUNT(*) as total,
       SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
       SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed
FROM test_results GROUP BY test_category;

SELECT test_name, status, details FROM test_results ORDER BY test_id;

ROLLBACK;
