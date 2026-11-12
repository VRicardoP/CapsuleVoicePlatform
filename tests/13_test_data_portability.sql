-- =====================================================
-- TEST 13: PORTABILIDAD DE DATOS (Art. 20 RGPD)
-- =====================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 20: Derecho a la portabilidad
--   • RGPD Art. 15.3: Derecho a obtener copia de datos
--   • LOPDGDD Art. 17: Portabilidad en formatos estructurados
-- 
-- NIVEL DE COMPLIANCE: ALTO
-- CRITICIDAD: ALTA
-- REQUISITOS NORMATIVA.MD: PARTE 1 (RGPD) - Art. 20
-- ============================================================================
-- Verifica el cumplimiento del derecho a la portabilidad
-- de datos según el Artículo 20 del RGPD
-- =====================================================

-- Iniciar transacción para garantizar idempotencia
BEGIN;

-- Configurar para detectar errores
\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '=============================================='
\echo 'TEST 13: PORTABILIDAD DE DATOS (Art. 20 RGPD)'
\echo '=============================================='
\echo ''

-- Contadores de tests
DO $$
BEGIN
    DROP TABLE IF EXISTS test_results;
    CREATE TEMP TABLE test_results (
        test_number INTEGER,
        test_name VARCHAR(200),
        passed BOOLEAN,
        details TEXT
    );
END $$;

-- =====================================================
-- TEST 13.1: Existencia de tabla data_exports
-- =====================================================
\echo 'Test 13.1: Verificando existencia de tabla data_exports...'
DO $$
DECLARE
    v_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'data_exports'
    ) INTO v_exists;

    INSERT INTO test_results VALUES (1, 'Tabla data_exports existe', v_exists,
        CASE WHEN v_exists THEN 'OK' ELSE 'ERROR: Tabla data_exports no existe' END);

    IF v_exists THEN
        RAISE NOTICE 'PASS: Tabla data_exports existe';
    ELSE
        RAISE WARNING 'FAIL: Tabla data_exports no existe';
    END IF;
END $$;

-- =====================================================
-- TEST 13.2: Estructura correcta de data_exports
-- =====================================================
\echo 'Test 13.2: Verificando estructura de data_exports...'
DO $$
DECLARE
    v_columns TEXT[];
    v_required_columns TEXT[] := ARRAY[
        'id', 'data_subject_id', 'data_subject_type', 'requested_by',
        'export_format', 'status', 'export_data', 'download_token',
        'download_token_expires_at', 'download_count', 'max_downloads',
        'expires_at', 'created_at', 'completed_at'
    ];
    v_missing TEXT[];
    v_all_present BOOLEAN;
BEGIN
    SELECT ARRAY_AGG(column_name::TEXT) INTO v_columns
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'data_exports';

    SELECT ARRAY_AGG(col) INTO v_missing
    FROM UNNEST(v_required_columns) AS col
    WHERE col != ALL(COALESCE(v_columns, ARRAY[]::TEXT[]));

    v_all_present := (v_missing IS NULL OR array_length(v_missing, 1) IS NULL);

    INSERT INTO test_results VALUES (2, 'Estructura data_exports correcta', v_all_present,
        CASE WHEN v_all_present THEN 'OK'
        ELSE 'ERROR: Faltan columnas: ' || array_to_string(v_missing, ', ') END);

    IF v_all_present THEN
        RAISE NOTICE 'PASS: Estructura de data_exports correcta';
    ELSE
        RAISE WARNING 'FAIL: Faltan columnas: %', array_to_string(v_missing, ', ');
    END IF;
END $$;

-- =====================================================
-- TEST 13.3: Función export_user_data existe
-- =====================================================
\echo 'Test 13.3: Verificando función export_user_data...'
DO $$
DECLARE
    v_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public'
        AND p.proname = 'export_user_data'
    ) INTO v_exists;

    INSERT INTO test_results VALUES (3, 'Función export_user_data existe', v_exists,
        CASE WHEN v_exists THEN 'OK' ELSE 'ERROR: Función no existe' END);

    IF v_exists THEN
        RAISE NOTICE 'PASS: Función export_user_data existe';
    ELSE
        RAISE WARNING 'FAIL: Función export_user_data no existe';
    END IF;
