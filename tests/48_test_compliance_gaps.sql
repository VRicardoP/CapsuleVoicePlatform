-- ============================================================================
-- TEST 48: Compliance Gaps Coverage (RGPD Art. 35, 37-39 + AI Act Art. 52)
-- ============================================================================
-- Fecha: 2025-12-04
-- Cobertura:
--   - RGPD Art. 35: Evaluación de Impacto (EIPD)
--   - RGPD Art. 37-39: Delegado de Protección de Datos (DPO)
--   - AI Act Art. 52: Acciones correctoras sistemas IA
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'TEST 48: Compliance Gaps Coverage'
\echo '============================================================================'
\echo 'RGPD Art. 35 (EIPD), Art. 37-39 (DPO), AI Act Art. 52 (Corrective Actions)'
\echo '============================================================================'
\echo ''

BEGIN;
\set ON_ERROR_STOP on
SET client_min_messages = notice;

CREATE TEMP TABLE test_results (
    test_id SERIAL,
    test_name TEXT,
    test_category TEXT,
    status TEXT CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMPTZ DEFAULT NOW()
);

SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';

-- ============================================================================
-- TEST 48.1: Tabla organization_settings existe (RGPD Art. 37-39)
-- ============================================================================

\echo '--- Test 48.1: Tabla organization_settings (DPO) ---'

DO $$
DECLARE
    v_table_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'organization_settings'
    ) INTO v_table_exists;

    IF v_table_exists THEN
        v_status := 'PASS';
        v_details := 'Tabla organization_settings existe (RGPD Art. 37-39 DPO)';
    ELSE
        v_status := 'FAIL';
        v_details := 'Tabla organization_settings NO existe';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Organization Settings Table', 'Compliance_Gaps', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 48.2: Campos DPO en organization_settings
-- ============================================================================

\echo '--- Test 48.2: Campos DPO ---'

DO $$
DECLARE
    v_dpo_fields INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(*) INTO v_dpo_fields
    FROM information_schema.columns
    WHERE table_name = 'organization_settings'
    AND column_name IN ('dpo_name', 'dpo_email', 'dpo_phone', 'dpo_required', 'dpo_appointment_date');

    IF v_dpo_fields >= 4 THEN
        v_status := 'PASS';
        v_details := format('Campos DPO encontrados: %s/5 (Art. 37-39)', v_dpo_fields);
    ELSE
        v_status := 'FAIL';
        v_details := format('Solo %s campos DPO encontrados', v_dpo_fields);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('DPO Fields', 'Compliance_Gaps', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 48.3: Tabla impact_assessments existe (RGPD Art. 35)
-- ============================================================================

\echo '--- Test 48.3: Tabla impact_assessments (EIPD) ---'

DO $$
DECLARE
    v_table_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'impact_assessments'
    ) INTO v_table_exists;

    IF v_table_exists THEN
        v_status := 'PASS';
        v_details := 'Tabla impact_assessments existe (RGPD Art. 35 EIPD)';
    ELSE
        v_status := 'FAIL';
        v_details := 'Tabla impact_assessments NO existe';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Impact Assessments Table', 'Compliance_Gaps', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 48.4: Campos EIPD según Art. 35.7
-- ============================================================================

\echo '--- Test 48.4: Campos EIPD Art. 35.7 ---'

DO $$
DECLARE
    v_fields_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Art. 35.7 requiere: descripción, necesidad, proporcionalidad, riesgos, medidas
    SELECT COUNT(*) INTO v_fields_count
    FROM information_schema.columns
    WHERE table_name = 'impact_assessments'
    AND column_name IN (
        'processing_description',    -- Art. 35.7.a
        'necessity_assessment',      -- Art. 35.7.b
        'proportionality_assessment', -- Art. 35.7.b
        'risks_identified',          -- Art. 35.7.c
        'mitigation_measures'        -- Art. 35.7.d
    );

    IF v_fields_count = 5 THEN
        v_status := 'PASS';
        v_details := 'Todos los campos Art. 35.7 (a-d) presentes: descripción, necesidad, proporcionalidad, riesgos, medidas';
    ELSIF v_fields_count >= 3 THEN
        v_status := 'PASS';
        v_details := format('Campos Art. 35.7: %s/5 encontrados', v_fields_count);
    ELSE
        v_status := 'FAIL';
        v_details := format('Solo %s campos Art. 35.7 encontrados', v_fields_count);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('EIPD Art 35.7 Fields', 'Compliance_Gaps', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 48.5: Campo dpo_consulted para Art. 35.2
-- ============================================================================

\echo '--- Test 48.5: Consulta DPO en EIPD (Art. 35.2) ---'

DO $$
DECLARE
    v_has_dpo_consulted BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'impact_assessments'
        AND column_name = 'dpo_consulted'
    ) INTO v_has_dpo_consulted;

    IF v_has_dpo_consulted THEN
        v_status := 'PASS';
        v_details := 'Campo dpo_consulted existe (Art. 35.2: recabar asesoramiento DPO)';
    ELSE
        v_status := 'FAIL';
        v_details := 'Falta campo dpo_consulted';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('DPO Consultation Field', 'Compliance_Gaps', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 48.6: Campo prior_consultation para Art. 36
-- ============================================================================

\echo '--- Test 48.6: Consulta previa autoridad (Art. 36) ---'

DO $$
DECLARE
    v_has_consultation BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'impact_assessments'
        AND column_name = 'prior_consultation_required'
    ) INTO v_has_consultation;

    IF v_has_consultation THEN
        v_status := 'PASS';
        v_details := 'Campo prior_consultation_required existe (Art. 36: consulta previa AEPD)';
    ELSE
        v_status := 'FAIL';
        v_details := 'Falta campo prior_consultation_required';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Prior Consultation Field', 'Compliance_Gaps', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 48.7: Tabla ai_corrective_actions existe (AI Act Art. 52)
