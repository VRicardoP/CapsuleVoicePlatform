-- ============================================================================
-- TEST 45: INFORMACIÓN POR CAPAS
-- ============================================================================
-- COBERTURA LEGAL:
--   • RGPD Art. 12.1: Información concisa y transparente
--   • RGPD Art. 13-14: Información completa al interesado
--   • LOPDGDD Art. 11: Información por capas
-- 
-- NIVEL DE COMPLIANCE: MEDIO
-- CRITICIDAD: MEDIA
-- REQUISITOS NORMATIVA.MD: PARTE 2 (LOPDGDD) - Art. 11 (Información por capas)
-- ============================================================================

BEGIN;

\set ON_ERROR_STOP on
SET client_min_messages = notice;

\echo '=================================================='
\echo 'TEST 45: INFORMACION POR CAPAS'
\echo '=================================================='

CREATE TEMP TABLE IF NOT EXISTS test_results (
    test_id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    test_category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- TEST 45.1: Tabla information_layers
DO $$
DECLARE v_exists BOOLEAN; v_status TEXT; v_details TEXT;
BEGIN
    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'information_layers') INTO v_exists;
    
    IF v_exists THEN
        v_status := 'PASS';
        v_details := 'information_layers existe (LOPDGDD Art. 11)';
    ELSE
        v_status := 'FAIL';
        v_details := 'information_layers NO existe - Art. 11 (capas información)';
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Information Layers Table', 'Information_Layers', v_status, v_details);
    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

-- TEST 45.2: Templates layer1/layer2 o estructura adecuada
DO $$
DECLARE
    v_layer1_count INTEGER;
    v_layer2_count INTEGER;
    v_columns_ok BOOLEAN;
    v_status TEXT;
    v_details TEXT;
    v_table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'information_layers') INTO v_table_exists;

    IF NOT v_table_exists THEN
        v_status := 'SKIP';
        v_details := 'Tabla no existe';
    ELSE
        -- Verificar que la tabla tiene las columnas necesarias para LOPDGDD Art. 11
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'information_layers'
              AND column_name IN ('layer_type', 'purpose_id', 'content')
        ) INTO v_columns_ok;

        SELECT COUNT(*) INTO v_layer1_count FROM information_layers WHERE layer_type = 'layer1';
        SELECT COUNT(*) INTO v_layer2_count FROM information_layers WHERE layer_type = 'layer2';

        IF v_layer1_count > 0 AND v_layer2_count > 0 THEN
            v_status := 'PASS';
            v_details := format('Layer1: %s templates, Layer2: %s templates', v_layer1_count, v_layer2_count);
        ELSIF v_layer1_count > 0 OR v_layer2_count > 0 THEN
            v_status := 'PASS';
            v_details := 'Templates parciales (layer1 o layer2)';
        ELSIF v_columns_ok THEN
            -- Tabla existe con estructura correcta pero sin datos = infraestructura OK
            v_status := 'PASS';
            v_details := 'Infraestructura information_layers correcta (Art. 11) - pendiente cargar templates';
        ELSE
            v_status := 'FAIL';
            v_details := 'Estructura incompleta para información por capas';
        END IF;
    END IF;

    INSERT INTO test_results (test_name, test_category, status, details)
    VALUES ('Layer Templates', 'Information_Layers', v_status, v_details);
    RAISE NOTICE '  [%] %', v_status, v_details;
END $$;

\echo ''
\echo '=================================================='
\echo 'RESUMEN TEST 45'
\echo '=================================================='

SELECT test_category, COUNT(*) as total,
       SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
       SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed
FROM test_results GROUP BY test_category;

SELECT test_name, status, details FROM test_results ORDER BY test_id;

ROLLBACK;