END $$;

-- =====================================================
-- TEST 13.4: Función export_contact_data existe
-- =====================================================
\echo 'Test 13.4: Verificando función export_contact_data...'
DO $$
DECLARE
    v_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public'
        AND p.proname = 'export_contact_data'
    ) INTO v_exists;

    INSERT INTO test_results VALUES (4, 'Función export_contact_data existe', v_exists,
        CASE WHEN v_exists THEN 'OK' ELSE 'ERROR: Función no existe' END);

    IF v_exists THEN
        RAISE NOTICE 'PASS: Función export_contact_data existe';
    ELSE
        RAISE WARNING 'FAIL: Función export_contact_data no existe';
    END IF;
END $$;

-- =====================================================
-- TEST 13.5: Función get_export_by_token existe
-- =====================================================
\echo 'Test 13.5: Verificando función get_export_by_token...'
DO $$
DECLARE
    v_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public'
        AND p.proname = 'get_export_by_token'
    ) INTO v_exists;

    INSERT INTO test_results VALUES (5, 'Función get_export_by_token existe', v_exists,
        CASE WHEN v_exists THEN 'OK' ELSE 'ERROR: Función no existe' END);

    IF v_exists THEN
        RAISE NOTICE 'PASS: Función get_export_by_token existe';
    ELSE
        RAISE WARNING 'FAIL: Función get_export_by_token no existe';
    END IF;
END $$;

-- =====================================================
-- PREPARACIÓN DE DATOS DE PRUEBA
-- =====================================================
\echo ''
\echo 'Preparando datos de prueba...'

-- Configurar clave HMAC para audit_log (requerida para triggers)
SELECT set_config('app.audit_hmac_key', 'test-hmac-key-for-portability-tests-only', false);

-- Crear tabla temporal para almacenar IDs de prueba (compartida entre bloques DO)
CREATE TEMP TABLE IF NOT EXISTS test_portability_ids (
    admin_id UUID,
    user_id UUID,
    contact_id UUID
);

-- Crear usuarios y contactos de prueba con UUIDs dinámicos
DO $$
DECLARE
    v_admin_id UUID := gen_random_uuid();
    v_user_id UUID := gen_random_uuid();
    v_contact_id UUID := gen_random_uuid();
    v_phone_hash VARCHAR(64);
    v_unique_suffix TEXT := substring(gen_random_uuid()::TEXT, 1, 8);
BEGIN
    -- Configurar HMAC dentro del bloque también
    PERFORM set_config('app.audit_hmac_key', 'test-hmac-key-for-portability-tests-only', false);

    -- Limpiar IDs anteriores de esta sesión
    DELETE FROM test_portability_ids;

    -- Guardar IDs para uso en otros bloques DO
    INSERT INTO test_portability_ids (admin_id, user_id, contact_id)
    VALUES (v_admin_id, v_user_id, v_contact_id);

    -- Crear usuario admin con email único
    INSERT INTO users (id, email, password_hash, role, name, is_active)
    VALUES (
        v_admin_id,
        'admin_portability_' || v_unique_suffix || '@capsule.test',
        crypt('TestPassword123!', gen_salt('bf', 12)),
        'admin',
        'Admin Portabilidad Test',
        true
    );

    -- Crear usuario regular para exportar sus datos
    INSERT INTO users (id, email, password_hash, role, name, is_active)
    VALUES (
        v_user_id,
        'user_portability_' || v_unique_suffix || '@capsule.test',
        crypt('TestPassword123!', gen_salt('bf', 12)),
        'user',
        'Usuario Portabilidad Test',
        true
    );

    -- Generar hash para el teléfono del contacto
    v_phone_hash := encode(sha256(('+34600' || v_unique_suffix)::bytea), 'hex');

    -- Crear contacto con campos cifrados (estructura real de la BD)
    INSERT INTO contacts (id, user_id, name_encrypted, phone_encrypted, phone_hash, phone_hash_pepper_version, created_at)
    VALUES (
        v_contact_id,
        v_user_id,
        '{"iv": "test", "data": "Q29udGFjdG8gUG9ydGFiaWxpZGFkIFRlc3Q=", "tag": "test"}'::JSONB,
        '{"iv": "test", "data": "KzM0NjAwMDAwMDEz", "tag": "test"}'::JSONB,
        v_phone_hash,
        1,
        CURRENT_TIMESTAMP
    );

    -- Guardar IDs en config para acceso desde otros bloques
    PERFORM set_config('test.admin_id', v_admin_id::TEXT, false);
    PERFORM set_config('test.user_id', v_user_id::TEXT, false);
    PERFORM set_config('test.contact_id', v_contact_id::TEXT, false);

    RAISE NOTICE 'Datos de prueba creados correctamente (admin=%, user=%, contact=%)',
        v_admin_id, v_user_id, v_contact_id;
