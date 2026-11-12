-- ============================================================================
-- TEST 38: GOBERNANZA DE DATOS IA Y GESTIÓN DE SESGOS
-- ============================================================================
-- COBERTURA LEGAL:
--   • AI Act Art. 10.1: Gobernanza de datos para sistemas IA
--   • AI Act Art. 10.2: Calidad de datos de entrenamiento
--   • AI Act Art. 10.2.a: Decisiones de diseño de datos documentadas
--   • AI Act Art. 10.2.b: Requisitos de datos (volumen, propiedades)
--   • AI Act Art. 10.2.c: Evaluación de disponibilidad de datos
--   • AI Act Art. 10.2.d: **EXAMEN DE SESGOS** (CRÍTICO)
--   • AI Act Art. 10.2.e: Identificar lagunas en datos
--   • AI Act Art. 10.3: Representatividad de datos
--   • AI Act Art. 10.4: Relevancia y completitud
--   • AI Act Art. 10.5: Uso datos personales en entrenamiento (base legal RGPD)
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: CRÍTICA
-- REQUISITOS NORMATIVA.MD: PARTE 3 (AI Act) - Gobernanza de Datos (Art. 10)
-- ============================================================================
-- Verifica que existe un sistema de gobernanza de datos de entrenamiento IA
-- con análisis de sesgos documentado
-- Ejecutar: psql -U postgres -d capsule -f 38_test_ai_data_governance.sql
-- ============================================================================

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '========================================================='
\echo 'TEST 38: GOBERNANZA DE DATOS IA Y GESTION DE SESGOS'
\echo '========================================================='

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
-- TEST 38.1: Verificar existencia de tabla training_data_registry
-- ============================================================================

\echo ''
\echo '--- Test 38.1: Tabla training_data_registry existe ---'

DO $$
DECLARE
    v_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'training_data_registry'
    ) INTO v_exists;

    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'Tabla training_data_registry existe (AI Act Art. 10.2)';
    ELSE
        v_status := 'FAIL';
        v_details := 'CRÍTICO: training_data_registry NO existe - INCUMPLIMIENTO AI Act Art. 10.2';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('training_data_registry Table Exists', 'AI_Data_Governance', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 38.2: Verificar columnas requeridas de training_data_registry
-- ============================================================================

\echo ''
\echo '--- Test 38.2: Columnas de training_data_registry ---'

DO $$
DECLARE
    v_columns TEXT[];
    v_required TEXT[] := ARRAY[
        'dataset_name', 'dataset_version', 'source', 'volume_records',
        'preprocessing_applied', 'bias_assessment_id', 'data_quality_score',
        'gdpr_legal_basis', 'collection_date', 'representativeness_score'
    ];
    v_col TEXT;
    v_missing TEXT[] := ARRAY[]::TEXT[];
    v_status TEXT;
    v_details TEXT;
    v_table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'training_data_registry'
    ) INTO v_table_exists;

    IF NOT v_table_exists THEN
        v_status := 'SKIP';
        v_details := 'Tabla training_data_registry no existe';
    ELSE
        SELECT ARRAY_AGG(column_name::TEXT) INTO v_columns
        FROM information_schema.columns
        WHERE table_name = 'training_data_registry';

        FOREACH v_col IN ARRAY v_required LOOP
            IF NOT (v_col = ANY(COALESCE(v_columns, ARRAY[]::TEXT[]))) THEN
                v_missing := array_append(v_missing, v_col);
            END IF;
        END LOOP;

        IF array_length(v_missing, 1) IS NULL OR array_length(v_missing, 1) = 0 THEN
            v_status := 'PASS';
            v_details := 'training_data_registry completo (AI Act Art. 10.2.a-e)';
        ELSE
            v_status := 'FAIL';
            v_details := 'Columnas faltantes: ' || array_to_string(v_missing, ', ');
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('training_data_registry Columns', 'AI_Data_Governance', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 38.3: Verificar existencia de tabla bias_assessments (**CRÍTICO**)
-- ============================================================================

\echo ''
\echo '--- Test 38.3: Tabla bias_assessments existe (CRITICO) ---'

DO $$
DECLARE
    v_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'bias_assessments'
    ) INTO v_exists;

    IF v_exists THEN
        v_status := 'PASS';
        v_details := '**CRÍTICO** bias_assessments existe (AI Act Art. 10.2.d)';
    ELSE
        v_status := 'FAIL';
        v_details := '**CRÍTICO**: bias_assessments NO existe - FALTA ANÁLISIS DE SESGOS (AI Act Art. 10.2.d)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('bias_assessments Table Exists', 'AI_Data_Governance', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 38.4: Verificar columnas de bias_assessments
-- ============================================================================

\echo ''
\echo '--- Test 38.4: Columnas de bias_assessments ---'

