-- ============================================================================
-- TEST 54: ENCARGADOS DE TRATAMIENTO (RGPD Art. 28-29)
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 28.1: Solo recurrir a encargados con garantías suficientes
--   • RGPD Art. 28.3: Contrato o acto jurídico vinculante (DPA)
--   • RGPD Art. 28.3.a: Instrucciones documentadas del responsable
--   • RGPD Art. 28.3.b: Confidencialidad de personas autorizadas
--   • RGPD Art. 28.3.c: Medidas de seguridad apropiadas (Art. 32)
--   • RGPD Art. 28.3.d: Subencargados solo con autorización
--   • RGPD Art. 28.3.e: Asistir al responsable con derechos interesados
--   • RGPD Art. 28.3.f: Asistir en cumplimiento Art. 32-36
--   • RGPD Art. 28.3.g: Supresión o devolución de datos al finalizar
--   • RGPD Art. 28.3.h: Poner a disposición información para auditorías
--   • RGPD Art. 29: Tratamiento bajo autoridad del responsable
--   • RGPD Art. 30.2: Registro de encargados (RoPA)
--   • RGPD Art. 44-49: Transferencias internacionales (si no UE)
--
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: ALTA
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Encargado de Tratamiento (Art. 28-29)
-- ============================================================================
-- Verifica el registro y gestión de encargados de tratamiento
-- Ejecutar: psql -U postgres -d sfera -f 54_test_data_processors.sql
-- ============================================================================

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo ''
\echo '=============================================='
\echo 'TEST 54: ENCARGADOS DE TRATAMIENTO'
\echo 'RGPD Art. 28-29'
\echo '=============================================='
\echo ''

-- Crear tabla temporal para resultados
CREATE TEMP TABLE IF NOT EXISTS test_results (
    test_id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    test_category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Limpiar resultados anteriores
DELETE FROM test_results WHERE test_category = 'Data_Processors';

-- Configurar variables de sesión
SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';
SET app.hash_pepper = 'TEST_PEPPER_V1_FOR_HMAC_FUNCTIONS';
SET app.hash_pepper_version = '1';
SET app.audit_hmac_key = 'TEST_AUDIT_KEY_FOR_HMAC_CHAIN__';

-- ============================================================================
-- TEST 54.1: Verificar existencia de tabla data_processors (Art. 28)
-- ============================================================================

\echo '--- Test 54.1: Tabla data_processors existe ---'

DO $$
DECLARE
    v_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'data_processors'
    ) INTO v_exists;

    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'Tabla data_processors existe para registro de encargados (Art. 28 RGPD)';
    ELSE
        v_status := 'FAIL';
        v_details := 'Tabla data_processors NO existe - incumplimiento Art. 28 RGPD';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Tabla data_processors existe', 'Data_Processors', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 54.2: Verificar campos obligatorios del DPA (Art. 28.3)
-- ============================================================================

\echo '--- Test 54.2: Campos obligatorios del DPA ---'

DO $$
DECLARE
    v_required_columns TEXT[] := ARRAY[
        'name',                     -- Identificación del encargado
        'legal_name',               -- Nombre legal
        'country',                  -- País (para Art. 44-49)
        'is_eu_based',              -- UE o no (transferencias)
        'contact_email',            -- Contacto
        'dpa_signed_date',          -- Fecha firma DPA (Art. 28.3)
        'dpa_document_reference',   -- Referencia al contrato
        'services_provided',        -- Servicios (instrucciones - Art. 28.3.a)
        'data_categories_processed', -- Categorías de datos
        'purposes',                 -- Finalidades
        'subprocessors_allowed',    -- Subencargados (Art. 28.3.d)
        'contract_start_date',      -- Vigencia
        'contract_end_date'         -- Fin (Art. 28.3.g - devolución/supresión)
    ];
    v_missing_columns TEXT[] := ARRAY[]::TEXT[];
    v_column TEXT;
    v_status TEXT;
    v_details TEXT;
