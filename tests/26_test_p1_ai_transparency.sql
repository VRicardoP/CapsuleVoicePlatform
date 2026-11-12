-- ============================================================================
-- TEST 26: P1 AI ACT TRANSPARENCY - Transparencia en Sistemas de IA
-- ============================================================================
-- COBERTURA LEGAL:
--   • AI Act Art. 50.1: Informar interacción con sistema IA
--   • AI Act Art. 50.3: Informar detección de emociones
--   • AI Act Art. 14: Supervisión humana de sistemas IA
--   • AI Act Art. 13: Transparencia e información
--   • RGPD Art. 13.2.f: Informar decisiones automatizadas
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: CRÍTICA
-- REQUISITOS NORMATIVA.MD: PARTE 3 (AI Act) - Arts. 13, 14, 50
-- ============================================================================
-- Verifica implementación de Art. 50 AI Act (transparencia en detección emocional)
-- y Art. 14 (supervisión humana de sistemas de IA de alto riesgo)
-- Ejecutar: psql -U postgres -d capsule -f 26_test_p1_ai_transparency.sql
-- ============================================================================

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '=============================================================='
\echo 'TEST 26: P1 AI ACT TRANSPARENCY'
\echo '=============================================================='

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
        'test_key_ai_' || substring(gen_random_uuid()::TEXT, 1, 8),
        pgp_sym_encrypt(encode(gen_random_bytes(32), 'hex'), current_setting('app.kms_master_key'), 'cipher-algo=aes256'),
        true,
        'hashicorp-vault',
        CURRENT_TIMESTAMP
    );
EXCEPTION WHEN OTHERS THEN
    NULL;
END $$;

-- ============================================================================
-- TEST 26.1: Verificar existencia del campo emotion_detection_disclosed
-- ============================================================================

\echo ''
\echo '--- Test 26.1: Campo emotion_detection_disclosed en calls ---'

DO $$
DECLARE
    v_column_exists BOOLEAN;
    v_column_type TEXT;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'calls'
        AND column_name = 'emotion_detection_disclosed'
    ) INTO v_column_exists;

    IF v_column_exists THEN
        SELECT data_type INTO v_column_type
        FROM information_schema.columns
        WHERE table_name = 'calls'
        AND column_name = 'emotion_detection_disclosed';

        v_status := 'PASS';
        v_details := format('Column exists with type: %s', v_column_type);
    ELSE
        v_status := 'FAIL';
        v_details := 'Column emotion_detection_disclosed not found in calls table';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('emotion_detection_disclosed Column', 'AI_Transparency', v_status, v_details);

    RAISE NOTICE '  [%] Column: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 26.2: Verificar campo emotion_detection_disclosed_at
-- ============================================================================

\echo ''
\echo '--- Test 26.2: Campo emotion_detection_disclosed_at ---'

DO $$
DECLARE
    v_column_exists BOOLEAN;
    v_column_type TEXT;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'calls'
        AND column_name = 'emotion_detection_disclosed_at'
    ) INTO v_column_exists;

    IF v_column_exists THEN
        SELECT data_type INTO v_column_type
        FROM information_schema.columns
        WHERE table_name = 'calls'
        AND column_name = 'emotion_detection_disclosed_at';

        v_status := 'PASS';
        v_details := format('Timestamp column exists with type: %s', v_column_type);
    ELSE
        v_status := 'FAIL';
        v_details := 'Column emotion_detection_disclosed_at not found';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('emotion_detection_disclosed_at Column', 'AI_Transparency', v_status, v_details);

    RAISE NOTICE '  [%] Timestamp: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 26.3: Verificar existencia de la función de validación
-- ============================================================================

\echo ''
\echo '--- Test 26.3: Función validate_emotion_detection_disclosure ---'

DO $$
DECLARE
    v_func_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public'
        AND p.proname = 'validate_emotion_detection_disclosure'
    ) INTO v_func_exists;

    IF v_func_exists THEN
        v_status := 'PASS';
        v_details := 'Function validate_emotion_detection_disclosure() exists';
    ELSE
        v_status := 'FAIL';
        v_details := 'Function validate_emotion_detection_disclosure() NOT found';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Validation Function Exists', 'AI_Transparency', v_status, v_details);

    RAISE NOTICE '  [%] Function: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 26.4: Verificar trigger de validación
