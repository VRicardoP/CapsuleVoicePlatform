-- ============================================================================
-- TEST 35: RETENCIÓN LOGS IA
-- ============================================================================
-- COBERTURA LEGAL:
--   • AI Act Art. 12.4: Logs IA mínimo 6 meses
--   • AI Act Art. 12.1: Registro automático eventos
-- 
-- NIVEL DE COMPLIANCE: MEDIO
-- CRITICIDAD: MEDIA
-- REQUISITOS NORMATIVA.MD: PARTE 3 (AI Act) - Art. 12
-- ============================================================================

BEGIN;
\set ON_ERROR_STOP on
SET client_min_messages = notice;

CREATE TEMP TABLE test_results (test_id SERIAL, test_name TEXT, test_category TEXT, status TEXT CHECK (status IN ('PASS', 'FAIL', 'SKIP')), details TEXT, executed_at TIMESTAMPTZ DEFAULT NOW());

DO $$
DECLARE v_retention_field BOOLEAN; v_status TEXT; v_details TEXT;
BEGIN
    SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ai_decision_logs' AND column_name = 'retention_period') INTO v_retention_field;
    IF v_retention_field THEN v_status := 'PASS'; v_details := 'AI logs retention field exists (AI Act Art. 12.4)';
    ELSE v_status := 'FAIL'; v_details := 'RECOMMENDATION: Add retention_period to ai_decision_logs (min 6 months)'; END IF;
    INSERT INTO test_results (test_name, test_category, status, details) VALUES ('AI Logs Retention Field', 'AI_Compliance', v_status, v_details);
    RAISE NOTICE '  [%] AI Retention: %', v_status, v_details;
END $$;

SELECT test_category, COUNT(*) total, COUNT(*) FILTER (WHERE status = 'PASS') passed FROM test_results WHERE test_category = 'AI_Compliance' GROUP BY test_category;
ROLLBACK;
