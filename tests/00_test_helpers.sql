-- ============================================================================
-- TEST HELPERS - Funciones auxiliares para la suite de tests
-- ============================================================================
-- Este archivo debe ejecutarse ANTES de cualquier test
-- ============================================================================

-- Configurar variables de sesión por defecto
SET client_min_messages = notice;

-- ============================================================================
-- Función: report_test_result
-- Propósito: Reportar resultado de test en formato que el runner puede capturar
-- ============================================================================
CREATE OR REPLACE FUNCTION report_test_result(
    p_status TEXT,
    p_test_name TEXT,
    p_details TEXT
) RETURNS VOID AS $$
BEGIN
    -- Formato: [STATUS] TestName: details
    -- Este formato es capturado por grep en run_all_tests.sh
    RAISE NOTICE '[%] %: %', p_status, p_test_name, p_details;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Tabla global de resultados de tests
-- ============================================================================
CREATE TABLE IF NOT EXISTS test_run_results (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    test_file TEXT NOT NULL,
    test_name TEXT NOT NULL,
    test_category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'SKIP')),
    details TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índice para búsquedas por run_id
CREATE INDEX IF NOT EXISTS idx_test_run_results_run_id 
    ON test_run_results(run_id);

-- ============================================================================
-- Función: get_test_run_id
-- Propósito: Obtener UUID de la ejecución actual de tests
-- ============================================================================
CREATE OR REPLACE FUNCTION get_test_run_id() RETURNS UUID AS $$
BEGIN
    RETURN COALESCE(
        nullif(current_setting('test.run_id', true), '')::UUID,
        gen_random_uuid()
    );
EXCEPTION WHEN OTHERS THEN
    RETURN gen_random_uuid();
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Función: record_test_result
-- Propósito: Guardar resultado en tabla global Y reportar a STDOUT
-- ============================================================================
CREATE OR REPLACE FUNCTION record_test_result(
    p_test_file TEXT,
    p_test_name TEXT,
    p_test_category TEXT,
    p_status TEXT,
    p_details TEXT
) RETURNS VOID AS $$
BEGIN
    -- Guardar en tabla
    INSERT INTO test_run_results (run_id, test_file, test_name, test_category, status, details)
    VALUES (get_test_run_id(), p_test_file, p_test_name, p_test_category, p_status, p_details);
    
    -- Reportar a STDOUT
    PERFORM report_test_result(p_status, p_test_name, p_details);
END;
$$ LANGUAGE plpgsql;

-- Mensaje de confirmación
DO $$
BEGIN
    RAISE NOTICE '✓ Test helpers loaded successfully';
END $$;