END $$;

-- Establecer contexto de admin (usa el ID dinámico)
SELECT set_config('app.current_user_id', current_setting('test.admin_id'), false);

-- =====================================================
-- TEST 13.6: Exportación de datos de usuario (admin exportando)
-- =====================================================
\echo ''
\echo 'Test 13.6: Verificando exportación de datos de usuario...'
DO $$
DECLARE
    v_result JSON;
    v_success BOOLEAN;
    v_has_required_fields BOOLEAN;
BEGIN
    -- Configurar HMAC
    PERFORM set_config('app.audit_hmac_key', 'test-hmac-key-for-portability-tests-only', false);
    PERFORM set_config('app.current_user_id', current_setting('test.admin_id'), false);

    -- Admin exporta datos del usuario de prueba
    SELECT export_user_data(
        current_setting('test.user_id')::UUID,
        'user',
        true,  -- include_contacts
        true,  -- include_calls
        'json'
    ) INTO v_result;

    v_success := v_result IS NOT NULL
                 AND (v_result->>'success')::BOOLEAN = true;

    -- Verificar campos requeridos (data->user_data según la función)
    v_has_required_fields := v_result->'data' IS NOT NULL
                            AND v_result->'data'->'user_data' IS NOT NULL;

    INSERT INTO test_results VALUES (6, 'Exportación de datos de usuario funciona',
        v_success AND v_has_required_fields,
        CASE WHEN v_success AND v_has_required_fields THEN 'OK: Datos exportados correctamente'
        ELSE 'ERROR: ' || COALESCE(v_result->>'error', 'Exportación falló o estructura incompleta') END);

    IF v_success AND v_has_required_fields THEN
        RAISE NOTICE 'PASS: Exportación de datos de usuario funciona';
    ELSE
        RAISE WARNING 'FAIL: Exportación de datos de usuario falló: %', COALESCE(v_result->>'error', 'Sin detalle');
    END IF;
END $$;

-- =====================================================
-- TEST 13.7: Exportación de datos de contacto
-- =====================================================
\echo 'Test 13.7: Verificando exportación de datos de contacto...'

-- Cambiar contexto al propietario del contacto para exportar
SELECT set_config('app.current_user_id', current_setting('test.user_id'), false);

DO $$
DECLARE
    v_result JSON;
    v_success BOOLEAN;
BEGIN
    -- Propietario exporta datos del contacto
    SELECT export_contact_data(
        current_setting('test.contact_id')::UUID,
        true,   -- include_calls
        false,  -- include_transcriptions
        'json'
    ) INTO v_result;

    v_success := v_result IS NOT NULL
                 AND (v_result->>'success')::BOOLEAN = true;

    INSERT INTO test_results VALUES (7, 'Exportación de datos de contacto funciona', v_success,
        CASE WHEN v_success THEN 'OK: Datos de contacto exportados'
        ELSE 'ERROR: ' || COALESCE(v_result->>'error', 'Exportación falló') END);

    IF v_success THEN
        RAISE NOTICE 'PASS: Exportación de datos de contacto funciona';
    ELSE
        RAISE WARNING 'FAIL: Exportación de datos de contacto falló: %', COALESCE(v_result->>'error', 'Sin detalle');
    END IF;