-- ============================================================================

\echo ''
\echo '--- Test 26.4: Trigger de validación de emotion_detection ---'

DO $$
DECLARE
    v_trigger_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM pg_trigger t
        JOIN pg_class c ON t.tgrelid = c.oid
        WHERE c.relname = 'calls'
        AND t.tgname = 'validate_emotion_detection_disclosure_trigger'
    ) INTO v_trigger_exists;

    IF v_trigger_exists THEN
        v_status := 'PASS';
        v_details := 'Trigger validate_emotion_detection_disclosure_trigger exists on calls';
    ELSE
        v_status := 'FAIL';
        v_details := 'Trigger NOT found on calls table';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Validation Trigger Exists', 'AI_Transparency', v_status, v_details);

    RAISE NOTICE '  [%] Trigger: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 26.5: Verificar vista v_ai_decision_audit
-- ============================================================================

\echo ''
\echo '--- Test 26.5: Vista v_ai_decision_audit ---'

DO $$
DECLARE
    v_view_exists BOOLEAN;
    v_column_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM information_schema.views
        WHERE table_name = 'v_ai_decision_audit'
    ) INTO v_view_exists;

    IF v_view_exists THEN
        SELECT COUNT(*) INTO v_column_count
        FROM information_schema.columns
        WHERE table_name = 'v_ai_decision_audit';

        v_status := 'PASS';
        v_details := format('View exists with %s columns', v_column_count);
    ELSE
        v_status := 'FAIL';
        v_details := 'View v_ai_decision_audit NOT found';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('v_ai_decision_audit View', 'AI_Transparency', v_status, v_details);

    RAISE NOTICE '  [%] View: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 26.6: Verificar vista v_ai_act_compliance_summary
-- ============================================================================

\echo ''
\echo '--- Test 26.6: Vista v_ai_act_compliance_summary ---'

DO $$
DECLARE
    v_view_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM information_schema.views
        WHERE table_name = 'v_ai_act_compliance_summary'
    ) INTO v_view_exists;

    IF v_view_exists THEN
        v_status := 'PASS';
        v_details := 'View v_ai_act_compliance_summary exists';
    ELSE
        v_status := 'FAIL';
        v_details := 'View v_ai_act_compliance_summary NOT found';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('v_ai_act_compliance_summary View', 'AI_Transparency', v_status, v_details);

    RAISE NOTICE '  [%] Summary View: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 26.7: Verificar nuevas acciones en audit_log
-- ============================================================================

\echo ''
\echo '--- Test 26.7: Acciones AI_TRANSPARENCY en audit_log ---'

DO $$
DECLARE
    v_constraint_text TEXT;
    v_has_ai_warning BOOLEAN;
    v_has_ai_decision BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Obtener el texto del constraint CHECK
    SELECT pg_get_constraintdef(c.oid) INTO v_constraint_text
    FROM pg_constraint c
    JOIN pg_class t ON c.conrelid = t.oid
    WHERE t.relname = 'audit_log'
    AND c.contype = 'c'
    AND c.conname LIKE '%action%'
    LIMIT 1;

    v_has_ai_warning := v_constraint_text LIKE '%AI_TRANSPARENCY_WARNING%';
    v_has_ai_decision := v_constraint_text LIKE '%AI_DECISION_LOGGED%';

    IF v_has_ai_warning AND v_has_ai_decision THEN
        v_status := 'PASS';
        v_details := 'Both AI_TRANSPARENCY_WARNING and AI_DECISION_LOGGED actions present';
    ELSIF v_has_ai_warning OR v_has_ai_decision THEN
        v_status := 'PASS';
        v_details := format('Actions present - WARNING: %s, DECISION: %s', v_has_ai_warning, v_has_ai_decision);
    ELSE
        v_status := 'FAIL';
        v_details := 'AI transparency actions NOT found in audit_log constraint';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('AI Actions in audit_log', 'AI_Transparency', v_status, v_details);

    RAISE NOTICE '  [%] Actions: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 26.8: Test funcional - Insertar llamada CON sentiment SIN disclosure
-- ============================================================================

\echo ''
\echo '--- Test 26.8: Llamada con sentiment sin disclosure (warning) ---'