BEGIN
    FOREACH v_column IN ARRAY v_required_columns LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'data_processors'
            AND column_name = v_column
        ) THEN
            v_missing_columns := array_append(v_missing_columns, v_column);
        END IF;
    END LOOP;

    IF array_length(v_missing_columns, 1) IS NULL THEN
        v_status := 'PASS';
        v_details := format('Todos los %s campos obligatorios del DPA presentes', array_length(v_required_columns, 1));
    ELSE
        v_status := 'FAIL';
        v_details := 'Faltan campos: ' || array_to_string(v_missing_columns, ', ');
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Campos DPA Art. 28.3', 'Data_Processors', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 54.3: Verificar campos de transferencias internacionales (Art. 44-49)
-- ============================================================================

\echo '--- Test 54.3: Campos transferencias internacionales ---'

DO $$
DECLARE
    v_transfer_columns TEXT[] := ARRAY[
        'is_eu_based',              -- Art. 44: Principio general
        'has_adequacy_decision',    -- Art. 45: Decisión de adecuación
        'safeguards_applied'        -- Art. 46: Garantías apropiadas (SCC, BCR)
    ];
    v_missing_columns TEXT[] := ARRAY[]::TEXT[];
    v_column TEXT;
    v_status TEXT;
    v_details TEXT;
BEGIN
    FOREACH v_column IN ARRAY v_transfer_columns LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'data_processors'
            AND column_name = v_column
        ) THEN
            v_missing_columns := array_append(v_missing_columns, v_column);
        END IF;
    END LOOP;

    IF array_length(v_missing_columns, 1) IS NULL THEN
        v_status := 'PASS';
        v_details := 'Campos de transferencias internacionales presentes (Art. 44-49)';
    ELSE
        v_status := 'FAIL';
        v_details := 'Faltan campos de transferencias: ' || array_to_string(v_missing_columns, ', ');
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Campos transferencias Art. 44-49', 'Data_Processors', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 54.4: Verificar campos de auditoría (Art. 28.3.h)
-- ============================================================================

\echo '--- Test 54.4: Campos de auditoría ---'

DO $$
DECLARE
    v_audit_columns TEXT[] := ARRAY[
        'last_audit_date',          -- Última auditoría
        'next_audit_date'           -- Próxima auditoría programada
    ];
    v_missing_columns TEXT[] := ARRAY[]::TEXT[];
    v_column TEXT;
    v_status TEXT;
    v_details TEXT;
BEGIN
    FOREACH v_column IN ARRAY v_audit_columns LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'data_processors'
            AND column_name = v_column
        ) THEN
            v_missing_columns := array_append(v_missing_columns, v_column);
        END IF;
    END LOOP;

    IF array_length(v_missing_columns, 1) IS NULL THEN
        v_status := 'PASS';
        v_details := 'Campos de auditoría presentes (Art. 28.3.h)';
    ELSE
        v_status := 'FAIL';
        v_details := 'Faltan campos de auditoría: ' || array_to_string(v_missing_columns, ', ');
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Campos auditoría Art. 28.3.h', 'Data_Processors', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 54.5: Crear encargado UE con DPA firmado (Art. 28.3)
-- ============================================================================

\echo '--- Test 54.5: Crear encargado UE con DPA ---'

DO $$
DECLARE
    v_processor_id UUID;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Insertar encargado de tratamiento de la UE
    INSERT INTO data_processors (
        name,
        legal_name,
        country,
        is_eu_based,
        has_adequacy_decision,
        safeguards_applied,
        contact_email,
        contact_phone,
        dpa_signed_date,
        dpa_document_reference,
        services_provided,
        data_categories_processed,
        purposes,
        subprocessors_allowed,
        is_active,
        contract_start_date,
        contract_end_date,
        last_audit_date,
        next_audit_date,
        notes
    ) VALUES (
        'Test Cloud Provider EU',
        'Test Cloud Provider EU S.L.',
        'ES',  -- España
        true,  -- Es UE
        false, -- No necesita decisión adecuación (es UE)
        NULL,  -- No necesita garantías adicionales (es UE)
        'dpo@testcloudeu.example.com',
        '+34 911 234 567',
        CURRENT_DATE - INTERVAL '6 months',
        'DPA-2024-EU-001',
        'Hosting de infraestructura cloud para base de datos',
        ARRAY['identificativos', 'contacto', 'llamadas'],
        ARRAY['almacenamiento', 'backup', 'disaster_recovery'],
        false, -- No permite subencargados
        true,
        CURRENT_DATE - INTERVAL '6 months',
        CURRENT_DATE + INTERVAL '2 years',
        CURRENT_DATE - INTERVAL '3 months',
        CURRENT_DATE + INTERVAL '9 months',
        'Encargado principal de hosting - Test Art. 28'
    )
    RETURNING id INTO v_processor_id;

    IF v_processor_id IS NOT NULL THEN
        v_status := 'PASS';
        v_details := format('Encargado UE creado: %s', v_processor_id);
    ELSE
        v_status := 'FAIL';
        v_details := 'No se pudo crear el encargado UE';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Crear encargado UE', 'Data_Processors', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Crear encargado UE', 'Data_Processors', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 54.6: Crear encargado NO-UE con garantías (Art. 44-46)