END $$;

-- Restaurar contexto admin
SELECT set_config('app.current_user_id', current_setting('test.admin_id'), false);

-- =====================================================
-- TEST 13.8: Registro de exportación en data_exports
-- =====================================================
\echo 'Test 13.8: Verificando registro de exportaciones...'
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM data_exports
    WHERE data_subject_id IN (
        current_setting('test.user_id')::UUID,
        current_setting('test.contact_id')::UUID
    );

    INSERT INTO test_results VALUES (8, 'Exportaciones registradas en data_exports', v_count > 0,
        CASE WHEN v_count > 0 THEN 'OK: ' || v_count || ' exportaciones registradas'
        ELSE 'ERROR: No se registraron exportaciones' END);

    IF v_count > 0 THEN
        RAISE NOTICE 'PASS: % exportaciones registradas en data_exports', v_count;
    ELSE
        RAISE WARNING 'FAIL: No se registraron exportaciones';
    END IF;
END $$;

-- =====================================================
-- TEST 13.9: Token de descarga generado
-- =====================================================
\echo 'Test 13.9: Verificando generación de token de descarga...'
DO $$
DECLARE
    v_token VARCHAR;
    v_expires_at TIMESTAMP WITH TIME ZONE;
    v_valid BOOLEAN;
BEGIN
    SELECT download_token, download_token_expires_at INTO v_token, v_expires_at
    FROM data_exports
    WHERE status = 'completed'
    AND data_subject_id IN (
        current_setting('test.user_id')::UUID,
        current_setting('test.contact_id')::UUID
    )
    ORDER BY created_at DESC
    LIMIT 1;

    v_valid := v_token IS NOT NULL
               AND LENGTH(v_token) > 20
               AND v_expires_at > CURRENT_TIMESTAMP;

    INSERT INTO test_results VALUES (9, 'Token de descarga generado correctamente', v_valid,
        CASE WHEN v_valid THEN 'OK: Token válido con expiración futura'
        ELSE 'ERROR: Token no generado o expirado' END);

    IF v_valid THEN
        RAISE NOTICE 'PASS: Token de descarga generado correctamente';
    ELSE
        RAISE WARNING 'FAIL: Token de descarga no válido';
    END IF;
END $$;

-- =====================================================
-- TEST 13.10: Descarga por token funciona
-- =====================================================
\echo 'Test 13.10: Verificando descarga por token...'
DO $$
DECLARE
    v_token VARCHAR;
    v_result JSON;
    v_success BOOLEAN;
BEGIN
    -- Obtener un token válido
    SELECT download_token INTO v_token
    FROM data_exports
    WHERE status = 'completed'
    AND download_token_expires_at > CURRENT_TIMESTAMP
    AND download_count < max_downloads
    AND data_subject_id IN (
        current_setting('test.user_id')::UUID,
        current_setting('test.contact_id')::UUID
    )
    ORDER BY created_at DESC
    LIMIT 1;

    IF v_token IS NOT NULL THEN
        SELECT get_export_by_token(v_token) INTO v_result;
        v_success := v_result IS NOT NULL AND (v_result->>'success')::BOOLEAN = true;
    ELSE
        v_success := false;
    END IF;

    INSERT INTO test_results VALUES (10, 'Descarga por token funciona', v_success,
        CASE WHEN v_success THEN 'OK: Descarga exitosa'
        ELSE 'ERROR: Descarga falló - ' || COALESCE(v_result->>'error', 'No hay token disponible') END);

    IF v_success THEN
        RAISE NOTICE 'PASS: Descarga por token funciona';
    ELSE
        RAISE WARNING 'FAIL: Descarga por token falló';
    END IF;