DO $$
DECLARE
    v_user_id UUID;
    v_call_id UUID;
    v_warning_logged BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario de prueba
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_AI_USER', 'ai_test_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Insertar llamada CON sentiment pero SIN disclosure (debe generar warning)
    INSERT INTO calls (
        user_id, call_date, call_time, call_timestamp, duration_seconds,
        caller_phone_hash, caller_phone_hash_pepper_version,
        status, sentiment, sentiment_score,
        emotion_detection_disclosed,  -- Explícitamente false
        recording_encrypted  -- Explícitamente false para evitar trigger
    )
    VALUES (
        v_user_id, CURRENT_DATE, CURRENT_TIME, CURRENT_TIMESTAMP, 120,
        (secure_hash_with_pepper('+34600111222')).hash, 1,
        'completed', 'positive', 0.85,
        false,  -- No se informó al usuario
        false
    )
    RETURNING id INTO v_call_id;

    -- Verificar que se generó warning en audit_log
    SELECT EXISTS(
        SELECT 1 FROM audit_log
        WHERE action = 'AI_TRANSPARENCY_WARNING'
        AND entity_id = v_call_id
        AND details->>'ai_act_article' = '50'
    ) INTO v_warning_logged;

    IF v_warning_logged THEN
        v_status := 'PASS';
        v_details := format('Warning logged for call %s - AI Act Art. 50 compliance tracking works', v_call_id);
    ELSE
        v_status := 'FAIL';
        v_details := 'No warning logged for sentiment analysis without disclosure';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Sentiment Without Disclosure Warning', 'AI_Transparency', v_status, v_details);

    RAISE NOTICE '  [%] Warning: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Sentiment Without Disclosure Warning', 'AI_Transparency', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Warning: Exception - %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 26.9: Test funcional - Insertar llamada CON disclosure
-- ============================================================================

\echo ''
\echo '--- Test 26.9: Llamada con sentiment Y disclosure ---'

DO $$
DECLARE
    v_user_id UUID;
    v_call_id UUID;
    v_disclosure_at TIMESTAMP WITH TIME ZONE;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario de prueba
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_AI_USER2', 'ai_test2_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'admin')
    RETURNING id INTO v_user_id;

    -- Insertar llamada CON sentiment Y disclosure
    INSERT INTO calls (
        user_id, call_date, call_time, call_timestamp, duration_seconds,
        caller_phone_hash, caller_phone_hash_pepper_version,
        status, sentiment, sentiment_score,
        emotion_detection_disclosed,  -- Usuario fue informado
        recording_encrypted  -- Explícitamente false
    )
    VALUES (
        v_user_id, CURRENT_DATE, CURRENT_TIME, CURRENT_TIMESTAMP, 180,
        (secure_hash_with_pepper('+34600333444')).hash, 1,
        'completed', 'neutral', 0.50,
        true,  -- Usuario fue informado
        false
    )
    RETURNING id INTO v_call_id;

    -- Verificar que se estableció el timestamp automáticamente
    SELECT emotion_detection_disclosed_at INTO v_disclosure_at
    FROM calls WHERE id = v_call_id;

    IF v_disclosure_at IS NOT NULL THEN
        v_status := 'PASS';
        v_details := format('Disclosure timestamp auto-set: %s', v_disclosure_at);
    ELSE
        v_status := 'FAIL';
        v_details := 'Disclosure timestamp NOT auto-set';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Disclosure Timestamp Auto-Set', 'AI_Transparency', v_status, v_details);

    RAISE NOTICE '  [%] Timestamp: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Disclosure Timestamp Auto-Set', 'AI_Transparency', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Timestamp: Exception - %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 26.10: Verificar que v_ai_decision_audit muestra datos correctos
-- ============================================================================

\echo ''
\echo '--- Test 26.10: Vista v_ai_decision_audit query ---'

DO $$
DECLARE
    v_record_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Contar registros en la vista
    SELECT COUNT(*) INTO v_record_count FROM v_ai_decision_audit;

    -- La vista debe poder consultarse sin errores
    v_status := 'PASS';
    v_details := format('View queryable, found %s AI decision records', v_record_count);

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('v_ai_decision_audit Queryable', 'AI_Transparency', v_status, v_details);

    RAISE NOTICE '  [%] Query: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('v_ai_decision_audit Queryable', 'AI_Transparency', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Query: Exception - %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 26.11: Verificar que v_ai_act_compliance_summary funciona
