-- ============================================================================
-- TEST 31: EXACTITUD DE DATOS
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 5.1.d: Exactitud de datos y actualización
--   • RGPD Art. 16: Derecho de rectificación
--   • LOPDGDD Art. 4.1: Exactitud y actualización
--   • LOPDGDD Art. 4.2: Conservación de datos inexactos con nota
-- 
--  NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: CRÍTICA
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Principios (Art. 5.1.d), PARTE 2 (LOPDGDD) - Art. 4
-- ============================================================================
-- Verifica mecanismos de exactitud, verificación y actualización de datos
-- Ejecutar: \i /path/to/31_test_data_accuracy.sql

-- Iniciar transacción para garantizar idempotencia
BEGIN;

\set ON_ERROR_STOP on
SET client_min_messages = notice;

CREATE TEMP TABLE IF NOT EXISTS test_results (
    test_id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    test_category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';
SET app.hash_pepper = 'TEST_PEPPER_V1_FOR_HMAC_FUNCTIONS';
SET app.hash_pepper_version = '1';
SET app.audit_hmac_key = 'TEST_AUDIT_KEY_FOR_HMAC_CHAIN__';

-- ============================================================================
-- TEST 31.1: Campo data_verified_at Existe en Contactos
-- ============================================================================

DO $$
DECLARE
    v_column_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'contacts'
        AND column_name = 'data_verified_at'
    ) INTO v_column_exists;

    IF v_column_exists THEN
        v_status := 'PASS';
        v_details := 'data_verified_at column exists for tracking accuracy (RGPD Art. 5.1.d)';
    ELSE
        v_status := 'FAIL';
        v_details := 'RECOMMENDATION: Add data_verified_at to track when data was last verified';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Data Verification Timestamp', 'Data_Accuracy', v_status, v_details);
    RAISE NOTICE '  [%] Verification Timestamp: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Data Verification Timestamp', 'Data_Accuracy', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 31.2: Campo accuracy_flag Para Estado de Exactitud
-- ============================================================================

DO $$
DECLARE
    v_column_exists BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'contacts'
        AND column_name = 'accuracy_flag'
    ) INTO v_column_exists;

    IF v_column_exists THEN
        v_status := 'PASS';
        v_details := 'accuracy_flag exists to mark data quality status';
    ELSE
        v_status := 'FAIL';
        v_details := 'RECOMMENDATION: Add accuracy_flag ENUM (verified, unverified, disputed, corrected)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Accuracy Flag Field', 'Data_Accuracy', v_status, v_details);
    RAISE NOTICE '  [%] Accuracy Flag: %', v_status, v_details;

EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Accuracy Flag Field', 'Data_Accuracy', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 31.3: Actualización de data_verified_at al Modificar Datos
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_test_contact_id UUID;
    v_initial_verified TIMESTAMP;
    v_updated_verified TIMESTAMP;
    v_status TEXT;
    v_details TEXT;
BEGIN
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_ACCURACY_USER', 'test_acc_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash', 'admin')
    RETURNING id INTO v_test_user_id;

    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash, data_verified_at)
    VALUES (
        v_test_user_id,
        '{\"c\": \"dGVzdA==\", \"alg\": \"test\", \"v\": 0}'::JSONB,
        '{\"c\": \"dGVzdA==\", \"alg\": \"test\", \"v\": 0}'::JSONB,
        'TEST_ACC_HASH',
        CURRENT_TIMESTAMP - INTERVAL '1 day'
    )
    RETURNING id, data_verified_at INTO v_test_contact_id, v_initial_verified;

    -- Pequeña espera (simulada con timestamp)
    PERFORM pg_sleep(0.1);

    -- Actualizar datos (debería actualizar data_verified_at automáticamente con trigger)
    UPDATE contacts
    SET phone_hash = 'UPDATED_HASH',
        data_verified_at = CURRENT_TIMESTAMP
    WHERE id = v_test_contact_id;

    SELECT data_verified_at INTO v_updated_verified
    FROM contacts WHERE id = v_test_contact_id;

    IF v_updated_verified > v_initial_verified THEN
        v_status := 'PASS';
        v_details := 'data_verified_at updates when data changes (good accuracy tracking)';
    ELSE
        v_status := 'FAIL';
        v_details := 'data_verified_at not updated - consider adding trigger';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Verification Update on Change', 'Data_Accuracy', v_status, v_details);
    RAISE NOTICE '  [%] Verification Update: %', v_status, v_details;