END $$;

-- =====================================================
-- TEST 13.11: Contador de descargas incrementa
-- =====================================================
\echo 'Test 13.11: Verificando contador de descargas...'
DO $$
DECLARE
    v_token VARCHAR;
    v_count_before INTEGER;
    v_count_after INTEGER;
    v_result JSON;
BEGIN
    -- Obtener token y su contador actual
    SELECT download_token, download_count INTO v_token, v_count_before
    FROM data_exports
    WHERE status = 'completed'
    AND download_token_expires_at > CURRENT_TIMESTAMP
    AND download_count < max_downloads - 1
    AND data_subject_id IN (
        current_setting('test.user_id')::UUID,
        current_setting('test.contact_id')::UUID
    )
    ORDER BY created_at DESC
    LIMIT 1;

    IF v_token IS NOT NULL THEN
        -- Realizar descarga
        SELECT get_export_by_token(v_token) INTO v_result;

        -- Verificar contador incrementado
        SELECT download_count INTO v_count_after
        FROM data_exports
        WHERE download_token = v_token;

        INSERT INTO test_results VALUES (11, 'Contador de descargas incrementa',
            v_count_after > v_count_before,
            CASE WHEN v_count_after > v_count_before
            THEN 'OK: Contador: ' || v_count_before || ' -> ' || v_count_after
            ELSE 'ERROR: Contador no incrementó' END);

        IF v_count_after > v_count_before THEN
            RAISE NOTICE 'PASS: Contador de descargas incrementó de % a %', v_count_before, v_count_after;
        ELSE
            RAISE WARNING 'FAIL: Contador no incrementó';
        END IF;
    ELSE
        INSERT INTO test_results VALUES (11, 'Contador de descargas incrementa', false,
            'SKIP: No hay tokens disponibles para test');
        RAISE NOTICE 'SKIP: No hay tokens disponibles para probar incremento';
    END IF;
END $$;

-- =====================================================
-- TEST 13.12: Límite de descargas respetado
-- =====================================================
\echo 'Test 13.12: Verificando límite de descargas...'
DO $$
DECLARE
    v_export_id UUID;
    v_token VARCHAR;
    v_result JSON;
    v_blocked BOOLEAN;
BEGIN
    -- Crear una exportación con límite alcanzado
    INSERT INTO data_exports (
        id, data_subject_id, data_subject_type, requested_by,
        export_format, status, export_data, download_token,
        download_token_expires_at, download_count, max_downloads
    )
    VALUES (
        gen_random_uuid(),
        current_setting('test.user_id')::UUID,
        'user',
        current_setting('test.admin_id')::UUID,
        'json',
        'completed',
        '{"test": "data"}'::JSONB,
        'TEST_TOKEN_MAX_DOWNLOADS_' || gen_random_uuid()::TEXT,
        CURRENT_TIMESTAMP + INTERVAL '1 day',
        3,  -- Ya descargado 3 veces
        3   -- Máximo 3 descargas
    )
    RETURNING id, download_token INTO v_export_id, v_token;

    -- Intentar descargar (debería fallar)
    SELECT get_export_by_token(v_token) INTO v_result;

    v_blocked := v_result IS NOT NULL
                 AND (v_result->>'success')::BOOLEAN = false
                 AND (v_result->>'error' LIKE '%descargas%' OR v_result->>'error' LIKE '%download%');

    INSERT INTO test_results VALUES (12, 'Límite de descargas respetado', v_blocked,
        CASE WHEN v_blocked THEN 'OK: Descarga bloqueada al alcanzar límite'
        ELSE 'ERROR: ' || COALESCE(v_result->>'error', 'Sin mensaje de error') END);

    IF v_blocked THEN
        RAISE NOTICE 'PASS: Límite de descargas respetado';
    ELSE
        RAISE WARNING 'FAIL: Límite de descargas no respetado - %', COALESCE(v_result->>'error', 'Sin detalle');
    END IF;

    -- Limpiar
    DELETE FROM data_exports WHERE id = v_export_id;
