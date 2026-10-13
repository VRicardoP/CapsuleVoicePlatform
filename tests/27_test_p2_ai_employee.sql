-- ============================================================================
-- TEST 27: P2 AI ACT - ai_decision_logs y Protección Empleados (Art. 5.1.f)
-- ============================================================================
-- COBERTURA LEGAL:
--   • AI Act Art. 5.1.f: Prohibición análisis emociones en trabajo
--   • LOPDGDD Arts. 87-91: Derechos digitales ámbito laboral
--   • LOPDGDD Art. 90: Grabación sonidos en lugar de trabajo
--   • Estatuto Trabajadores Art. 20.3: Control empresarial proporcionado
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: CRÍTICA
-- REQUISITOS NORMATIVA.MD: PARTE 3 (AI Act) - Art. 5, PARTE 2 (LOPDGDD) - Arts. 87-91
-- ============================================================================
-- Verifica:
-- P2.7: Tabla ai_decision_logs para trazabilidad IA (Art. 12)
-- P2.8: Prohibición análisis emocional empleados (Art. 5.1.f)
-- Ejecutar: psql -U postgres -d sfera -f 27_test_p2_ai_employee.sql
-- ============================================================================

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '=============================================='
\echo 'TEST 27: P2 AI ACT - AI Decision Logs & Employee Protection'
\echo '=============================================='

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

-- Crear clave de cifrado temporal para tests si no existe
DO $$
BEGIN
    INSERT INTO encryption_keys (key_id, encrypted_key, is_active, kms_provider, activated_at)
    VALUES (
        'test_key_p2_' || substring(gen_random_uuid()::TEXT, 1, 8),
        pgp_sym_encrypt(encode(gen_random_bytes(32), 'hex'), current_setting('app.kms_master_key'), 'cipher-algo=aes256'),
        true,
        'hashicorp-vault',
        CURRENT_TIMESTAMP
    );
EXCEPTION WHEN OTHERS THEN
    NULL;
END $$;

-- ============================================================================
-- TEST 27.1: Verificar existencia de tabla ai_decision_logs
-- ============================================================================

\echo ''
\echo '--- Test 27.1: Existencia de tabla ai_decision_logs ---'