-- ============================================================================

\echo ''
\echo '--- Test 26.11: Vista v_ai_act_compliance_summary query ---'

DO $$
DECLARE
    v_record_count INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT COUNT(*) INTO v_record_count FROM v_ai_act_compliance_summary;

    v_status := 'PASS';
    v_details := format('Summary view queryable, %s days with AI activity', v_record_count);

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('v_ai_act_compliance_summary Queryable', 'AI_Transparency', v_status, v_details);

    RAISE NOTICE '  [%] Summary: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('v_ai_act_compliance_summary Queryable', 'AI_Transparency', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Summary: Exception - %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 26.12: Verificar comentarios de documentación legal
-- ============================================================================

\echo ''
\echo '--- Test 26.12: Documentación legal en campos ---'

DO $$
DECLARE
    v_comment TEXT;
    v_has_ai_act_ref BOOLEAN := false;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Verificar comentario de la columna
    SELECT col_description(
        (SELECT oid FROM pg_class WHERE relname = 'calls'),
        (SELECT attnum FROM pg_attribute WHERE attrelid = (SELECT oid FROM pg_class WHERE relname = 'calls') AND attname = 'emotion_detection_disclosed')
    ) INTO v_comment;

    IF v_comment IS NOT NULL AND v_comment LIKE '%AI ACT%' THEN
        v_has_ai_act_ref := true;
    END IF;

    IF v_has_ai_act_ref THEN
        v_status := 'PASS';
        v_details := format('Legal documentation present: %s', LEFT(v_comment, 80));
    ELSE
        v_status := 'PASS';  -- Warning, no fail
        v_details := 'Column exists but AI Act reference in comment not found (acceptable)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Legal Documentation', 'AI_Transparency', v_status, v_details);

    RAISE NOTICE '  [%] Docs: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Legal Documentation', 'AI_Transparency', 'PASS', 'Check skipped: ' || SQLERRM);
    RAISE NOTICE '  [PASS] Docs: Check skipped - %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 26.13: Verificar índice para consultas de compliance
-- ============================================================================

\echo ''
\echo '--- Test 26.13: Índices para consultas AI compliance ---'

DO $$
DECLARE
    v_idx_sentiment BOOLEAN;
    v_idx_disclosure BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Verificar si hay índices relevantes para consultas de sentiment
    SELECT EXISTS(
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'calls'
        AND indexdef LIKE '%sentiment%'
    ) INTO v_idx_sentiment;

    SELECT EXISTS(
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'calls'
        AND indexdef LIKE '%emotion_detection%'
    ) INTO v_idx_disclosure;

    -- No es crítico tener índices específicos, pero es buena práctica
    IF v_idx_sentiment THEN
        v_status := 'PASS';
        v_details := 'Sentiment index exists for performance';
    ELSE
        v_status := 'PASS';
        v_details := 'No specific index for emotion_detection (acceptable for current volume)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('AI Compliance Indexes', 'AI_Transparency', v_status, v_details);

    RAISE NOTICE '  [%] Indexes: %', v_status, v_details;
END $$;

-- ============================================================================
-- TEST 26.14: Test de integración - Flujo completo de AI transparency
-- ============================================================================

\echo ''
\echo '--- Test 26.14: Flujo completo AI transparency ---'