END $$;

-- =====================================================
-- TEST 13.13: Token expirado rechazado
-- =====================================================
\echo 'Test 13.13: Verificando rechazo de token expirado...'
DO $$
DECLARE
    v_export_id UUID;
    v_token VARCHAR;
    v_result JSON;
    v_rejected BOOLEAN;
BEGIN
    -- Crear exportación con token expirado
    INSERT INTO data_exports (
        id, data_subject_id, data_subject_type, requested_by,
        export_format, status, export_data, download_token,
        download_token_expires_at, download_count, max_downloads
    )
    VALUES (
        gen_random_uuid(),
        current_setting('test.user_id')::UUID,
        'user',
        current_setting('test.admin_id')::UUID,
        'json',
        'completed',
        '{"test": "data"}'::JSONB,
        'TEST_TOKEN_EXPIRED_' || gen_random_uuid()::TEXT,
        CURRENT_TIMESTAMP - INTERVAL '1 day',  -- Expirado ayer
        0,
        3
    )
    RETURNING id, download_token INTO v_export_id, v_token;

    -- Intentar descargar (debería fallar)
    SELECT get_export_by_token(v_token) INTO v_result;

    v_rejected := v_result IS NOT NULL
                  AND (v_result->>'success')::BOOLEAN = false
                  AND (v_result->>'error' LIKE '%expirado%' OR v_result->>'error' LIKE '%expired%');

    INSERT INTO test_results VALUES (13, 'Token expirado rechazado', v_rejected,
        CASE WHEN v_rejected THEN 'OK: Token expirado rechazado correctamente'
        ELSE 'ERROR: ' || COALESCE(v_result->>'error', 'Sin mensaje de error') END);

    IF v_rejected THEN
        RAISE NOTICE 'PASS: Token expirado rechazado correctamente';
    ELSE
        RAISE WARNING 'FAIL: Token expirado no fue rechazado - %', COALESCE(v_result->>'error', 'Sin detalle');
    END IF;

    -- Limpiar
    DELETE FROM data_exports WHERE id = v_export_id;
END $$;

-- =====================================================
-- TEST 13.14: Formato de exportación estructurado
-- =====================================================
\echo 'Test 13.14: Verificando formato estructurado de exportación...'
DO $$
DECLARE
    v_result JSON;
    v_export_data JSON;
    v_has_structure BOOLEAN;
BEGIN
    -- Configurar HMAC y contexto
    PERFORM set_config('app.audit_hmac_key', 'test-hmac-key-for-portability-tests-only', false);
    PERFORM set_config('app.current_user_id', current_setting('test.admin_id'), false);

    SELECT export_user_data(
        current_setting('test.user_id')::UUID,
        'user', true, true, 'json'
    ) INTO v_result;

    v_export_data := v_result->'data';

    -- Verificar estructura mínima requerida (user_data y export_metadata según la función)
    v_has_structure := v_export_data IS NOT NULL
                       AND v_export_data->'user_data' IS NOT NULL
                       AND v_export_data->'export_metadata' IS NOT NULL;

    INSERT INTO test_results VALUES (14, 'Formato de exportación estructurado', v_has_structure,
        CASE WHEN v_has_structure THEN 'OK: Formato JSON estructurado correctamente'
        ELSE 'ERROR: Estructura incompleta - export_data: ' || COALESCE(v_export_data::TEXT, 'NULL') END);

    IF v_has_structure THEN
        RAISE NOTICE 'PASS: Formato de exportación estructurado correctamente';
    ELSE
        RAISE WARNING 'FAIL: Formato de exportación incompleto';
    END IF;
END $$;

-- =====================================================
-- TEST 13.15: No se exportan datos sensibles
-- =====================================================
\echo 'Test 13.15: Verificando exclusión de datos sensibles...'
DO $$
DECLARE
    v_result JSON;
    v_export_text TEXT;
    v_has_sensitive BOOLEAN;
