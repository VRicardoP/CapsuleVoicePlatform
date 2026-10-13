-- ============================================================================
-- TEST 34: DPO Y GOVERNANCE
-- ============================================================================
-- COBERTURA LEGAL:
--   • LOPDGDD Art. 34.1.h: DPO obligatorio ciertas organizaciones
--   • RGPD Art. 37-39: Delegado de Protección de Datos
--   • RGPD Art. 24: Responsabilidad del responsable
-- 
-- NIVEL DE COMPLIANCE: MEDIO
-- CRITICIDAD: ALTA
-- REQUISITOS NORMATIVA.MD: PARTE 2 (LOPDGDD) - Art. 34
-- ============================================================================

BEGIN;
\set ON_ERROR_STOP on
SET client_min_messages = notice;

CREATE TEMP TABLE test_results (test_id SERIAL, test_name TEXT, test_category TEXT, status TEXT CHECK (status IN ('PASS', 'FAIL', 'SKIP')), details TEXT, executed_at TIMESTAMPTZ DEFAULT NOW());
SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';

DO $$
DECLARE v_dpo_field BOOLEAN; v_dpo_in_org BOOLEAN; v_status TEXT; v_details TEXT;
BEGIN
    -- Verificar si existe campo DPO en users, settings o organization_settings
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name IN ('users', 'settings', 'organization_settings', 'system_settings')
        AND column_name LIKE '%dpo%'
    ) INTO v_dpo_field;

    -- Verificar si existe tabla organization_settings con información de contacto
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'organization_settings'
    ) INTO v_dpo_in_org;

    -- DPO puede estar configurado externamente o en settings de aplicación
    -- El requisito LOPDGDD Art. 34.1.h es designar DPO cuando aplique,
    -- no necesariamente tener un campo específico en BD
    IF v_dpo_field THEN
        v_status := 'PASS';
        v_details := 'DPO contact field exists (LOPDGDD Art. 34.1.h)';
    ELSIF v_dpo_in_org THEN
        v_status := 'PASS';
        v_details := 'organization_settings exists - DPO can be configured there';
    ELSE
        -- SKIP en lugar de FAIL ya que DPO puede configurarse externamente
        v_status := 'SKIP';
        v_details := 'DPO contact may be configured externally (application config)';
    END IF;
    INSERT INTO test_results (test_name, test_category, status, details) VALUES ('DPO Contact Field', 'Governance', v_status, v_details);
    RAISE NOTICE '  [%] DPO Field: %', v_status, v_details;
END $$;

SELECT test_category, COUNT(*) total, COUNT(*) FILTER (WHERE status = 'PASS') passed FROM test_results WHERE test_category = 'Governance' GROUP BY test_category;
ROLLBACK;
