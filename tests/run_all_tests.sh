#!/bin/bash
# ============================================================================
# Script para ejecutar todos los 52 tests de CapsuleCorp (Compliance Completo)
# ============================================================================
# Ejecutar: ./tests/run_all_tests.sh
# Última actualización: 2025-12-05 - Añadido test 52 (Mitigaciones de Seguridad)
# ============================================================================

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración de base de datos
DB_HOST="${DB_HOST:-localhost}"
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-capsule}"
DB_PASS="${DB_PASS:-Pretoriano.}"

# Directorio de tests
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_DIR="$SCRIPT_DIR"

# Contadores globales
TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_SKIPPED=0

# Archivos de test a ejecutar (en orden numérico)
TEST_FILES=(
    "01_test_integridad_referencial.sql"
    "02_test_funciones_cifrado.sql"
    "03_test_audit_inmutable.sql"
    "04_test_retencion_automatica.sql"
    "05_test_consentimientos.sql"
    "06_test_portabilidad.sql"
    "07_test_limitacion_tratamiento.sql"
    "08_test_derechos_arco.sql"
    "09_test_breach_notification.sql"
    "10_test_security_breaches.sql"
    "11_test_sensitive_data.sql"
    "12_test_retention_deletion.sql"
    "13_test_data_portability.sql"
    "14_test_dashboard_metrics.sql"
    "15_test_call_processing_consents.sql"
    "16_test_gdpr_right_to_erasure.sql"
    "17_test_performance_conversions.sql"
    "18_test_campaigns.sql"
    "19_test_dashboard_metrics_complete.sql"
    "20_test_kpi_metrics.sql"
    "21_test_rgpd_compliance.sql"
    "22_test_rls_isolation.sql"
    "23_test_pii_masking.sql"
    "24_test_performance_optimization.sql"
    "25_test_p0_lopdgdd_lgt.sql"
    "26_test_p1_ai_transparency.sql"
    "27_test_p2_ai_employee.sql"
    "28_test_p3_robinson.sql"
    "29_test_base_legal_validation.sql"
    "30_test_data_minimization.sql"
    "31_test_data_accuracy.sql"
    "32_test_minor_consent.sql"
    "33_test_rat_compliance.sql"
    "34_test_dpo_governance.sql"
    "35_test_ai_logs_retention.sql"
    "36_test_marketing_consent.sql"
    "37_test_ai_risk_management.sql"
    "38_test_ai_data_governance.sql"
    "39_test_ai_technical_docs.sql"
    "40_test_privacy_by_design.sql"
    "41_test_international_transfers.sql"
    "42_test_ai_accuracy_robustness.sql"
    "43_test_ai_quality_management.sql"
    "44_test_ai_right_to_explanation.sql"
    "45_test_information_layers.sql"
    "46_test_ai_deployer_obligations.sql"
    "47_test_nis2_cybersecurity.sql"
    "48_test_compliance_gaps.sql"
    "49_test_age_verification.sql"
    "50_test_audit_integrity_verification.sql"
    "51_test_blocked_data_rls_anonymization.sql"
    "52_test_security_mitigations.sql"
)

echo -e "${BLUE}=============================================="
echo "  CAPSULECORP - Suite de Tests de Compliance"
echo "=============================================="
echo -e "  Fecha: $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "  Base de datos: $DB_NAME@$DB_HOST"
echo -e "==============================================${NC}"
echo ""