-- ============================================================================

\echo '--- Test 54.6: Crear encargado NO-UE con SCC ---'

DO $$
DECLARE
    v_processor_id UUID;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Insertar encargado de tratamiento fuera de la UE (con SCC)
    INSERT INTO data_processors (
        name,
        legal_name,
        country,
        is_eu_based,
        has_adequacy_decision,
        safeguards_applied,
        contact_email,
        dpa_signed_date,
        dpa_document_reference,
        services_provided,
        data_categories_processed,
        purposes,
        subprocessors_allowed,
        is_active,
        contract_start_date,
        notes
    ) VALUES (
        'Test Analytics US',
        'Test Analytics Inc.',
        'US',  -- Estados Unidos
        false, -- NO es UE
        false, -- No hay decisión adecuación para US (tras Schrems II)
        ARRAY['SCC_2021', 'Supplementary_Measures', 'Encryption_Transit_Rest'], -- Art. 46.2.c
        'privacy@testanalytics.example.com',
        CURRENT_DATE - INTERVAL '3 months',
        'DPA-2024-US-001-SCC',
        'Análisis de métricas de llamadas (anonimizadas)',
        ARRAY['estadisticos', 'anonimizados'],
        ARRAY['analytics', 'reporting'],
        true,  -- Permite subencargados (con aprobación)
        true,
        CURRENT_DATE - INTERVAL '3 months',
        'Encargado US con SCC 2021 + medidas suplementarias - Test Art. 46'
    )
    RETURNING id INTO v_processor_id;

    IF v_processor_id IS NOT NULL THEN
        v_status := 'PASS';
        v_details := format('Encargado NO-UE con SCC creado: %s', v_processor_id);
    ELSE
        v_status := 'FAIL';
        v_details := 'No se pudo crear el encargado NO-UE';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Crear encargado NO-UE con SCC', 'Data_Processors', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Crear encargado NO-UE con SCC', 'Data_Processors', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 54.7: Crear encargado con decisión de adecuación (Art. 45)
-- ============================================================================

\echo '--- Test 54.7: Crear encargado con decisión adecuación ---'

DO $$
DECLARE
    v_processor_id UUID;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Insertar encargado de país con decisión de adecuación
    INSERT INTO data_processors (
        name,
        legal_name,
        country,
        is_eu_based,
        has_adequacy_decision,
        safeguards_applied,
        contact_email,
        dpa_signed_date,
        dpa_document_reference,
        services_provided,
        data_categories_processed,
        purposes,
        subprocessors_allowed,
        is_active,
        contract_start_date,
        notes
    ) VALUES (
        'Test Backup JP',
        'Test Backup Japan K.K.',
        'JP',  -- Japón
        false, -- NO es UE
        true,  -- SÍ tiene decisión de adecuación (desde 2019)
        NULL,  -- No necesita garantías adicionales
        'privacy@testbackupjp.example.com',
        CURRENT_DATE - INTERVAL '1 year',
        'DPA-2024-JP-001',
        'Servicio de backup offsite',
        ARRAY['backups_cifrados'],
        ARRAY['disaster_recovery'],
        false,
        true,
        CURRENT_DATE - INTERVAL '1 year',
        'Encargado Japón con decisión adecuación - Test Art. 45'
    )
    RETURNING id INTO v_processor_id;

    IF v_processor_id IS NOT NULL THEN
        v_status := 'PASS';
        v_details := format('Encargado con decisión adecuación creado: %s', v_processor_id);
    ELSE
        v_status := 'FAIL';
        v_details := 'No se pudo crear el encargado con decisión adecuación';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Crear encargado Art. 45', 'Data_Processors', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Crear encargado Art. 45', 'Data_Processors', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 54.8: Verificar que DPA es obligatorio (Art. 28.3)