BEGIN
    SELECT export_user_data(
        current_setting('test.user_id')::UUID,
        'user', true, true, 'json'
    ) INTO v_result;

    -- Convertir a texto para buscar patrones sensibles
    v_export_text := COALESCE(v_result::TEXT, '');

    -- Verificar que no hay datos sensibles
    v_has_sensitive := v_export_text LIKE '%password_hash%'
                       OR v_export_text LIKE '%encryption_key%'
                       OR v_export_text LIKE '%mfa_secret%'
                       OR v_export_text LIKE '%two_factor_secret%';

    INSERT INTO test_results VALUES (15, 'Datos sensibles excluidos de exportación', NOT v_has_sensitive,
        CASE WHEN NOT v_has_sensitive THEN 'OK: Sin datos sensibles en exportación'
        ELSE 'ERROR: Datos sensibles encontrados en exportación' END);

    IF NOT v_has_sensitive THEN
        RAISE NOTICE 'PASS: Datos sensibles excluidos de exportación';
    ELSE
        RAISE WARNING 'FAIL: Datos sensibles incluidos en exportación';
    END IF;
END $$;

-- =====================================================
-- TEST 13.16: Función get_data_exports existe
-- =====================================================
\echo 'Test 13.16: Verificando función get_data_exports...'
DO $$
DECLARE
    v_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public'
        AND p.proname = 'get_data_exports'
    ) INTO v_exists;

    INSERT INTO test_results VALUES (16, 'Función get_data_exports existe', v_exists,
        CASE WHEN v_exists THEN 'OK' ELSE 'ERROR: Función no existe' END);

    IF v_exists THEN
        RAISE NOTICE 'PASS: Función get_data_exports existe';
    ELSE
        RAISE WARNING 'FAIL: Función get_data_exports no existe';
    END IF;
END $$;

-- =====================================================
-- TEST 13.17: Función cleanup_expired_exports existe
-- =====================================================
\echo 'Test 13.17: Verificando función cleanup_expired_exports...'
DO $$
DECLARE
    v_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public'
        AND p.proname = 'cleanup_expired_exports'
    ) INTO v_exists;

    INSERT INTO test_results VALUES (17, 'Función cleanup_expired_exports existe', v_exists,
        CASE WHEN v_exists THEN 'OK' ELSE 'ERROR: Función no existe' END);

    IF v_exists THEN
        RAISE NOTICE 'PASS: Función cleanup_expired_exports existe';
    ELSE
        RAISE WARNING 'FAIL: Función cleanup_expired_exports no existe';
    END IF;
END $$;

-- =====================================================
-- TEST 13.18: Vista v_data_exports_dashboard existe
-- =====================================================
\echo 'Test 13.18: Verificando vista v_data_exports_dashboard...'
DO $$
DECLARE
    v_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.views
        WHERE table_schema = 'public'
        AND table_name = 'v_data_exports_dashboard'
    ) INTO v_exists;

    INSERT INTO test_results VALUES (18, 'Vista v_data_exports_dashboard existe', v_exists,
        CASE WHEN v_exists THEN 'OK' ELSE 'ERROR: Vista no existe' END);

    IF v_exists THEN
        RAISE NOTICE 'PASS: Vista v_data_exports_dashboard existe';
    ELSE
        RAISE WARNING 'FAIL: Vista v_data_exports_dashboard no existe';
    END IF;
END $$;

-- =====================================================
-- TEST 13.19: Limpieza de exportaciones expiradas
-- =====================================================
\echo 'Test 13.19: Verificando limpieza de exportaciones expiradas...'
DO $$
DECLARE
    v_export_id UUID;
    v_cleaned INTEGER;
    v_status VARCHAR;
    v_export_data JSONB;
    v_success BOOLEAN;