# Función para ejecutar un test
run_test() {
    local test_file="$1"
    local test_path="$TESTS_DIR/$test_file"

    if [[ ! -f "$test_path" ]]; then
        echo -e "${YELLOW}[SKIP] $test_file - Archivo no encontrado${NC}"
        return 1
    fi

    echo -e "${BLUE}----------------------------------------------"
    echo -e "Ejecutando: $test_file"
    echo -e "----------------------------------------------${NC}"

    # Ejecutar test con configuración mejorada y capturar output
    local output
    local exit_code
    output=$(PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
        -v ON_ERROR_STOP=1 \
        -v test_run_id="$TEST_RUN_ID" \
        -f "$test_path" 2>&1) || exit_code=$?

    # Si hubo error SQL, marcar como fallo
    if [[ $exit_code -ne 0 ]]; then
        echo -e "${RED}[FAIL] $test_file: SQL ERROR${NC}"
        echo "$output" | tail -n 10
        TOTAL_FAILED=$((TOTAL_FAILED + 1))
        return 1
    fi

    # Contar PASS, FAIL y SKIP en el output
    local passed=$(echo "$output" | grep -c '\[PASS\]' || true)
    local failed=$(echo "$output" | grep -c '\[FAIL\]' || true)
    local skipped=$(echo "$output" | grep -c '\[SKIP\]' || true)

    local total=$((passed + failed + skipped))

    # Actualizar contadores globales
    TOTAL_PASSED=$((TOTAL_PASSED + passed))
    TOTAL_FAILED=$((TOTAL_FAILED + failed))
    TOTAL_SKIPPED=$((TOTAL_SKIPPED + skipped))

    # Mostrar resultado del test
    if [[ $failed -eq 0 ]]; then
        echo -e "${GREEN}[PASS] $test_file: $passed/$total tests passed${NC}"
        if [[ $skipped -gt 0 ]]; then
            echo -e "${YELLOW}       ($skipped skipped)${NC}"
        fi
    else
        echo -e "${RED}[FAIL] $test_file: $passed passed, $failed FAILED${NC}"
        # Mostrar detalles de los tests fallidos
        echo "$output" | grep '\[FAIL\]' | while read -r line; do
            echo -e "  ${RED}$line${NC}"
        done
    fi

    echo ""
    return $failed
}

# Generar UUID único para esta ejecución de tests
TEST_RUN_ID=$(uuidgen || echo "$(date +%s)-$$")

# Cargar helpers y fixtures ANTES de ejecutar tests
echo -e "${BLUE}Cargando helpers y fixtures...${NC}"
PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
    -f "$TESTS_DIR/00_test_helpers.sql" > /dev/null 2>&1 || {
    echo -e "${RED}Error cargando helpers${NC}"
    exit 1
}

PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
    -v test_run_id="$TEST_RUN_ID" \
    -f "$TESTS_DIR/00_seed_fixtures.sql" > /dev/null 2>&1 || {
    echo -e "${RED}Error cargando fixtures${NC}"
    exit 1
}

echo -e "${GREEN}✓ Helpers y fixtures cargados (run_id: $TEST_RUN_ID)${NC}"
echo ""

# Ejecutar todos los tests
echo -e "${BLUE}Ejecutando tests...${NC}"
echo ""

TESTS_WITH_FAILURES=()

for test_file in "${TEST_FILES[@]}"; do
    run_test "$test_file"
    if [[ $? -ne 0 ]]; then
        TESTS_WITH_FAILURES+=("$test_file")
    fi
done

# Calcular totales
TOTAL_TESTS=$((TOTAL_PASSED + TOTAL_FAILED + TOTAL_SKIPPED))

# Resumen final
echo -e "${BLUE}=============================================="
echo "  RESUMEN FINAL"
echo "==============================================${NC}"
echo ""
echo -e "  Total de tests:    $TOTAL_TESTS"
echo -e "  ${GREEN}Passed:            $TOTAL_PASSED${NC}"
if [[ $TOTAL_FAILED -gt 0 ]]; then
    echo -e "  ${RED}Failed:            $TOTAL_FAILED${NC}"
else
    echo -e "  Failed:            $TOTAL_FAILED"
fi
if [[ $TOTAL_SKIPPED -gt 0 ]]; then
    echo -e "  ${YELLOW}Skipped:           $TOTAL_SKIPPED${NC}"
else
    echo -e "  Skipped:           $TOTAL_SKIPPED"
fi
echo ""

# Calcular porcentaje de éxito
if [[ $TOTAL_TESTS -gt 0 ]]; then
    SUCCESS_RATE=$(awk "BEGIN {printf \"%.1f\", $TOTAL_PASSED * 100 / $TOTAL_TESTS}")
    echo -e "  Tasa de éxito:     ${SUCCESS_RATE}%"
fi
echo ""

# Estado final
if [[ $TOTAL_FAILED -eq 0 ]]; then
    echo -e "${GREEN}=============================================="
    echo "  TODOS LOS TESTS PASARON"
    echo "==============================================${NC}"
    exit 0
else
    echo -e "${RED}=============================================="
    echo "  ALGUNOS TESTS FALLARON"
    echo "==============================================${NC}"
    echo ""
    echo "Tests con fallos:"
    for test in "${TESTS_WITH_FAILURES[@]}"; do
        echo "  - $test"
    done
    exit 1
fi
