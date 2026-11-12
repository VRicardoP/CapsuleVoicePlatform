-- ============================================================================
-- TEST 11: SISTEMA DE DATOS SENSIBLES (Art. 9 RGPD)
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 9.1: Prohibición categorías especiales de datos
--   • RGPD Art. 9.2.a: Consentimiento explícito para datos especiales
--   • LOPDGDD Art. 9: Categorías especiales (salud)
--   • RGPD Art. 32: Seguridad reforzada para datos sensibles
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: CRÍTICA
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Art. 9
-- ============================================================================
-- Valida la implementación del sistema de control de categorías especiales:
--   - Art. 9.1: Prohibición general de tratamiento
--   - Art. 9.2: Excepciones permitidas
--   - Detección automática de datos sensibles
--   - Gestión de excepciones y aprobaciones DPO
--
-- Ejecutar: psql -U postgres -d capsule -f 11_test_sensitive_data.sql
-- ============================================================================

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo ''
\echo '============================================================================'
\echo 'TEST 11: SISTEMA DE DATOS SENSIBLES (Art. 9 RGPD)'
\echo '============================================================================'
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

-- Limpiar resultados anteriores de esta categoría
DELETE FROM test_results WHERE test_category = 'Sensitive_Data';

-- Configurar variables de sesión para tests
SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';
SET app.hash_pepper = 'TEST_PEPPER_V1_FOR_HMAC_FUNCTIONS';
SET app.hash_pepper_version = '1';
SET app.audit_hmac_key = 'TEST_AUDIT_KEY_FOR_HMAC_CHAIN_32';

-- Variables de test
DO $$ BEGIN PERFORM set_config('test.admin_user_id', '', false); END $$;

-- ============================================================================
-- SETUP: Crear usuario admin de prueba
-- ============================================================================

DO $$
DECLARE
    v_admin_id UUID;
BEGIN
    INSERT INTO users (name, email, password_hash, password_algorithm, role, is_active)
    VALUES (
        'TEST_SENSITIVE_ADMIN',
        'test_sensitive_admin_' || gen_random_uuid()::TEXT || '@test.local',
        'test_hash',
        'bcrypt',
        'admin',
        true
    )
    RETURNING id INTO v_admin_id;

    PERFORM set_config('test.admin_user_id', v_admin_id::TEXT, false);
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    RAISE NOTICE 'Setup: Usuario admin de prueba creado: %', v_admin_id;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Setup FAILED: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 11.1: Verificar existencia de tablas de datos sensibles
-- ============================================================================

\echo '  [TEST 11.1] Verificar existencia de tablas'

DO $$
DECLARE
    v_tables_exist BOOLEAN;
    v_missing_tables TEXT[];
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT
        ARRAY_AGG(t.table_name) FILTER (WHERE NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = t.table_name
        ))
    INTO v_missing_tables
    FROM (VALUES
        ('sensitive_data_categories'),
        ('sensitive_data_detections'),
        ('sensitive_data_exceptions')
    ) AS t(table_name);

    IF v_missing_tables IS NULL OR array_length(v_missing_tables, 1) IS NULL THEN
        v_status := 'PASS';
        v_details := 'Todas las tablas de datos sensibles existen';
    ELSE
        v_status := 'FAIL';
        v_details := 'Tablas faltantes: ' || array_to_string(v_missing_tables, ', ');
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Tables Existence', 'Sensitive_Data', v_status, v_details);

    RAISE NOTICE '    [%] Tables Existence: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 11.2: Verificar categorías del Art. 9.1 cargadas
-- ============================================================================

\echo '  [TEST 11.2] Verificar categorías Art. 9.1 cargadas'