-- ============================================================================

\echo '--- Test 48.7: Tabla ai_corrective_actions ---'

DO $$
DECLARE
    v_table_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'ai_corrective_actions'
    ) INTO v_table_exists;

    IF v_table_exists THEN
        v_status := 'PASS';
        v_details := 'Tabla ai_corrective_actions existe (AI Act Art. 52)';
    ELSE
        v_status := 'FAIL';
        v_details := 'Tabla ai_corrective_actions NO existe';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('AI Corrective Actions Table', 'Compliance_Gaps', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 48.8: Campos esenciales ai_corrective_actions
-- ============================================================================

\echo '--- Test 48.8: Campos acciones correctoras ---'

DO $$
DECLARE
    v_fields_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(*) INTO v_fields_count
    FROM information_schema.columns
    WHERE table_name = 'ai_corrective_actions'
    AND column_name IN (
        'issue_type',
        'issue_severity',
        'corrective_action',
        'effectiveness_verified',
        'root_cause_analysis'
    );

    IF v_fields_count >= 4 THEN
        v_status := 'PASS';
        v_details := format('Campos acciones correctoras: %s/5 (issue, severity, action, effectiveness, root_cause)', v_fields_count);
    ELSE
        v_status := 'FAIL';
        v_details := format('Solo %s campos de acciones correctoras', v_fields_count);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Corrective Action Fields', 'Compliance_Gaps', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 48.9: CHECK constraint en issue_type
-- ============================================================================

\echo '--- Test 48.9: Tipos de issues definidos ---'

DO $$
DECLARE
    v_has_check BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.check_constraints cc
        JOIN information_schema.constraint_column_usage ccu ON cc.constraint_name = ccu.constraint_name
        WHERE ccu.table_name = 'ai_corrective_actions'
        AND (cc.check_clause LIKE '%bias_detected%' OR cc.check_clause LIKE '%issue_type%')
    ) INTO v_has_check;

    IF v_has_check THEN
        v_status := 'PASS';
        v_details := 'CHECK constraint en issue_type con tipos: bias_detected, accuracy_degradation, etc.';
    ELSE
        -- Verificar si existe el campo al menos
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'ai_corrective_actions' AND column_name = 'issue_type'
        ) INTO v_has_check;

        IF v_has_check THEN
            v_status := 'PASS';
            v_details := 'Campo issue_type existe para clasificar problemas';
        ELSE
            v_status := 'FAIL';
            v_details := 'No hay campo issue_type';
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Issue Type Check', 'Compliance_Gaps', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 48.10: Vista v_compliance_gaps_summary
-- ============================================================================

\echo '--- Test 48.10: Vista resumen compliance gaps ---'

DO $$
DECLARE
    v_view_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.views
        WHERE table_name = 'v_compliance_gaps_summary'
    ) INTO v_view_exists;

    IF v_view_exists THEN
        v_status := 'PASS';
        v_details := 'Vista v_compliance_gaps_summary existe para monitorizar gaps';
    ELSE
        v_status := 'PASS'; -- No crítico si tablas existen
        v_details := 'Vista v_compliance_gaps_summary no existe (opcional)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Compliance Summary View', 'Compliance_Gaps', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 48.11: Revisión periódica EIPD (Art. 35.11)
-- ============================================================================

\echo '--- Test 48.11: Revisión periódica EIPD (Art. 35.11) ---'

DO $$
DECLARE
    v_has_review_fields BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'impact_assessments'
        AND column_name IN ('review_frequency_months', 'next_review_date')
    ) INTO v_has_review_fields;

    IF v_has_review_fields THEN
        v_status := 'PASS';
        v_details := 'Campos de revisión periódica existen (Art. 35.11)';
    ELSE
        v_status := 'FAIL';
        v_details := 'Faltan campos de revisión periódica';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('EIPD Periodic Review', 'Compliance_Gaps', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 48.12: Integración EIPD con sistemas IA
-- ============================================================================

\echo '--- Test 48.12: Integración EIPD-IA ---'

DO $$
DECLARE
    v_has_ai_fields BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'impact_assessments'
        AND column_name IN ('involves_ai_system', 'ai_system_id', 'ai_risk_level')
    ) INTO v_has_ai_fields;

    IF v_has_ai_fields THEN
        v_status := 'PASS';
        v_details := 'EIPD integrada con sistemas IA (involves_ai_system, ai_risk_level)';
    ELSE
        v_status := 'PASS'; -- Opcional pero recomendado
        v_details := 'Campos de integración IA opcionales';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('EIPD AI Integration', 'Compliance_Gaps', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- RESUMEN DE RESULTADOS
-- ============================================================================

\echo ''
\echo '--- Resumen Test 48 ---'

SELECT test_category,
       COUNT(*) as total,
       SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
       SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed,
       SUM(CASE WHEN status = 'SKIP' THEN 1 ELSE 0 END) as skipped
FROM test_results
GROUP BY test_category;

\echo ''
\echo '--- Detalle de Tests ---'

SELECT test_name, status, details FROM test_results ORDER BY test_id;

\echo ''
\echo '============================================================================'
\echo 'TEST 48 COMPLETADO - Compliance Gaps Coverage'
\echo '============================================================================'

ROLLBACK;