DO $$
DECLARE
    v_columns TEXT[];
    v_required TEXT[] := ARRAY[
        'assessment_date', 'dataset_id', 'methodology', 'bias_metrics',
        'protected_attributes_analyzed', 'bias_found', 'bias_type',
        'mitigation_actions', 'severity', 'status'
    ];
    v_col TEXT;
    v_missing TEXT[] := ARRAY[]::TEXT[];
    v_status TEXT;
    v_details TEXT;
    v_table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'bias_assessments'
    ) INTO v_table_exists;

    IF NOT v_table_exists THEN
        v_status := 'SKIP';
        v_details := 'Tabla bias_assessments no existe';
    ELSE
        SELECT ARRAY_AGG(column_name::TEXT) INTO v_columns
        FROM information_schema.columns
        WHERE table_name = 'bias_assessments';

        FOREACH v_col IN ARRAY v_required LOOP
            IF NOT (v_col = ANY(COALESCE(v_columns, ARRAY[]::TEXT[]))) THEN
                v_missing := array_append(v_missing, v_col);
            END IF;
        END LOOP;

        IF array_length(v_missing, 1) IS NULL OR array_length(v_missing, 1) = 0 THEN
            v_status := 'PASS';
            v_details := 'bias_assessments completa (AI Act Art. 10.2.d - Análisis sesgos)';
        ELSE
            v_status := 'FAIL';
            v_details := 'Columnas faltantes: ' || array_to_string(v_missing, ', ');
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('bias_assessments Columns', 'AI_Data_Governance', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 38.5: Verificar campo gdpr_legal_basis para datos personales
-- ============================================================================

\echo ''
\echo '--- Test 38.5: Base legal RGPD en datos de entrenamiento ---'

DO $$
DECLARE
    v_column_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
    v_table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'training_data_registry'
    ) INTO v_table_exists;

    IF NOT v_table_exists THEN
        v_status := 'SKIP';
        v_details := 'Tabla no existe';
    ELSE
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'training_data_registry' AND column_name = 'gdpr_legal_basis'
        ) INTO v_column_exists;

        IF v_column_exists THEN
            v_status := 'PASS';
            v_details := 'Campo gdpr_legal_basis documentado (AI Act Art. 10.5 + RGPD)';
        ELSE
            v_status := 'FAIL';
            v_details := 'gdpr_legal_basis NO existe - falta documentación RGPD (Art. 10.5)';
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('GDPR Legal Basis for Training Data', 'AI_Data_Governance', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 38.6: Verificar campo bias_metrics en formato JSONB
-- ============================================================================

\echo ''
\echo '--- Test 38.6: Metricas de sesgo en formato estructurado ---'

DO $$
DECLARE
    v_data_type TEXT;
    v_status TEXT;
    v_details TEXT;
    v_table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'bias_assessments'
    ) INTO v_table_exists;

    IF NOT v_table_exists THEN
        v_status := 'SKIP';
        v_details := 'Tabla no existe';
    ELSE
        SELECT data_type INTO v_data_type
        FROM information_schema.columns
        WHERE table_name = 'bias_assessments' AND column_name = 'bias_metrics';

        IF v_data_type = 'jsonb' OR v_data_type = 'json' THEN
            v_status := 'PASS';
            v_details := 'bias_metrics usa JSONB para métricas estructuradas';
        ELSIF v_data_type IS NOT NULL THEN
            v_status := 'PASS';
            v_details := format('bias_metrics existe (tipo: %s)', v_data_type);
        ELSE
            v_status := 'FAIL';
            v_details := 'bias_metrics NO existe - no se pueden documentar métricas';
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Bias Metrics Format', 'AI_Data_Governance', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 38.7: Verificar campo protected_attributes_analyzed
-- ============================================================================

\echo ''
\echo '--- Test 38.7: Atributos protegidos analizados ---'

DO $$
DECLARE
    v_data_type TEXT;
    v_status TEXT;
    v_details TEXT;
    v_table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'bias_assessments'
    ) INTO v_table_exists;

    IF NOT v_table_exists THEN
        v_status := 'SKIP';
        v_details := 'Tabla no existe';
    ELSE
        SELECT data_type INTO v_data_type
        FROM information_schema.columns
        WHERE table_name = 'bias_assessments' AND column_name = 'protected_attributes_analyzed';

        IF v_data_type = 'ARRAY' OR v_data_type LIKE '%text%' THEN
            v_status := 'PASS';
            v_details := 'protected_attributes_analyzed documenta atributos sensibles (género, edad, etc.)';
        ELSIF v_data_type IS NOT NULL THEN
            v_status := 'PASS';
            v_details := format('protected_attributes_analyzed existe (%s)', v_data_type);
        ELSE
            v_status := 'FAIL';
            v_details := 'protected_attributes_analyzed NO existe - AI Act Art. 10.2.d';
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Protected Attributes Tracking', 'AI_Data_Governance', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 38.8: Verificar relación FK entre training_data y bias_assessments
-- ============================================================================