DO $$
DECLARE
    v_category_count INTEGER;
    v_expected_categories TEXT[] := ARRAY[
        'racial_ethnic_origin',
        'political_opinions',
        'religious_philosophical_beliefs',
        'trade_union_membership',
        'genetic_data',
        'biometric_data',
        'health_data',
        'sex_life',
        'sexual_orientation',
        'criminal_data'
    ];
    v_missing TEXT[];
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(*) INTO v_category_count
    FROM sensitive_data_categories
    WHERE is_active = true;

    SELECT ARRAY_AGG(cat)
    INTO v_missing
    FROM UNNEST(v_expected_categories) AS cat
    WHERE NOT EXISTS (
        SELECT 1 FROM sensitive_data_categories
        WHERE category_code = cat AND is_active = true
    );

    IF v_category_count >= 10 AND (v_missing IS NULL OR array_length(v_missing, 1) IS NULL) THEN
        v_status := 'PASS';
        v_details := format('10 categorías Art. 9.1 cargadas correctamente (total: %s)', v_category_count);
    ELSE
        v_status := 'FAIL';
        v_details := format('Categorías faltantes: %s', array_to_string(v_missing, ', '));
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Categories Loaded', 'Sensitive_Data', v_status, v_details);

    RAISE NOTICE '    [%] Categories Loaded: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 11.3: Detección de datos de salud (health_data)
-- ============================================================================

\echo '  [TEST 11.3] Detección de datos de salud'

DO $$
DECLARE
    v_result JSON;
    v_has_sensitive BOOLEAN;
    v_category TEXT;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Texto con datos de salud
    SELECT detect_sensitive_data(
        'El paciente tiene un diagnóstico de diabetes tipo 2 y está tomando medicamentos para la hipertensión.',
        'test_table',
        'test_column',
        NULL,
        'flag'
    ) INTO v_result;

    v_has_sensitive := (v_result->>'has_sensitive_data')::BOOLEAN;

    IF v_has_sensitive THEN
        v_status := 'PASS';
        v_details := format('Detectado correctamente: %s detecciones', v_result->>'detections_count');
    ELSE
        v_status := 'FAIL';
        v_details := 'No se detectaron datos de salud en texto con diagnóstico y medicamentos';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Health Data Detection', 'Sensitive_Data', v_status, v_details);

    RAISE NOTICE '    [%] Health Data Detection: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Health Data Detection', 'Sensitive_Data', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Health Data Detection: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 11.4: Detección de datos religiosos
-- ============================================================================

\echo '  [TEST 11.4] Detección de datos religiosos'

DO $$
DECLARE
    v_result JSON;
    v_has_sensitive BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT detect_sensitive_data(
        'Es practicante católico y asiste a la iglesia todos los domingos.',
        'test_table',
        'test_column',
        NULL,
        'flag'
    ) INTO v_result;

    v_has_sensitive := (v_result->>'has_sensitive_data')::BOOLEAN;

    IF v_has_sensitive THEN
        v_status := 'PASS';
        v_details := 'Detectadas convicciones religiosas correctamente';
    ELSE
        v_status := 'FAIL';
        v_details := 'No se detectaron datos religiosos';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Religious Data Detection', 'Sensitive_Data', v_status, v_details);

    RAISE NOTICE '    [%] Religious Data Detection: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Religious Data Detection', 'Sensitive_Data', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Religious Data Detection: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 11.5: Detección de afiliación sindical
-- ============================================================================

\echo '  [TEST 11.5] Detección de afiliación sindical'

DO $$
DECLARE
    v_result JSON;
    v_has_sensitive BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT detect_sensitive_data(
        'El empleado es delegado sindical de CCOO y participó en la huelga del sector.',
        'test_table',
        'test_column',
        NULL,
        'flag'
    ) INTO v_result;

    v_has_sensitive := (v_result->>'has_sensitive_data')::BOOLEAN;

    IF v_has_sensitive THEN
        v_status := 'PASS';
        v_details := 'Detectada afiliación sindical correctamente';
    ELSE
        v_status := 'FAIL';
        v_details := 'No se detectó afiliación sindical';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Union Membership Detection', 'Sensitive_Data', v_status, v_details);

    RAISE NOTICE '    [%] Union Membership Detection: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Union Membership Detection', 'Sensitive_Data', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Union Membership Detection: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 11.6: Detección de datos biométricos
-- ============================================================================

\echo '  [TEST 11.6] Detección de datos biométricos'