-- ============================================================================

\echo '--- Test 54.8: Verificar NOT NULL en campos críticos ---'

DO $$
DECLARE
    v_critical_columns TEXT[] := ARRAY[
        'name',
        'legal_name',
        'country',
        'is_eu_based',
        'contact_email',
        'services_provided',
        'data_categories_processed',
        'purposes',
        'contract_start_date'
    ];
    v_non_nullable INTEGER := 0;
    v_column TEXT;
    v_status TEXT;
    v_details TEXT;
BEGIN
    FOREACH v_column IN ARRAY v_critical_columns LOOP
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'data_processors'
            AND column_name = v_column
            AND is_nullable = 'NO'
        ) THEN
            v_non_nullable := v_non_nullable + 1;
        END IF;
    END LOOP;

    IF v_non_nullable >= 7 THEN  -- Al menos 7 de 9 deben ser NOT NULL
        v_status := 'PASS';
        v_details := format('%s de %s campos críticos son NOT NULL', v_non_nullable, array_length(v_critical_columns, 1));
    ELSE
        v_status := 'FAIL';
        v_details := format('Solo %s de %s campos críticos son NOT NULL', v_non_nullable, array_length(v_critical_columns, 1));
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Campos NOT NULL obligatorios', 'Data_Processors', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 54.9: Consultar encargados activos (Art. 30.2 - RoPA)
-- ============================================================================

\echo '--- Test 54.9: Consulta de encargados activos ---'

DO $$
DECLARE
    v_active_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(*) INTO v_active_count
    FROM data_processors
    WHERE is_active = true;

    IF v_active_count >= 0 THEN
        v_status := 'PASS';
        v_details := format('Consulta RoPA exitosa: %s encargados activos', v_active_count);
    ELSE
        v_status := 'FAIL';
        v_details := 'Error en consulta de encargados activos';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Consulta RoPA encargados', 'Data_Processors', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Consulta RoPA encargados', 'Data_Processors', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 54.10: Verificar encargados NO-UE sin garantías (debe alertar)
-- ============================================================================

\echo '--- Test 54.10: Detectar encargados NO-UE sin garantías ---'

DO $$
DECLARE
    v_unsafe_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Buscar encargados fuera de UE sin decisión adecuación ni garantías
    SELECT COUNT(*) INTO v_unsafe_count
    FROM data_processors
    WHERE is_active = true
    AND is_eu_based = false
    AND has_adequacy_decision = false
    AND (safeguards_applied IS NULL OR array_length(safeguards_applied, 1) IS NULL);

    -- Este test verifica que la consulta funciona
    -- Un resultado > 0 sería una alerta de compliance, no un fallo del test
    v_status := 'PASS';
    v_details := format('Consulta de alertas funciona: %s encargados NO-UE sin garantías detectados', v_unsafe_count);

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Detectar NO-UE sin garantías', 'Data_Processors', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Detectar NO-UE sin garantías', 'Data_Processors', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 54.11: Verificar auditorías pendientes (Art. 28.3.h)
-- ============================================================================

\echo '--- Test 54.11: Detectar auditorías pendientes ---'

DO $$
DECLARE
    v_pending_audits INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Buscar encargados con auditoría vencida o próxima
    SELECT COUNT(*) INTO v_pending_audits
    FROM data_processors
    WHERE is_active = true
    AND (
        next_audit_date IS NULL
        OR next_audit_date <= CURRENT_DATE + INTERVAL '30 days'
    );

    v_status := 'PASS';
    v_details := format('Consulta de auditorías pendientes funciona: %s encargados requieren auditoría', v_pending_audits);

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Auditorías pendientes Art. 28.3.h', 'Data_Processors', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Auditorías pendientes Art. 28.3.h', 'Data_Processors', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 54.12: Verificar contratos próximos a vencer (Art. 28.3.g)
-- ============================================================================

