-- ============================================================================
-- SEED FIXTURES - Datos compartidos requeridos por múltiples tests
-- ============================================================================
-- Este archivo crea datos base que los tests asumen que existen
-- Se ejecuta ANTES de cada test para garantizar fixtures consistentes
-- ============================================================================

-- Configurar variables de sesión para cifrado
DO $$
BEGIN
    -- Solo configurar si no está ya configurado
    IF current_setting('app.kms_master_key', true) IS NULL OR 
       current_setting('app.kms_master_key', true) = '' THEN
        PERFORM set_config('app.kms_master_key', 'TEST_MASTER_KEY_FOR_TESTS_32CHAR', false);
    END IF;
    
    IF current_setting('app.hash_pepper', true) IS NULL OR 
       current_setting('app.hash_pepper', true) = '' THEN
        PERFORM set_config('app.hash_pepper', 'TEST_PEPPER_V1_FOR_HMAC_FUNCTIONS', false);
        PERFORM set_config('app.hash_pepper_version', '1', false);
    END IF;
    
    IF current_setting('app.audit_hmac_key', true) IS NULL OR
       current_setting('app.audit_hmac_key', true) = '' THEN
        PERFORM set_config('app.audit_hmac_key', 'TEST_AUDIT_KEY_FOR_HMAC_CHAIN__', false);
    END IF;

    -- MITIGACIÓN SEGURIDAD: Clave HMAC para firmar sesiones
    IF current_setting('app.session_hmac_key', true) IS NULL OR
       current_setting('app.session_hmac_key', true) = '' THEN
        PERFORM set_config('app.session_hmac_key', 'TEST_SESSION_HMAC_KEY_32CHARS__', false);
    END IF;
END $$;

-- ============================================================================
-- FIXTURE 1: data_processing_purposes
-- Requerido por: tests 01, 04, 05, 06, 08, 09, 10, 11, 12, 13, 15, 16, etc.
-- ============================================================================
INSERT INTO data_processing_purposes (code, name, legal_basis, retention_period_days, description) VALUES
    ('call_recording', 'Grabación de Llamadas', 'consent', 365, 
     'Grabación de conversaciones telefónicas para control de calidad'),
    ('call_analytics', 'Análisis de Llamadas', 'legitimate_interest', 180,
     'Análisis automático de conversaciones para métricas de negocio'),
    ('marketing', 'Comunicaciones Comerciales', 'consent', 730,
     'Envío de comunicaciones comerciales y promocionales'),
    ('customer_support', 'Atención al Cliente', 'contract', 365,
     'Gestión de solicitudes de soporte y atención al cliente'),
    ('quality_assurance', 'Control de Calidad', 'legitimate_interest', 180,
     'Evaluación de calidad del servicio prestado'),
    ('fraud_prevention', 'Prevención de Fraude', 'legal_obligation', 1825,
     'Detección y prevención de actividades fraudulentas'),
    ('ai_training', 'Entrenamiento de IA', 'consent', 365,
     'Mejora de modelos de inteligencia artificial')
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    legal_basis = EXCLUDED.legal_basis,
    retention_period_days = EXCLUDED.retention_period_days,
    description = EXCLUDED.description;

-- ============================================================================
-- FIXTURE 2: consent_versions
-- Crear versiones base de consentimiento para cada propósito
-- ============================================================================
INSERT INTO consent_versions (purpose_id, version, consent_text, consent_text_hash, effective_from)
SELECT 
    p.id,
    '1.0',
    'Consiento el ' || p.name || ' de mis datos personales para ' || p.description,
    encode(digest('Consiento el ' || p.name || ' de mis datos personales para ' || p.description, 'sha256'), 'hex'),
    '2024-01-01 00:00:00+00'::TIMESTAMP WITH TIME ZONE
FROM data_processing_purposes p
WHERE NOT EXISTS (
    SELECT 1 FROM consent_versions cv 
    WHERE cv.purpose_id = p.id AND cv.version = '1.0'
);

-- ============================================================================
-- FIXTURE 3: encryption_keys
-- Crear clave de cifrado compartida para tests (si no existe una activa)
-- ============================================================================
DO $$
DECLARE
    v_has_active_key BOOLEAN;
BEGIN
    -- Verificar si ya existe una clave activa
    SELECT EXISTS(SELECT 1 FROM encryption_keys WHERE is_active = true)
    INTO v_has_active_key;
    
    -- Solo crear si no hay ninguna activa
    IF NOT v_has_active_key THEN
        -- Desactivar cualquier clave previa de test
        UPDATE encryption_keys 
        SET is_active = false 
        WHERE key_id LIKE 'test_key_%';
        
        -- Crear nueva clave de test
        INSERT INTO encryption_keys (
            key_id,
            encrypted_key,
            algorithm,
            key_version,
            is_active,
            kms_provider,
            kms_key_id,
            activated_at
        ) VALUES (
            'test_key_shared_' || substring(gen_random_uuid()::TEXT, 1, 8),
            pgp_sym_encrypt(
                encode(gen_random_bytes(32), 'hex'),
                current_setting('app.kms_master_key'),
                'cipher-algo=aes256'
            ),
            'aes-256-gcm',
            1,
            true,
            'hashicorp-vault',
            'test-shared-key',
            CURRENT_TIMESTAMP
        );
        
        RAISE NOTICE '✓ Created shared test encryption key';
    ELSE
        RAISE NOTICE '✓ Active encryption key already exists';
    END IF;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Warning: Could not create encryption key: %', SQLERRM;
END $$;

-- Mensaje de confirmación
DO $$
DECLARE
    v_purposes_count INTEGER;
    v_versions_count INTEGER;
    v_keys_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_purposes_count FROM data_processing_purposes;
    SELECT COUNT(*) INTO v_versions_count FROM consent_versions;
    SELECT COUNT(*) INTO v_keys_count FROM encryption_keys WHERE is_active = true;
    
    RAISE NOTICE '✓ Fixtures loaded: % purposes, % consent versions, % active key(s)',
        v_purposes_count, v_versions_count, v_keys_count;
END $$;