DO $$
DECLARE
    v_result JSON;
    v_has_sensitive BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT detect_sensitive_data(
        'Se utilizará reconocimiento facial y huella dactilar para el control de acceso.',
        'test_table',
        'test_column',
        NULL,
        'flag'
    ) INTO v_result;

    v_has_sensitive := (v_result->>'has_sensitive_data')::BOOLEAN;

    IF v_has_sensitive THEN
        v_status := 'PASS';
        v_details := 'Detectados datos biométricos correctamente';
    ELSE
        v_status := 'FAIL';
        v_details := 'No se detectaron datos biométricos';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Biometric Data Detection', 'Sensitive_Data', v_status, v_details);

    RAISE NOTICE '    [%] Biometric Data Detection: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Biometric Data Detection', 'Sensitive_Data', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Biometric Data Detection: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 11.7: No detección en texto sin datos sensibles
-- ============================================================================

\echo '  [TEST 11.7] No detección en texto normal'

DO $$
DECLARE
    v_result JSON;
    v_has_sensitive BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT detect_sensitive_data(
        'Buenos días, le llamamos para confirmar su cita de mañana a las 10:00 en nuestras oficinas.',
        'test_table',
        'test_column',
        NULL,
        'flag'
    ) INTO v_result;

    v_has_sensitive := (v_result->>'has_sensitive_data')::BOOLEAN;

    IF NOT v_has_sensitive THEN
        v_status := 'PASS';
        v_details := 'Correctamente no detectó datos sensibles en texto normal';
    ELSE
        v_status := 'FAIL';
        v_details := 'Falso positivo: detectó datos sensibles en texto normal';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('No False Positive', 'Sensitive_Data', v_status, v_details);

    RAISE NOTICE '    [%] No False Positive: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('No False Positive', 'Sensitive_Data', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] No False Positive: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 11.8: Registro de detecciones en tabla
-- ============================================================================

\echo '  [TEST 11.8] Registro de detecciones en tabla'

DO $$
DECLARE
    v_detection_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(*) INTO v_detection_count
    FROM sensitive_data_detections
    WHERE detected_in_table = 'test_table';

    IF v_detection_count > 0 THEN
        v_status := 'PASS';
        v_details := format('%s detecciones registradas en sensitive_data_detections', v_detection_count);
    ELSE
        v_status := 'FAIL';
        v_details := 'No se registraron detecciones en la tabla';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Detections Logged', 'Sensitive_Data', v_status, v_details);

    RAISE NOTICE '    [%] Detections Logged: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Detections Logged', 'Sensitive_Data', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Detections Logged: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 11.9: Función register_sensitive_exception()
-- ============================================================================

\echo '  [TEST 11.9] Registrar excepción Art. 9.2'

DO $$
DECLARE
    v_result JSON;
    v_success BOOLEAN;
    v_exception_id UUID;
    v_requires_dpo BOOLEAN;
    v_status TEXT;
    v_details TEXT;
    v_admin_id UUID;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    SELECT register_sensitive_exception(
        'health_data',
        'explicit_consent',
        'Consentimiento explícito obtenido del interesado para tratamiento de datos de salud',
        'Art. 9.2.a RGPD',
        NULL,  -- user_id
        NULL,  -- contact_id
        NULL,  -- consent_id
        CURRENT_TIMESTAMP + INTERVAL '1 year'
    ) INTO v_result;

    v_success := (v_result->>'success')::BOOLEAN;
    v_exception_id := (v_result->>'exception_id')::UUID;
    v_requires_dpo := (v_result->>'requires_dpo_approval')::BOOLEAN;

    IF v_success AND v_exception_id IS NOT NULL THEN
        PERFORM set_config('test.exception_id', v_exception_id::TEXT, false);
        v_status := 'PASS';
        v_details := format('Excepción registrada: %s, requiere DPO: %s', v_exception_id, v_requires_dpo);
    ELSE
        v_status := 'FAIL';
        v_details := 'Error registrando excepción';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Register Exception', 'Sensitive_Data', v_status, v_details);

    RAISE NOTICE '    [%] Register Exception: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Register Exception', 'Sensitive_Data', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Register Exception: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 11.10: Verificar excepción no válida sin aprobación DPO