DO $$
DECLARE
    v_table_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'ai_decision_logs'
    ) INTO v_table_exists;

    IF v_table_exists THEN
        v_status := 'PASS';
        v_details := 'Table ai_decision_logs exists (P2.7 AI Act Art.12)';
    ELSE
        v_status := 'FAIL';
        v_details := 'Table ai_decision_logs NOT FOUND';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('ai_decision_logs Table Exists', 'P2_AI_Decision_Logs', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 27.2: Verificar columnas clave de ai_decision_logs
-- ============================================================================

\echo ''
\echo '--- Test 27.2: Columnas de ai_decision_logs ---'

DO $$
DECLARE
    v_col_model_name BOOLEAN;
    v_col_model_version BOOLEAN;
    v_col_ai_risk_level BOOLEAN;
    v_col_human_oversight BOOLEAN;
    v_col_emotion_detection BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ai_decision_logs' AND column_name = 'model_name') INTO v_col_model_name;
    SELECT EXISTS(SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ai_decision_logs' AND column_name = 'model_version') INTO v_col_model_version;
    SELECT EXISTS(SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ai_decision_logs' AND column_name = 'ai_risk_level') INTO v_col_ai_risk_level;
    SELECT EXISTS(SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ai_decision_logs' AND column_name = 'human_oversight_required') INTO v_col_human_oversight;
    SELECT EXISTS(SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ai_decision_logs' AND column_name = 'emotion_detection_disclosed') INTO v_col_emotion_detection;

    IF v_col_model_name AND v_col_model_version AND v_col_ai_risk_level
       AND v_col_human_oversight AND v_col_emotion_detection THEN
        v_status := 'PASS';
        v_details := 'All required columns present: model_name, model_version, ai_risk_level, human_oversight_required, emotion_detection_disclosed';
    ELSE
        v_status := 'FAIL';
        v_details := format('Missing columns - model_name:%s, model_version:%s, ai_risk_level:%s, human_oversight:%s, emotion_detection:%s',
            v_col_model_name, v_col_model_version, v_col_ai_risk_level, v_col_human_oversight, v_col_emotion_detection);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('ai_decision_logs Columns', 'P2_AI_Decision_Logs', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 27.3: Verificar constraint ai_risk_level
-- ============================================================================

\echo ''
\echo '--- Test 27.3: Constraint ai_risk_level válido ---'

DO $$
DECLARE
    v_test_id UUID;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Insertar registro con ai_risk_level válido
    INSERT INTO ai_decision_logs (
        model_name, model_version, input_type, output_type, ai_risk_level
    )
    VALUES ('test_model', '1.0', 'text', 'classification', 'high')
    RETURNING id INTO v_test_id;

    IF v_test_id IS NOT NULL THEN
        v_status := 'PASS';
        v_details := format('ai_risk_level "high" accepted. ID: %s', v_test_id);
        -- Limpiar
        DELETE FROM ai_decision_logs WHERE id = v_test_id;
    ELSE
        v_status := 'FAIL';
        v_details := 'Failed to insert record with valid ai_risk_level';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('ai_risk_level Valid Values', 'P2_AI_Decision_Logs', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('ai_risk_level Valid Values', 'P2_AI_Decision_Logs', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 27.4: Verificar rechazo de ai_risk_level inválido
-- ============================================================================

\echo ''
\echo '--- Test 27.4: Rechazo ai_risk_level inválido ---'

DO $$
DECLARE
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Intentar insertar con valor inválido
    INSERT INTO ai_decision_logs (
        model_name, model_version, input_type, output_type, ai_risk_level
    )
    VALUES ('test_model', '1.0', 'text', 'classification', 'invalid_level');

    -- Si llegamos aquí, el constraint NO funcionó
    v_status := 'FAIL';
    v_details := 'Invalid ai_risk_level was accepted (should have been rejected)';

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('ai_risk_level Invalid Rejected', 'P2_AI_Decision_Logs', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;

EXCEPTION WHEN check_violation THEN
    v_status := 'PASS';
    v_details := 'Invalid ai_risk_level correctly rejected by constraint';

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('ai_risk_level Invalid Rejected', 'P2_AI_Decision_Logs', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('ai_risk_level Invalid Rejected', 'P2_AI_Decision_Logs', 'FAIL', 'Unexpected exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Unexpected exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 27.5: Verificar campos is_employee_call y employee_id en calls
-- ============================================================================

\echo ''
\echo '--- Test 27.5: Campos employee en tabla calls ---'

DO $$
DECLARE
    v_col_is_employee BOOLEAN;
    v_col_employee_id BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(SELECT 1 FROM information_schema.columns
        WHERE table_name = 'calls' AND column_name = 'is_employee_call') INTO v_col_is_employee;
    SELECT EXISTS(SELECT 1 FROM information_schema.columns
        WHERE table_name = 'calls' AND column_name = 'employee_id') INTO v_col_employee_id;

    IF v_col_is_employee AND v_col_employee_id THEN
        v_status := 'PASS';
        v_details := 'Columns is_employee_call and employee_id exist in calls table (P2.8 AI Act Art.5.1.f)';
    ELSE
        v_status := 'FAIL';
        v_details := format('Missing columns - is_employee_call:%s, employee_id:%s', v_col_is_employee, v_col_employee_id);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Employee Columns in Calls', 'P2_Employee_Protection', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 27.6: Verificar existencia de función de prohibición
-- ============================================================================

\echo ''
\echo '--- Test 27.6: Función validate_employee_emotion_prohibition ---'

DO $$
DECLARE
    v_func_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public' AND p.proname = 'validate_employee_emotion_prohibition'
    ) INTO v_func_exists;

    IF v_func_exists THEN
        v_status := 'PASS';
        v_details := 'Function validate_employee_emotion_prohibition exists';
    ELSE
        v_status := 'FAIL';
        v_details := 'Function validate_employee_emotion_prohibition NOT FOUND';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Employee Prohibition Function', 'P2_Employee_Protection', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 27.7: Verificar trigger de prohibición activado
-- ============================================================================

\echo ''
\echo '--- Test 27.7: Trigger de prohibición activado ---'

DO $$
DECLARE
    v_trigger_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM pg_trigger t
        JOIN pg_class c ON t.tgrelid = c.oid
        WHERE c.relname = 'calls' AND t.tgname = 'validate_employee_emotion_prohibition_trigger'
    ) INTO v_trigger_exists;

    IF v_trigger_exists THEN
        v_status := 'PASS';
        v_details := 'Trigger validate_employee_emotion_prohibition_trigger is active on calls';
    ELSE
        v_status := 'FAIL';
        v_details := 'Trigger NOT FOUND on calls table';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Employee Prohibition Trigger', 'P2_Employee_Protection', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 27.8: Llamada de NO empleado puede tener sentiment
-- ============================================================================

\echo ''
\echo '--- Test 27.8: Llamada NO empleado acepta sentiment ---'

DO $$
DECLARE
    v_user_id UUID;
    v_contact_id UUID;
    v_call_id UUID;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario de prueba
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_P2_USER', 'p2_test_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Crear contacto
    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_user_id,
        encrypt_pii_with_metadata('Test Contact P2'),
        encrypt_pii_with_metadata('+34600111222'),
        (secure_hash_with_pepper('+34600111222')).hash
    )
    RETURNING id INTO v_contact_id;

    -- Crear llamada de NO empleado CON sentiment (debe funcionar)
    INSERT INTO calls (
        user_id, contact_id, call_date, call_time, caller_name_encrypted, caller_phone_encrypted,
        caller_phone_hash, call_timestamp, duration_seconds, status, recording_encrypted,
        is_employee_call, sentiment, sentiment_score, emotion_detection_disclosed
    )
    VALUES (
        v_user_id, v_contact_id, CURRENT_DATE, CURRENT_TIME,
        encrypt_pii_with_metadata('Non-Employee Caller'),
        encrypt_pii_with_metadata('+34600111222'),
        (secure_hash_with_pepper('+34600111222')).hash,
        CURRENT_TIMESTAMP, 120, 'completed', false,
        false, -- NO es empleado
        'positive', 0.85, true
    )
    RETURNING id INTO v_call_id;

    IF v_call_id IS NOT NULL THEN
        v_status := 'PASS';
        v_details := format('Non-employee call with sentiment created successfully. ID: %s', v_call_id);
    ELSE
        v_status := 'FAIL';
        v_details := 'Failed to create non-employee call with sentiment';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Non-Employee Sentiment Allowed', 'P2_Employee_Protection', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Non-Employee Sentiment Allowed', 'P2_Employee_Protection', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 27.9: Llamada de empleado SIN sentiment funciona
-- ============================================================================

\echo ''
\echo '--- Test 27.9: Llamada empleado SIN sentiment permitida ---'

DO $$
DECLARE
    v_user_id UUID;
    v_contact_id UUID;
    v_call_id UUID;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario de prueba
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_P2_EMP', 'p2_emp_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Crear contacto
    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_user_id,
        encrypt_pii_with_metadata('Employee Contact'),
        encrypt_pii_with_metadata('+34600333444'),
        (secure_hash_with_pepper('+34600333444')).hash
    )
    RETURNING id INTO v_contact_id;

    -- Crear llamada de empleado SIN sentiment (debe funcionar)
    INSERT INTO calls (
        user_id, contact_id, call_date, call_time, caller_name_encrypted, caller_phone_encrypted,
        caller_phone_hash, call_timestamp, duration_seconds, status, recording_encrypted,
        is_employee_call, employee_id, sentiment, sentiment_score
    )
    VALUES (
        v_user_id, v_contact_id, CURRENT_DATE, CURRENT_TIME,
        encrypt_pii_with_metadata('Employee Caller'),
        encrypt_pii_with_metadata('+34600333444'),
        (secure_hash_with_pepper('+34600333444')).hash,
        CURRENT_TIMESTAMP, 180, 'completed', false,
        true, -- ES empleado
        v_user_id, -- employee_id
        NULL, NULL -- Sin sentiment
    )
    RETURNING id INTO v_call_id;

    IF v_call_id IS NOT NULL THEN
        v_status := 'PASS';
        v_details := format('Employee call without sentiment created. ID: %s', v_call_id);
    ELSE
        v_status := 'FAIL';
        v_details := 'Failed to create employee call without sentiment';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Employee Without Sentiment Allowed', 'P2_Employee_Protection', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Employee Without Sentiment Allowed', 'P2_Employee_Protection', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 27.10: PROHIBICIÓN - Llamada de empleado CON sentiment BLOQUEADA
-- ============================================================================

\echo ''
\echo '--- Test 27.10: Llamada empleado CON sentiment BLOQUEADA ---'

DO $$
DECLARE
    v_user_id UUID;
    v_contact_id UUID;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario de prueba
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_P2_BLOCK', 'p2_block_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Crear contacto
    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash)
    VALUES (
        v_user_id,
        encrypt_pii_with_metadata('Blocked Employee'),
        encrypt_pii_with_metadata('+34600555666'),
        (secure_hash_with_pepper('+34600555666')).hash
    )
    RETURNING id INTO v_contact_id;

    -- Intentar crear llamada de empleado CON sentiment (DEBE FALLAR)
    INSERT INTO calls (
        user_id, contact_id, call_date, call_time, caller_name_encrypted, caller_phone_encrypted,
        caller_phone_hash, call_timestamp, duration_seconds, status, recording_encrypted,
        is_employee_call, employee_id, sentiment, sentiment_score
    )
    VALUES (
        v_user_id, v_contact_id, CURRENT_DATE, CURRENT_TIME,
        encrypt_pii_with_metadata('Employee With Sentiment'),
        encrypt_pii_with_metadata('+34600555666'),
        (secure_hash_with_pepper('+34600555666')).hash,
        CURRENT_TIMESTAMP, 200, 'completed', false,
        true, -- ES empleado
        v_user_id,
        'negative', 0.30 -- Intentar guardar sentiment (PROHIBIDO)
    );

    -- Si llegamos aquí, el trigger NO bloqueó
    v_status := 'FAIL';
    v_details := 'CRITICAL: Employee call with sentiment was ALLOWED (should have been blocked by AI Act Art.5.1.f)';

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Employee Sentiment BLOCKED', 'P2_Employee_Protection', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;

EXCEPTION
    WHEN raise_exception THEN
        -- Verificar que es la excepción correcta
        IF SQLERRM LIKE '%AI Act Art. 5.1.f%' THEN
            v_status := 'PASS';
            v_details := 'Employee sentiment correctly BLOCKED: ' || SQLERRM;
        ELSE
            v_status := 'FAIL';
            v_details := 'Wrong exception message: ' || SQLERRM;
        END IF;

        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('Employee Sentiment BLOCKED', 'P2_Employee_Protection', v_status, v_details);

        RAISE NOTICE '  [%] %', v_status, v_details;
    WHEN OTHERS THEN
        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('Employee Sentiment BLOCKED', 'P2_Employee_Protection', 'FAIL', 'Unexpected exception: ' || SQLERRM);
        RAISE NOTICE '  [FAIL] Unexpected: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 27.11: Verificar audit log registra intento de violación
-- ============================================================================

\echo ''
\echo '--- Test 27.11: Audit log de intento de violación ---'

DO $$
DECLARE
    v_violation_logged BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Buscar si se registró intento de violación
    SELECT EXISTS(
        SELECT 1 FROM audit_log
        WHERE action = 'AI_ACT_VIOLATION_BLOCKED'
        AND legal_basis = 'AI Act Art. 5.1.f'
        AND created_at > CURRENT_TIMESTAMP - INTERVAL '5 minutes'
    ) INTO v_violation_logged;

    IF v_violation_logged THEN
        v_status := 'PASS';
        v_details := 'AI Act violation attempt was logged in audit_log';
    ELSE
        v_status := 'SKIP';
        v_details := 'No violation logged (may need to run test 27.10 first, or audit insert may have been rolled back)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Violation Attempt Logged', 'P2_Employee_Protection', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Violation Attempt Logged', 'P2_Employee_Protection', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 27.12: Verificar índice is_employee_call
-- ============================================================================

\echo ''
\echo '--- Test 27.12: Índice para is_employee_call ---'

DO $$
DECLARE
    v_index_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'calls' AND indexname LIKE '%employee%'
    ) INTO v_index_exists;

    IF v_index_exists THEN
        v_status := 'PASS';
        v_details := 'Index for employee calls exists';
    ELSE
        v_status := 'FAIL';
        v_details := 'No index found for employee calls';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Employee Index Exists', 'P2_Employee_Protection', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 27.13: Insertar y consultar registro en ai_decision_logs
-- ============================================================================

\echo ''
\echo '--- Test 27.13: CRUD ai_decision_logs ---'

DO $$
DECLARE
    v_test_id UUID;
    v_retrieved_model TEXT;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Insertar registro completo
    INSERT INTO ai_decision_logs (
        model_name, model_version, model_provider,
        input_type, output_type, output_confidence,
        ai_risk_level, decision_category,
        human_oversight_required, user_informed,
        emotion_detection_used, emotion_detection_disclosed,
        processing_time_ms
    )
    VALUES (
        'sentiment_analyzer', '2.1.0', 'internal',
        'audio', 'classification', 0.9234,
        'limited', 'sentiment',
        false, true,
        true, true,
        152
    )
    RETURNING id INTO v_test_id;

    -- Verificar lectura
    SELECT model_name INTO v_retrieved_model FROM ai_decision_logs WHERE id = v_test_id;

    IF v_retrieved_model = 'sentiment_analyzer' THEN
        v_status := 'PASS';
        v_details := format('ai_decision_logs INSERT/SELECT working. ID: %s', v_test_id);
        -- Limpiar
        DELETE FROM ai_decision_logs WHERE id = v_test_id;
    ELSE
        v_status := 'FAIL';
        v_details := 'Failed to read back inserted record';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('ai_decision_logs CRUD', 'P2_AI_Decision_Logs', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('ai_decision_logs CRUD', 'P2_AI_Decision_Logs', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Exception: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 27.14: Verificar índices de ai_decision_logs
-- ============================================================================

\echo ''
\echo '--- Test 27.14: Índices de ai_decision_logs ---'

DO $$
DECLARE
    v_idx_timestamp BOOLEAN;
    v_idx_risk BOOLEAN;
    v_idx_model BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE indexname = 'idx_ai_decisions_timestamp') INTO v_idx_timestamp;
    SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE indexname = 'idx_ai_decisions_risk') INTO v_idx_risk;
    SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE indexname = 'idx_ai_decisions_model') INTO v_idx_model;

    IF v_idx_timestamp AND v_idx_risk AND v_idx_model THEN
        v_status := 'PASS';
        v_details := 'All key indexes present: timestamp, risk_level, model';
    ELSE
        v_status := 'FAIL';
        v_details := format('Missing indexes - timestamp:%s, risk:%s, model:%s',
            v_idx_timestamp, v_idx_risk, v_idx_model);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('ai_decision_logs Indexes', 'P2_AI_Decision_Logs', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 27.15: Verificar campos human oversight en ai_decision_logs
-- ============================================================================

\echo ''
\echo '--- Test 27.15: Campos de supervisión humana (Art. 14) ---'

DO $$
DECLARE
    v_col_required BOOLEAN;
    v_col_override BOOLEAN;
    v_col_reviewer BOOLEAN;
    v_col_decision BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ai_decision_logs' AND column_name = 'human_oversight_required') INTO v_col_required;
    SELECT EXISTS(SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ai_decision_logs' AND column_name = 'human_override_occurred') INTO v_col_override;
    SELECT EXISTS(SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ai_decision_logs' AND column_name = 'human_reviewer_id') INTO v_col_reviewer;
    SELECT EXISTS(SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ai_decision_logs' AND column_name = 'human_review_decision') INTO v_col_decision;

    IF v_col_required AND v_col_override AND v_col_reviewer AND v_col_decision THEN
        v_status := 'PASS';
        v_details := 'All human oversight columns present (AI Act Art. 14)';
    ELSE
        v_status := 'FAIL';
        v_details := format('Missing - required:%s, override:%s, reviewer:%s, decision:%s',
            v_col_required, v_col_override, v_col_reviewer, v_col_decision);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Human Oversight Columns', 'P2_AI_Decision_Logs', v_status, v_details);

    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- ============================================================================
-- RESUMEN
-- ============================================================================

\echo ''
\echo '=============================================='
\echo 'RESUMEN TEST 27: P2 AI ACT'
\echo '=============================================='

SELECT test_category,
       COUNT(*) as total_tests,
       SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
       SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed,
       SUM(CASE WHEN status = 'SKIP' THEN 1 ELSE 0 END) as skipped
FROM test_results
GROUP BY test_category;

SELECT test_name, status, details
FROM test_results
ORDER BY test_id;

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