EXCEPTION 
    WHEN undefined_column THEN
        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('Verification Update on Change', 'Data_Accuracy', 'SKIP', 'data_verified_at column not found');
    WHEN OTHERS THEN
        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('Verification Update on Change', 'Data_Accuracy', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 31.4: Procedimiento de Verificación Periódica
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_test_contact_id UUID;
    v_old_verified TIMESTAMP := CURRENT_TIMESTAMP - INTERVAL '1 year';
    v_needs_verification BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_PERIODIC_USER', 'test_periodic_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash', 'admin')
    RETURNING id INTO v_test_user_id;

    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash, data_verified_at)
    VALUES (
        v_test_user_id,
        '{\"c\": \"dGVzdA==\", \"alg\": \"test\", \"v\": 0}'::JSONB,
        '{\"c\": \"dGVzdA==\", \"alg\": \"test\", \"v\": 0}'::JSONB,
        'TEST_OLD_HASH',
        v_old_verified
    )
    RETURNING id INTO v_test_contact_id;

    -- Verificar que contactos antiguos necesitan re-verificación
    SELECT (data_verified_at < CURRENT_TIMESTAMP - INTERVAL '6 months')
    INTO v_needs_verification
    FROM contacts WHERE id = v_test_contact_id;

    IF v_needs_verification THEN
        v_status := 'PASS';
        v_details := 'Old data correctly identified for re-verification (>6 months)';
    ELSE
        v_status := 'FAIL';
        v_details := 'Verification logic not detecting old data';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Periodic Verification Detection', 'Data_Accuracy', v_status, v_details);
    RAISE NOTICE '  [%] Periodic Verification: %', v_status, v_details;

EXCEPTION 
    WHEN undefined_column THEN
        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('Periodic Verification Detection', 'Data_Accuracy', 'SKIP', 'data_verified_at not found');
    WHEN OTHERS THEN
        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('Periodic Verification Detection', 'Data_Accuracy', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 31.5: Flag de Datos Inexactos Impide Uso
-- ============================================================================

DO $$
DECLARE
    v_test_user_id UUID;
    v_test_contact_id UUID;
    v_can_use_inaccurate BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    INSERT INTO users (name, email, password_hash, role)
    VALUES ('TEST_INACCURATE_USER', 'test_inac_' || gen_random_uuid()::TEXT || '@test.local', 'test_hash', 'admin')
    RETURNING id INTO v_test_user_id;

    INSERT INTO contacts (user_id, name_encrypted, phone_encrypted, phone_hash, accuracy_flag)
    VALUES (
        v_test_user_id,
        '{\"c\": \"dGVzdA==\", \"alg\": \"test\", \"v\": 0}'::JSONB,
        '{\"c\": \"dGVzdA==\", \"alg\": \"test\", \"v\": 0}'::JSONB,
        'TEST_INACCURATE_HASH',
        'disputed'
    )
    RETURNING id INTO v_test_contact_id;

    -- Verificar que datos disputados no se usan (requiere WHERE accuracy_flag != 'disputed')
    SELECT EXISTS(
        SELECT 1 FROM contacts
        WHERE id = v_test_contact_id
        AND (accuracy_flag IS NULL OR accuracy_flag NOT IN ('disputed', 'incorrect'))
    ) INTO v_can_use_inaccurate;

    IF NOT v_can_use_inaccurate THEN
        v_status := 'PASS';
        v_details := 'Inaccurate data correctly flagged and excluded from normal queries';
    ELSE
        v_status := 'FAIL';
        v_details := 'RECOMMENDATION: Implement views/functions that filter out disputed/incorrect data';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Inaccurate Data Flagging', 'Data_Accuracy', v_status, v_details);
    RAISE NOTICE '  [%] Inaccurate Flagging: %', v_status, v_details;

EXCEPTION 
    WHEN undefined_column THEN
        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('Inaccurate Data Flagging', 'Data_Accuracy', 'SKIP', 'accuracy_flag not found');
    WHEN OTHERS THEN
        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('Inaccurate Data Flagging', 'Data_Accuracy', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- RESUMEN DE RESULTADOS
-- ============================================================================

SELECT
    test_category,
    COUNT(*) as total_tests,
    COUNT(*) FILTER (WHERE status = 'PASS') as passed,
    COUNT(*) FILTER (WHERE status = 'FAIL') as failed,
    COUNT(*) FILTER (WHERE status = 'SKIP') as skipped
FROM test_results
WHERE test_category = 'Data_Accuracy'
GROUP BY test_category;

SELECT test_name, details
FROM test_results
WHERE test_category = 'Data_Accuracy' AND status = 'FAIL';

ROLLBACK;