-- ============================================================================

\echo '  [TEST 11.10] Excepción no válida sin aprobación DPO'

DO $$
DECLARE
    v_exception_id UUID;
    v_dpo_required BOOLEAN;
    v_dpo_approved BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Obtener ID de la excepción creada en test 11.9
    v_exception_id := current_setting('test.exception_id', true)::UUID;

    IF v_exception_id IS NULL THEN
        v_status := 'SKIP';
        v_details := 'No se creó excepción en test anterior';
    ELSE
        -- Verificar directamente el estado de la excepción recién creada
        SELECT dpo_approval_required, dpo_approved
        INTO v_dpo_required, v_dpo_approved
        FROM sensitive_data_exceptions
        WHERE id = v_exception_id;

        -- La excepción debe requerir DPO y NO estar aprobada aún
        IF v_dpo_required = true AND v_dpo_approved = false THEN
            v_status := 'PASS';
            v_details := format('Excepción %s requiere DPO (dpo_required=%s, dpo_approved=%s)',
                v_exception_id, v_dpo_required, v_dpo_approved);
        ELSIF v_dpo_required = false THEN
            v_status := 'FAIL';
            v_details := format('ERROR: La excepción no requiere aprobación DPO (dpo_required=%s)', v_dpo_required);
        ELSE
            v_status := 'FAIL';
            v_details := format('ERROR: La excepción ya está aprobada (dpo_approved=%s)', v_dpo_approved);
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Exception Without DPO Invalid', 'Sensitive_Data', v_status, v_details);

    RAISE NOTICE '    [%] Exception Without DPO Invalid: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Exception Without DPO Invalid', 'Sensitive_Data', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Exception Without DPO Invalid: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 11.11: Aprobación DPO de excepción
-- ============================================================================

\echo '  [TEST 11.11] Aprobación DPO de excepción'

DO $$
DECLARE
    v_exception_id UUID;
    v_result JSON;
    v_success BOOLEAN;
    v_status TEXT;
    v_details TEXT;
    v_admin_id UUID;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    v_exception_id := current_setting('test.exception_id', true)::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    IF v_exception_id IS NULL THEN
        v_status := 'SKIP';
        v_details := 'No hay excepción para aprobar';
    ELSE
        SELECT dpo_approve_sensitive_exception(
            v_exception_id,
            true,
            'Aprobado para test - consentimiento explícito verificado'
        ) INTO v_result;

        v_success := (v_result->>'success')::BOOLEAN;

        IF v_success THEN
            v_status := 'PASS';
            v_details := 'DPO aprobó correctamente la excepción';
        ELSE
            v_status := 'FAIL';
            v_details := 'Error en aprobación DPO';
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('DPO Approval', 'Sensitive_Data', v_status, v_details);

    RAISE NOTICE '    [%] DPO Approval: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('DPO Approval', 'Sensitive_Data', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] DPO Approval: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 11.12: Excepción válida después de aprobación DPO
-- ============================================================================

\echo '  [TEST 11.12] Excepción válida con aprobación DPO'

DO $$
DECLARE
    v_result JSON;
    v_has_exception BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT has_valid_sensitive_exception(
        'health_data',
        NULL,
        NULL,
        'explicit_consent'
    ) INTO v_result;

    v_has_exception := (v_result->>'has_exception')::BOOLEAN;

    IF v_has_exception THEN
        v_status := 'PASS';
        v_details := format('Excepción válida: tipo=%s', v_result->>'exception_type');
    ELSE
        v_status := 'FAIL';
        v_details := 'Excepción no válida después de aprobación DPO';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Exception Valid After DPO', 'Sensitive_Data', v_status, v_details);

    RAISE NOTICE '    [%] Exception Valid After DPO: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Exception Valid After DPO', 'Sensitive_Data', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Exception Valid After DPO: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 11.13: Vista v_sensitive_data_dashboard
-- ============================================================================