BEGIN
    -- Crear exportación ya expirada
    INSERT INTO data_exports (
        id, data_subject_id, data_subject_type, requested_by,
        export_format, status, export_data,
        expires_at, created_at
    )
    VALUES (
        gen_random_uuid(),
        current_setting('test.user_id')::UUID,
        'user',
        current_setting('test.admin_id')::UUID,
        'json',
        'completed',
        '{"test": "expired"}'::JSONB,
        CURRENT_TIMESTAMP - INTERVAL '10 days',  -- Expirada hace 10 días
        CURRENT_TIMESTAMP - INTERVAL '20 days'
    )
    RETURNING id INTO v_export_id;

    -- Ejecutar limpieza
    SELECT cleanup_expired_exports() INTO v_cleaned;

    -- Verificar que se marcó como expirada y los datos fueron eliminados
    SELECT status, export_data INTO v_status, v_export_data
    FROM data_exports WHERE id = v_export_id;

    -- La función marca como 'expired' y pone export_data a NULL
    v_success := (v_status = 'expired' AND v_export_data IS NULL)
                 OR v_status IS NULL;  -- O ya fue eliminada

    INSERT INTO test_results VALUES (19, 'Limpieza de exportaciones expiradas funciona',
        v_success,
        CASE WHEN v_success THEN 'OK: Exportación marcada como expirada y datos eliminados'
        ELSE 'ERROR: Status=' || COALESCE(v_status, 'NULL') || ', Data=' || COALESCE(v_export_data::TEXT, 'NULL') END);

    IF v_success THEN
        RAISE NOTICE 'PASS: Exportación marcada como expirada correctamente';
    ELSE
        RAISE WARNING 'FAIL: Exportación no procesada correctamente';
    END IF;

    -- Limpiar
    DELETE FROM data_exports WHERE id = v_export_id;
END $$;

-- =====================================================
-- TEST 13.20: Auditoría de exportaciones en audit_log
-- =====================================================
\echo 'Test 13.20: Verificando auditoría de exportaciones...'
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM audit_log
    WHERE action = 'DATA_EXPORT'
    AND created_at > CURRENT_TIMESTAMP - INTERVAL '5 minutes';

    INSERT INTO test_results VALUES (20, 'Exportaciones registradas en audit_log', v_count > 0,
        CASE WHEN v_count > 0 THEN 'OK: ' || v_count || ' exportaciones en audit_log'
        ELSE 'ERROR: No hay registros de exportación en audit_log' END);

    IF v_count > 0 THEN
        RAISE NOTICE 'PASS: % exportaciones registradas en audit_log', v_count;
    ELSE
        RAISE WARNING 'FAIL: No hay registros de exportación en audit_log';
    END IF;
END $$;

-- =====================================================
-- NOTA: No se necesita limpieza manual de datos de prueba
-- ROLLBACK al final del test elimina todo automáticamente
-- Esto es más seguro porque audit_log es inmutable
-- =====================================================
\echo ''
\echo 'Datos de prueba seran eliminados por ROLLBACK...'

-- =====================================================
-- RESUMEN DE RESULTADOS
-- =====================================================
\echo ''
\echo '=============================================='
\echo 'RESUMEN DE RESULTADOS - TEST 13 (Art. 20 RGPD)'
\echo '=============================================='

SELECT
    CASE WHEN passed THEN 'PASS' ELSE 'FAIL' END AS resultado,
    'Test 13.' || test_number || ': ' || test_name AS test,
    details
FROM test_results
ORDER BY test_number;

\echo ''

SELECT
    COUNT(*) FILTER (WHERE passed) AS tests_passed,
    COUNT(*) FILTER (WHERE NOT passed) AS tests_failed,
    COUNT(*) AS total_tests,
    ROUND(100.0 * COUNT(*) FILTER (WHERE passed) / COUNT(*), 1) AS porcentaje_exito
FROM test_results;

\echo ''
\echo 'Test 13 completado.'
\echo '=============================================='

-- Limpiar tabla temporal
DROP TABLE IF EXISTS test_results;

-- ============================================================================
-- FIN DEL TEST - Revertir todos los cambios (idempotencia)
-- ============================================================================
ROLLBACK;