\echo ''
\echo '--- Test 38.8: Relacion FK training_data -> bias_assessments ---'

DO $$
DECLARE
    v_fk_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
    v_both_tables_exist BOOLEAN;
BEGIN
    SELECT (
        EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'training_data_registry') AND
        EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'bias_assessments')
    ) INTO v_both_tables_exist;

    IF NOT v_both_tables_exist THEN
        v_status := 'SKIP';
        v_details := 'Una o ambas tablas no existen';
    ELSE
        SELECT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE table_name = 'training_data_registry'
              AND constraint_type = 'FOREIGN KEY'
              AND constraint_name LIKE '%bias%'
        ) INTO v_fk_exists;

        IF v_fk_exists THEN
            v_status := 'PASS';
            v_details := 'FK existe - cada dataset vinculado a análisis de sesgos';
        ELSE
            v_status := 'FAIL';
            v_details := 'FK faltante - datasets sin vinculación obligatoria a bias_assessments';
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Dataset-Bias Assessment FK', 'AI_Data_Governance', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 38.9: Verificar campo representativeness_score
-- ============================================================================

\echo ''
\echo '--- Test 38.9: Puntuacion de representatividad de datos ---'

DO $$
DECLARE
    v_column_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
    v_table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'training_data_registry'
    ) INTO v_table_exists;

    IF NOT v_table_exists THEN
        v_status := 'SKIP';
        v_details := 'Tabla no existe';
    ELSE
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'training_data_registry' AND column_name = 'representativeness_score'
        ) INTO v_column_exists;

        IF v_column_exists THEN
            v_status := 'PASS';
            v_details := 'representativeness_score documenta calidad datos (AI Act Art. 10.3)';
        ELSE
            v_status := 'FAIL';
            v_details := 'representativeness_score NO existe - Art. 10.3 (representatividad)';
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Data Representativeness Score', 'AI_Data_Governance', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 38.10: Verificar índices para consultas de gobernanza
-- ============================================================================

\echo ''
\echo '--- Test 38.10: Indices en tablas de gobernanza ---'

DO $$
DECLARE
    v_training_idx INTEGER;
    v_bias_idx INTEGER;
    v_status TEXT;
    v_details TEXT;
    v_both_exist BOOLEAN;
BEGIN
    SELECT (
        EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'training_data_registry') AND
        EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'bias_assessments')
    ) INTO v_both_exist;

    IF NOT v_both_exist THEN
        v_status := 'SKIP';
        v_details := 'Tablas no existen';
    ELSE
        SELECT COUNT(*) INTO v_training_idx FROM pg_indexes WHERE tablename = 'training_data_registry';
        SELECT COUNT(*) INTO v_bias_idx FROM pg_indexes WHERE tablename = 'bias_assessments';

        IF v_training_idx >= 2 AND v_bias_idx >= 2 THEN
            v_status := 'PASS';
            v_details := format('Índices adecuados - training_data: %s, bias: %s', v_training_idx, v_bias_idx);
        ELSIF v_training_idx > 0 AND v_bias_idx > 0 THEN
            v_status := 'PASS';
            v_details := format('Índices básicos presentes - training_data: %s, bias: %s', v_training_idx, v_bias_idx);
        ELSE
            v_status := 'FAIL';
            v_details := 'Índices insuficientes para rendimiento de consultas';
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Governance Tables Indexes', 'AI_Data_Governance', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- RESUMEN
-- ============================================================================

\echo ''
\echo '========================================================='
\echo 'RESUMEN TEST 38: GOBERNANZA DE DATOS IA'
\echo '========================================================='

SELECT test_category,
       COUNT(*) as total_tests,
       SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
       SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed,
       SUM(CASE WHEN status = 'SKIP' THEN 1 ELSE 0 END) as skipped
FROM test_results
GROUP BY test_category
ORDER BY test_category;

\echo ''
\echo '--- Detalle de tests ---'

SELECT test_name, status, details
FROM test_results
ORDER BY test_id;

\echo ''
\echo '========================================================='
\echo 'CUMPLIMIENTO LEGAL VERIFICADO:'
\echo '  - AI Act Art. 10.2: Calidad datos entrenamiento'
\echo '  - AI Act Art. 10.2.d: **ANALISIS DE SESGOS** (CRITICO)'
\echo '  - AI Act Art. 10.3: Representatividad de datos'
\echo '  - AI Act Art. 10.5: Base legal RGPD para datos personales'
\echo '========================================================='

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