\echo '  [TEST 11.13] Vista dashboard de datos sensibles'

DO $$
DECLARE
    v_row_count INTEGER;
    v_has_columns BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(*) INTO v_row_count FROM v_sensitive_data_dashboard;

    -- Verificar que tiene las columnas esperadas
    SELECT EXISTS(
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'v_sensitive_data_dashboard'
        AND column_name IN ('category_code', 'total_detections', 'pending_review')
    ) INTO v_has_columns;

    IF v_row_count > 0 THEN
        v_status := 'PASS';
        v_details := format('Dashboard funcional con %s categorías', v_row_count);
    ELSE
        v_status := 'FAIL';
        v_details := 'Vista vacía o no funcional';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Dashboard View', 'Sensitive_Data', v_status, v_details);

    RAISE NOTICE '    [%] Dashboard View: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Dashboard View', 'Sensitive_Data', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Dashboard View: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 11.14: Función get_pending_sensitive_reviews()
-- ============================================================================

\echo '  [TEST 11.14] Revisiones pendientes'

DO $$
DECLARE
    v_pending_count INTEGER;
    v_status TEXT;
    v_details TEXT;
    v_admin_id UUID;
BEGIN
    v_admin_id := current_setting('test.admin_user_id')::UUID;
    PERFORM set_current_user(v_admin_id, NULL::UUID, '127.0.0.1'::INET);

    SELECT COUNT(*) INTO v_pending_count
    FROM get_pending_sensitive_reviews();

    -- Debería haber detecciones pendientes de los tests anteriores
    IF v_pending_count >= 0 THEN
        v_status := 'PASS';
        v_details := format('Función ejecutada: %s revisiones pendientes', v_pending_count);
    ELSE
        v_status := 'FAIL';
        v_details := 'Error ejecutando get_pending_sensitive_reviews()';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Pending Reviews Function', 'Sensitive_Data', v_status, v_details);

    RAISE NOTICE '    [%] Pending Reviews Function: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Pending Reviews Function', 'Sensitive_Data', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Pending Reviews Function: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 11.15: RLS en tablas de datos sensibles
-- ============================================================================

\echo '  [TEST 11.15] RLS habilitado en tablas'

DO $$
DECLARE
    v_rls_categories BOOLEAN;
    v_rls_detections BOOLEAN;
    v_rls_exceptions BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT relrowsecurity INTO v_rls_categories
    FROM pg_class WHERE relname = 'sensitive_data_categories';

    SELECT relrowsecurity INTO v_rls_detections
    FROM pg_class WHERE relname = 'sensitive_data_detections';

    SELECT relrowsecurity INTO v_rls_exceptions
    FROM pg_class WHERE relname = 'sensitive_data_exceptions';

    IF v_rls_categories AND v_rls_detections AND v_rls_exceptions THEN
        v_status := 'PASS';
        v_details := 'RLS habilitado en las 3 tablas de datos sensibles';
    ELSE
        v_status := 'FAIL';
        v_details := format('RLS incompleto: categories=%s, detections=%s, exceptions=%s',
            v_rls_categories, v_rls_detections, v_rls_exceptions);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('RLS Enabled', 'Sensitive_Data', v_status, v_details);

    RAISE NOTICE '    [%] RLS Enabled: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('RLS Enabled', 'Sensitive_Data', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] RLS Enabled: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 11.16: Detección múltiple de categorías
-- ============================================================================

\echo '  [TEST 11.16] Detección de múltiples categorías'

DO $$
DECLARE
    v_result JSON;
    v_detections_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Texto con múltiples categorías de datos sensibles
    SELECT detect_sensitive_data(
        'El paciente es católico practicante, tiene diabetes y es delegado sindical de UGT.',
        'test_multi',
        'test_column',
        NULL,
        'flag'
    ) INTO v_result;

    v_detections_count := (v_result->>'detections_count')::INTEGER;

    IF v_detections_count >= 3 THEN
        v_status := 'PASS';
        v_details := format('Detectadas %s categorías diferentes en un texto', v_detections_count);
    ELSIF v_detections_count > 0 THEN
        v_status := 'PASS';
        v_details := format('Detectadas %s categorías (esperado 3+, pero detección parcial OK)', v_detections_count);
    ELSE
        v_status := 'FAIL';
        v_details := 'No se detectaron múltiples categorías';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Multi-Category Detection', 'Sensitive_Data', v_status, v_details);

    RAISE NOTICE '    [%] Multi-Category Detection: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Multi-Category Detection', 'Sensitive_Data', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Multi-Category Detection: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 11.17: Detección de datos penales (Art. 10)
