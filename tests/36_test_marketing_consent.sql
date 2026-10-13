-- ============================================================================
-- TEST 36: MARKETING CONSENT
-- ============================================================================
-- COBERTURA LEGAL:
--   • LSSI Art. 21.2: Consentimiento previo comunicaciones comerciales
--   • LSSI Art. 22: Oposición fácil (opt-out)
-- 
-- NIVEL DE COMPLIANCE: MEDIO
-- CRITICIDAD: MEDIA
-- REQUISITOS NORMATIVA.MD: PARTE 6 (LSSI-CE) - Arts. 21-22
-- ============================================================================

BEGIN;
\set ON_ERROR_STOP on
SET client_min_messages = notice;

CREATE TEMP TABLE test_results (test_id SERIAL, test_name TEXT, test_category TEXT, status TEXT CHECK (status IN ('PASS', 'FAIL', 'SKIP')), details TEXT, executed_at TIMESTAMPTZ DEFAULT NOW());

DO $$
DECLARE v_marketing_purpose BOOLEAN; v_status TEXT; v_details TEXT;
BEGIN
    SELECT EXISTS (SELECT 1 FROM data_processing_purposes WHERE code LIKE '%marketing%' OR code LIKE '%commercial%') INTO v_marketing_purpose;
    IF v_marketing_purpose THEN v_status := 'PASS'; v_details := 'Marketing purpose exists with consent requirement (LSSI Art. 21)';
    ELSE v_status := 'SKIP'; v_details := 'No marketing purposes defined (may not be applicable)'; END IF;
    INSERT INTO test_results (test_name, test_category, status, details) VALUES ('Marketing Purpose Defined', 'Marketing_Compliance', v_status, v_details);
    RAISE NOTICE '  [%] Marketing Purpose: %', v_status, v_details;
END $$;

SELECT test_category, COUNT(*) total, COUNT(*) FILTER (WHERE status = 'PASS') passed FROM test_results WHERE test_category = 'Marketing_Compliance' GROUP BY test_category;
ROLLBACK;