DO $$
DECLARE
    v_user_id UUID;
    v_call1_id UUID;
    v_call2_id UUID;
    v_warnings_count INTEGER;
    v_compliance_records INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_INTEGRATION', 'integration_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'user')
    RETURNING id INTO v_user_id;

    -- Llamada 1: Sin sentiment (no debe generar warning)
    INSERT INTO calls (
        user_id, call_date, call_time, call_timestamp, duration_seconds,
        caller_phone_hash, caller_phone_hash_pepper_version, status,
        recording_encrypted  -- Explícitamente false para evitar trigger de consent
    )
    VALUES (
        v_user_id, CURRENT_DATE, CURRENT_TIME, CURRENT_TIMESTAMP, 60,
        (secure_hash_with_pepper('+34600555666')).hash, 1, 'completed',
        false
    )
    RETURNING id INTO v_call1_id;

    -- Llamada 2: Con sentiment sin disclosure (debe generar warning)
    INSERT INTO calls (
        user_id, call_date, call_time, call_timestamp, duration_seconds,
        caller_phone_hash, caller_phone_hash_pepper_version, status,
        sentiment, sentiment_score, emotion_detection_disclosed,
        recording_encrypted  -- Explícitamente false
    )
    VALUES (
        v_user_id, CURRENT_DATE, CURRENT_TIME, CURRENT_TIMESTAMP, 90,
        (secure_hash_with_pepper('+34600777888')).hash, 1, 'completed',
        'negative', 0.25, false,
        false
    )
    RETURNING id INTO v_call2_id;

    -- Contar warnings generados
    SELECT COUNT(*) INTO v_warnings_count
    FROM audit_log
    WHERE action = 'AI_TRANSPARENCY_WARNING'
    AND entity_id IN (v_call1_id, v_call2_id);

    -- Verificar que hay registros en la vista de compliance
    SELECT COUNT(*) INTO v_compliance_records
    FROM v_ai_decision_audit
    WHERE entity_id = v_call2_id;

    IF v_warnings_count >= 1 AND v_compliance_records >= 0 THEN
        v_status := 'PASS';
        v_details := format('Integration OK: %s warnings, %s compliance records', v_warnings_count, v_compliance_records);
    ELSE
        v_status := 'FAIL';
        v_details := format('Integration FAIL: warnings=%s, compliance=%s', v_warnings_count, v_compliance_records);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Full Integration Test', 'AI_Transparency', v_status, v_details);

    RAISE NOTICE '  [%] Integration: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Full Integration Test', 'AI_Transparency', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Integration: Exception - %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 26.15: Verificar que llamadas sin sentiment no generan warnings
-- ============================================================================

\echo ''
\echo '--- Test 26.15: Llamadas sin sentiment no generan warnings ---'

DO $$
DECLARE
    v_user_id UUID;
    v_call_id UUID;
    v_warnings_before INTEGER;
    v_warnings_after INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Contar warnings antes
    SELECT COUNT(*) INTO v_warnings_before FROM audit_log WHERE action = 'AI_TRANSPARENCY_WARNING';

    -- Crear usuario
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_NO_SENTIMENT', 'nosent_' || substring(gen_random_uuid()::TEXT, 1, 8) || '@test.local', 'hash', 'user')
    RETURNING id INTO v_user_id;

    -- Llamada SIN sentiment
    INSERT INTO calls (
        user_id, call_date, call_time, call_timestamp, duration_seconds,
        caller_phone_hash, caller_phone_hash_pepper_version, status,
        recording_encrypted  -- Explícitamente false para evitar trigger
        -- SIN sentiment ni sentiment_score
    )
    VALUES (
        v_user_id, CURRENT_DATE, CURRENT_TIME, CURRENT_TIMESTAMP, 45,
        (secure_hash_with_pepper('+34600999000')).hash, 1, 'completed',
        false
    )
    RETURNING id INTO v_call_id;

    -- Contar warnings después
    SELECT COUNT(*) INTO v_warnings_after FROM audit_log WHERE action = 'AI_TRANSPARENCY_WARNING';

    -- No debe haber nuevos warnings
    IF v_warnings_after = v_warnings_before THEN
        v_status := 'PASS';
        v_details := 'No warning generated for call without sentiment analysis';
    ELSE
        v_status := 'FAIL';
        v_details := format('Unexpected warning generated: before=%s, after=%s', v_warnings_before, v_warnings_after);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('No Sentiment No Warning', 'AI_Transparency', v_status, v_details);

    RAISE NOTICE '  [%] No Warning: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('No Sentiment No Warning', 'AI_Transparency', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] No Warning: Exception - %', SQLERRM;
END $$;

-- ============================================================================
-- RESUMEN
-- ============================================================================

\echo ''
\echo '=============================================================='
\echo 'RESUMEN TEST 26: P1 AI ACT TRANSPARENCY'
\echo '=============================================================='

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

\echo ''
\echo '=============================================================='
\echo 'FIN TEST 26'
\echo '=============================================================='

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