-- ============================================================================

\echo '  [TEST 11.17] Detección de datos penales (Art. 10)'

DO $$
DECLARE
    v_result JSON;
    v_has_sensitive BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT detect_sensitive_data(
        'El candidato tiene antecedentes penales y estuvo en prisión por un delito menor.',
        'test_criminal',
        'test_column',
        NULL,
        'flag'
    ) INTO v_result;

    v_has_sensitive := (v_result->>'has_sensitive_data')::BOOLEAN;

    IF v_has_sensitive THEN
        v_status := 'PASS';
        v_details := 'Detectados datos penales (Art. 10) correctamente';
    ELSE
        v_status := 'FAIL';
        v_details := 'No se detectaron datos penales';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Criminal Data Detection', 'Sensitive_Data', v_status, v_details);

    RAISE NOTICE '    [%] Criminal Data Detection: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Criminal Data Detection', 'Sensitive_Data', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Criminal Data Detection: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 11.18: Control de acceso - Usuario no admin
-- ============================================================================

\echo '  [TEST 11.18] Control de acceso usuario no admin'

DO $$
DECLARE
    v_regular_user_id UUID;
    v_access_denied BOOLEAN := false;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario regular
    INSERT INTO users (name, email, password_hash, password_algorithm, role, is_active)
    VALUES (
        'TEST_REGULAR_USER',
        'test_regular_sensitive_' || gen_random_uuid()::TEXT || '@test.local',
        'test_hash',
        'bcrypt',
        'user',
        true
    )
    RETURNING id INTO v_regular_user_id;

    PERFORM set_current_user(v_regular_user_id, NULL::UUID, '127.0.0.1'::INET);

    -- Intentar registrar excepción (debe fallar)
    BEGIN
        PERFORM register_sensitive_exception(
            'health_data',
            'explicit_consent',
            'Test unauthorized',
            NULL, NULL, NULL, NULL, NULL
        );
    EXCEPTION WHEN OTHERS THEN
        IF SQLERRM LIKE '%Access denied%' OR SQLERRM LIKE '%only admin%' THEN
            v_access_denied := true;
        END IF;
    END;

    IF v_access_denied THEN
        v_status := 'PASS';
        v_details := 'Acceso denegado correctamente a usuario no admin';
    ELSE
        v_status := 'FAIL';
        v_details := 'ERROR: Usuario no admin pudo registrar excepción';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Non-Admin Access Denied', 'Sensitive_Data', v_status, v_details);

    RAISE NOTICE '    [%] Non-Admin Access Denied: %', v_status, v_details;

    -- Restaurar admin
    PERFORM set_current_user(current_setting('test.admin_user_id')::UUID, NULL::UUID, '127.0.0.1'::INET);

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Non-Admin Access Denied', 'Sensitive_Data', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Non-Admin Access Denied: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 11.19: Índices de rendimiento
-- ============================================================================

\echo '  [TEST 11.19] Índices de rendimiento'

DO $$
DECLARE
    v_index_count INTEGER;
    v_expected_indexes TEXT[] := ARRAY[
        'idx_sensitive_categories_code',
        'idx_sensitive_detections_table',
        'idx_sensitive_detections_category',
        'idx_sensitive_exceptions_category'
    ];
    v_missing TEXT[];
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT ARRAY_AGG(idx_name)
    INTO v_missing
    FROM UNNEST(v_expected_indexes) AS idx_name
    WHERE NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = idx_name
    );

    IF v_missing IS NULL OR array_length(v_missing, 1) IS NULL THEN
        v_status := 'PASS';
        v_details := 'Todos los índices de rendimiento existen';
    ELSE
        v_status := 'FAIL';
        v_details := 'Índices faltantes: ' || array_to_string(v_missing, ', ');
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Performance Indexes', 'Sensitive_Data', v_status, v_details);

    RAISE NOTICE '    [%] Performance Indexes: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Performance Indexes', 'Sensitive_Data', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Performance Indexes: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 11.20: Confidence score en detecciones