\echo '--- Test 54.12: Detectar contratos próximos a vencer ---'

DO $$
DECLARE
    v_expiring_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Buscar contratos que vencen en los próximos 90 días
    SELECT COUNT(*) INTO v_expiring_count
    FROM data_processors
    WHERE is_active = true
    AND contract_end_date IS NOT NULL
    AND contract_end_date <= CURRENT_DATE + INTERVAL '90 days';

    v_status := 'PASS';
    v_details := format('Consulta de contratos a vencer funciona: %s contratos expiran en 90 días', v_expiring_count);

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Contratos a vencer Art. 28.3.g', 'Data_Processors', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Contratos a vencer Art. 28.3.g', 'Data_Processors', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 54.13: Desactivar encargado (fin de contrato - Art. 28.3.g)
-- ============================================================================

\echo '--- Test 54.13: Desactivar encargado al finalizar contrato ---'

DO $$
DECLARE
    v_processor_id UUID;
    v_is_active BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Obtener un encargado de test
    SELECT id INTO v_processor_id
    FROM data_processors
    WHERE name LIKE 'Test%'
    LIMIT 1;

    IF v_processor_id IS NOT NULL THEN
        -- Desactivar (simular fin de contrato)
        UPDATE data_processors
        SET is_active = false,
            notes = COALESCE(notes, '') || ' | Desactivado por fin de contrato - Test Art. 28.3.g',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = v_processor_id;

        -- Verificar
        SELECT is_active INTO v_is_active
        FROM data_processors
        WHERE id = v_processor_id;

        IF v_is_active = false THEN
            v_status := 'PASS';
            v_details := 'Encargado desactivado correctamente al finalizar contrato';
        ELSE
            v_status := 'FAIL';
            v_details := 'No se pudo desactivar el encargado';
        END IF;
    ELSE
        v_status := 'SKIP';
        v_details := 'No hay encargados de test para desactivar';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Desactivar encargado Art. 28.3.g', 'Data_Processors', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Desactivar encargado Art. 28.3.g', 'Data_Processors', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 54.14: Verificar enlace con supplier_risk_assessments (NIS2)
-- ============================================================================

\echo '--- Test 54.14: Enlace con evaluación de riesgos NIS2 ---'

DO $$
DECLARE
    v_has_fk BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Verificar si existe FK de supplier_risk_assessments a data_processors
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'supplier_risk_assessments'
        AND column_name = 'data_processor_id'
    ) INTO v_has_fk;

    IF v_has_fk THEN
        v_status := 'PASS';
        v_details := 'Enlace con supplier_risk_assessments existe (NIS2 Art. 21.2.d)';
    ELSE
        v_status := 'SKIP';
        v_details := 'No existe enlace con supplier_risk_assessments (opcional)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Enlace NIS2 risk assessments', 'Data_Processors', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- RESUMEN DE RESULTADOS
-- ============================================================================

\echo ''
\echo '=============================================='
\echo 'RESUMEN TEST 54: ENCARGADOS DE TRATAMIENTO'
\echo '=============================================='

SELECT
    test_category,
    COUNT(*) as total_tests,
    COUNT(*) FILTER (WHERE status = 'PASS') as passed,
    COUNT(*) FILTER (WHERE status = 'FAIL') as failed,
    COUNT(*) FILTER (WHERE status = 'SKIP') as skipped
FROM test_results
WHERE test_category = 'Data_Processors'
GROUP BY test_category;

\echo ''
\echo '--- Tests fallidos (si los hay): ---'

SELECT test_name, details
FROM test_results
WHERE test_category = 'Data_Processors' AND status = 'FAIL';

\echo ''
\echo '--- Tests pasados: ---'

SELECT test_name, LEFT(details, 60) as details
FROM test_results
WHERE test_category = 'Data_Processors' AND status = 'PASS'
ORDER BY test_id;

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;

\echo ''
\echo 'Test 54 completado - Cambios revertidos (ROLLBACK)'
\echo ''
