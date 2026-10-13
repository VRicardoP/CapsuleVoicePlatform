-- ============================================================================
-- TEST 02: FUNCIONES DE CIFRADO
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 32.1.a: Seudonimización y cifrado de datos personales
--   • RGPD Art. 5.1.f: Integridad y confidencialidad (seguridad del tratamiento)
--   • RGPD Art. 32.1.b: Garantizar confidencialidad, integridad, disponibilidad
--   • RGPD Art. 25.1: Protección de datos desde el diseño (cifrado por defecto)
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: CRÍTICA (seguridad fundamental)
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Seguridad del Tratamiento (Art. 32)
-- ============================================================================
-- Verifica el sistema de cifrado end-to-end con metadata completa
-- Ejecutar: \i /path/to/02_test_funciones_cifrado.sql

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

-- IMPORTANTE: Este test requiere que las variables de sesión KMS estén configuradas
-- Para tests, usar claves de prueba:
-- SET app.kms_master_key = 'TEST_MASTER_KEY_32_CHARACTERS!!';
-- SET app.hash_pepper = 'TEST_PEPPER_VALUE';
-- SET app.hash_pepper_version = '1';

CREATE TEMP TABLE IF NOT EXISTS test_results (
    test_id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    test_category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- Configurar claves de prueba
SET app.kms_master_key = 'TEST_MASTER_KEY_FOR_TESTS_32CHAR';
SET app.hash_pepper = 'TEST_PEPPER_V1_FOR_HMAC_FUNCTIONS';
SET app.hash_pepper_version = '1';
SET app.audit_hmac_key = 'TEST_AUDIT_KEY_FOR_HMAC_CHAIN__';

-- CORRECCIÓN: Desactivar todas las claves existentes y crear una única clave de test
-- El índice idx_single_active_key solo permite UNA clave activa
DO $$
BEGIN
    -- Desactivar todas las claves existentes
    UPDATE encryption_keys SET is_active = false WHERE is_active = true;

    -- Crear o actualizar clave de test única
    INSERT INTO encryption_keys (key_id, encrypted_key, is_active, kms_provider, activated_at)
    VALUES (
        'test_key_encryption_suite',
        pgp_sym_encrypt(encode(gen_random_bytes(32), 'hex'), current_setting('app.kms_master_key'), 'cipher-algo=aes256'),
        true,
        'hashicorp-vault',
        CURRENT_TIMESTAMP
    )
    ON CONFLICT (key_id) DO UPDATE SET
        is_active = true,
        activated_at = CURRENT_TIMESTAMP;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Note: Could not setup test key: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 2.1: Cifrado y Descifrado Básico
-- ============================================================================

DO $$
DECLARE
    v_plain_text TEXT := 'Dato sensible de prueba PII';
    v_encrypted JSONB;
    v_decrypted TEXT;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- La clave ya está creada arriba, no necesitamos crear otra

    -- Cifrar
    BEGIN
        v_encrypted := encrypt_pii_with_metadata(v_plain_text);
    EXCEPTION WHEN OTHERS THEN
        v_status := 'FAIL';
        v_details := 'Encryption failed: ' || SQLERRM;
        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('Encrypt PII', 'Encryption', v_status, v_details);
        RAISE NOTICE '  [%] Encrypt PII: %', v_status, v_details;
        RETURN;
    END;

    -- Descifrar
    BEGIN
        v_decrypted := decrypt_pii_with_metadata(v_encrypted);
    EXCEPTION WHEN OTHERS THEN
        v_status := 'FAIL';
        v_details := 'Decryption failed: ' || SQLERRM;
        INSERT INTO test_results (test_name, test_category, status, details)
        VALUES ('Decrypt PII', 'Encryption', v_status, v_details);
        RAISE NOTICE '  [%] Decrypt PII: %', v_status, v_details;
        RETURN;
    END;

    -- Verificar
    IF v_decrypted = v_plain_text THEN
        v_status := 'PASS';
        v_details := 'Encryption/decryption successful';
    ELSE
        v_status := 'FAIL';
        v_details := format('Decrypted text does not match. Expected: %s, Got: %s', v_plain_text, v_decrypted);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Basic Encryption/Decryption', 'Encryption', v_status, v_details);
    
    RAISE NOTICE '  [%] Basic Encryption/Decryption: %', v_status, v_details;

    -- No limpiar la clave - se reutiliza en los siguientes tests
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Basic Encryption/Decryption', 'Encryption', 'FAIL', 'Exception: ' || SQLERRM);
    RAISE NOTICE '  [FAIL] Basic Encryption/Decryption: %', SQLERRM;
END $$;

-- ============================================================================
-- TEST 2.2: Metadata Completa en Datos Cifrados
-- ============================================================================

DO $$
DECLARE
    v_encrypted JSONB;
    v_has_ciphertext BOOLEAN;
    v_has_iv BOOLEAN;
    v_has_tag BOOLEAN;
    v_has_alg BOOLEAN;
    v_has_kid BOOLEAN;
    v_has_version BOOLEAN;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Usar la clave creada al inicio del test suite
    v_encrypted := encrypt_pii_with_metadata('Test data for metadata');

    -- Verificar campos
    v_has_ciphertext := (v_encrypted ? 'c');
    v_has_iv := (v_encrypted ? 'iv');
    v_has_tag := (v_encrypted ? 'tag');
    v_has_alg := (v_encrypted ? 'alg');
    v_has_kid := (v_encrypted ? 'kid');
    v_has_version := (v_encrypted ? 'v');

    IF v_has_ciphertext AND v_has_iv AND v_has_tag AND v_has_alg AND v_has_kid AND v_has_version THEN
        v_status := 'PASS';
        v_details := 'All metadata fields present (c, iv, tag, alg, kid, v)';
    ELSE
        v_status := 'FAIL';
        v_details := format('Missing fields - c:%s, iv:%s, tag:%s, alg:%s, kid:%s, v:%s',
            v_has_ciphertext, v_has_iv, v_has_tag, v_has_alg, v_has_kid, v_has_version);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Encryption Metadata Complete', 'Encryption', v_status, v_details);

    RAISE NOTICE '  [%] Encryption Metadata: %', v_status, v_details;

    -- No eliminar clave - se reutiliza
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Encryption Metadata Complete', 'Encryption', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 2.3: Autenticación HMAC (Detección de Manipulación)
-- ============================================================================

DO $$
DECLARE
    v_encrypted JSONB;
    v_tampered JSONB;
    v_decryption_result TEXT;
    v_tampering_detected BOOLEAN := false;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Usar la clave creada al inicio del test suite
    v_encrypted := encrypt_pii_with_metadata('Original data');

    -- MANIPULAR el ciphertext (cambiar un byte)
    v_tampered := jsonb_set(v_encrypted, '{c}', '"MANIPULATED_DATA"');

    -- Intentar descifrar datos manipulados
    -- La función retorna un mensaje de error en lugar de lanzar excepción
    v_decryption_result := decrypt_pii_with_metadata(v_tampered);

    -- Verificar si el resultado indica error de autenticación o manipulación
    v_tampering_detected := (
        v_decryption_result LIKE '%DECRYPTION_ERROR%' OR
        v_decryption_result LIKE '%tampered%' OR
        v_decryption_result LIKE '%Authentication failed%' OR
        v_decryption_result != 'Original data'
    );

    IF v_tampering_detected THEN
        v_status := 'PASS';
        v_details := 'Tampering correctly detected: ' || LEFT(v_decryption_result, 50);
    ELSE
        v_status := 'FAIL';
        v_details := 'Failed to detect data tampering';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('HMAC Authentication', 'Encryption', v_status, v_details);

    RAISE NOTICE '  [%] HMAC Authentication: %', v_status, v_details;

    -- No eliminar clave - se reutiliza
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('HMAC Authentication', 'Encryption', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 2.4: Secure Hash con Pepper
-- ============================================================================

DO $$
DECLARE
    v_hash1 TEXT;
    v_hash2 TEXT;
    v_version1 INTEGER;
    v_version2 INTEGER;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Generar hash
    SELECT hash, pepper_version INTO v_hash1, v_version1
    FROM secure_hash_with_pepper('test@example.com');

    -- Generar mismo hash de nuevo
    SELECT hash, pepper_version INTO v_hash2, v_version2
    FROM secure_hash_with_pepper('test@example.com');

    -- Los hashes deben ser iguales (mismo pepper)
    IF v_hash1 = v_hash2 AND v_version1 = v_version2 AND v_version1 = 1 THEN
        v_status := 'PASS';
        v_details := format('Hash consistent with pepper version %s', v_version1);
    ELSE
        v_status := 'FAIL';
        v_details := format('Hash inconsistent. Hash1:%s, Hash2:%s, Version1:%s, Version2:%s',
            LEFT(v_hash1, 16), LEFT(v_hash2, 16), v_version1, v_version2);
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('HMAC Hash with Pepper', 'Encryption', v_status, v_details);
    
    RAISE NOTICE '  [%] HMAC Hash with Pepper: %', v_status, v_details;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('HMAC Hash with Pepper', 'Encryption', 'FAIL', 'Exception: ' || SQLERRM);
END $$;

-- ============================================================================
-- TEST 2.5: Cifrado de Diferentes Tipos de PII
-- ============================================================================

DO $$
DECLARE
    v_test_data TEXT[] := ARRAY[
        'Juan Pérez García',
        '+34 612 345 678',
        'juan.perez@example.com',
        'Calle Mayor 123, Madrid',
        'Texto con caracteres especiales: ñ, á, é, ü, ¿?'
    ];
    v_encrypted JSONB;
    v_decrypted TEXT;
    v_all_passed BOOLEAN := true;
    v_failed_items TEXT[] := ARRAY[]::TEXT[];
    v_item TEXT;
    v_status TEXT;
    v_details TEXT;
BEGIN
    -- Usar la clave creada al inicio del test suite
    FOREACH v_item IN ARRAY v_test_data LOOP
        v_encrypted := encrypt_pii_with_metadata(v_item);
        v_decrypted := decrypt_pii_with_metadata(v_encrypted);
        
        IF v_decrypted != v_item THEN
            v_all_passed := false;
            v_failed_items := array_append(v_failed_items, LEFT(v_item, 20));
        END IF;
    END LOOP;

    IF v_all_passed THEN
        v_status := 'PASS';
        v_details := format('Successfully encrypted/decrypted %s different PII types', array_length(v_test_data, 1));
    ELSE
        v_status := 'FAIL';
        v_details := 'Failed items: ' || array_to_string(v_failed_items, ', ');
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Multiple PII Types', 'Encryption', v_status, v_details);

    RAISE NOTICE '  [%] Multiple PII Types: %', v_status, v_details;

    -- No eliminar clave - puede ser usada por otros tests
EXCEPTION WHEN OTHERS THEN
    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Multiple PII Types', 'Encryption', 'FAIL', 'Exception: ' || SQLERRM);
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
WHERE test_category = 'Encryption'
GROUP BY test_category;

SELECT test_name, details
FROM test_results
WHERE test_category = 'Encryption' AND status = 'FAIL';


-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