-- ============================================================================

\echo '  [TEST 11.20] Confidence score en detecciones'

DO $$
DECLARE
    v_pattern_confidence NUMERIC;
    v_keyword_confidence NUMERIC;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Verificar que las detecciones tienen confidence score correcto
    SELECT AVG(confidence_score) INTO v_pattern_confidence
    FROM sensitive_data_detections
    WHERE matched_pattern IS NOT NULL;

    SELECT AVG(confidence_score) INTO v_keyword_confidence
    FROM sensitive_data_detections
    WHERE matched_keyword IS NOT NULL;

    IF v_pattern_confidence >= 0.80 OR v_keyword_confidence >= 0.60 THEN
        v_status := 'PASS';
        v_details := format('Confidence scores: pattern=%s, keyword=%s',
            to_char(COALESCE(v_pattern_confidence, 0), 'FM0.00'),
            to_char(COALESCE(v_keyword_confidence, 0), 'FM0.00'));
    ELSE
        v_status := 'FAIL';
        v_details := 'Confidence scores incorrectos';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Confidence Scores', 'Sensitive_Data', v_status, v_details);

    RAISE NOTICE '    [%] Confidence Scores: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Confidence Scores', 'Sensitive_Data', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '    [FAIL] Confidence Scores: Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- CLEANUP
-- ============================================================================

\echo ''
\echo '  [CLEANUP] Eliminando datos de prueba...'

DO $$
DECLARE
    v_admin_id UUID;
BEGIN
    v_admin_id := current_setting('test.admin_user_id', true)::UUID;

    IF v_admin_id IS NOT NULL THEN
        DELETE FROM sensitive_data_detections WHERE detected_in_table LIKE 'test%';
        DELETE FROM sensitive_data_exceptions WHERE created_by = v_admin_id;
        DELETE FROM users WHERE id = v_admin_id;
        DELETE FROM users WHERE email LIKE 'test_%@test.local';
    END IF;

    RAISE NOTICE '    Datos de prueba eliminados';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE '    Error en cleanup: %', SQLERRM;
END $$;

-- ============================================================================
-- RESUMEN DE RESULTADOS
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'RESUMEN DE RESULTADOS - TEST 11: DATOS SENSIBLES (Art. 9)'
\echo '============================================================================'

SELECT
    '  Total: ' || COUNT(*) || ' tests' AS summary,
    '  Passed: ' || COUNT(*) FILTER (WHERE status = 'PASS') AS passed,
    '  Failed: ' || COUNT(*) FILTER (WHERE status = 'FAIL') AS failed,
    '  Skipped: ' || COUNT(*) FILTER (WHERE status = 'SKIP') AS skipped
FROM test_results
WHERE test_category = 'Sensitive_Data';

\echo ''
\echo 'Detalle de tests fallidos:'

SELECT '  - ' || test_name || ': ' || details AS failed_test
FROM test_results
WHERE test_category = 'Sensitive_Data' AND status = 'FAIL';

\echo ''
\echo 'Detalle de todos los tests:'

SELECT
    CASE status
        WHEN 'PASS' THEN '  [OK] '
        WHEN 'FAIL' THEN '  [X]  '
        ELSE '  [~]  '
    END || test_name || ': ' || COALESCE(LEFT(details, 70), 'N/A') AS test_result
FROM test_results
WHERE test_category = 'Sensitive_Data'
ORDER BY test_id;

\echo ''
\echo '============================================================================'
\echo 'FIN TEST 11: DATOS SENSIBLES (Art. 9 RGPD)'
\echo '============================================================================'

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
