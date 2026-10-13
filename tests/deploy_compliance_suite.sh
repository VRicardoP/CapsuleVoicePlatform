#!/bin/bash
# ============================================================================
# Script de Deployment: Tests de Compliance + Mejoras Schema
# ============================================================================
# Uso: sudo ./deploy_compliance_suite.sh
# ============================================================================

set -e  # Exit on error

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-sfera}"
DB_PASS="${DB_PASS:-Pretoriano.}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}SferaAI Compliance Suite - Deployment Script${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

# ============================================================================
# PASO 1: Verificar Conexión PostgreSQL
# ============================================================================

echo -e "${YELLOW}[1/5] Verificando conexión a PostgreSQL...${NC}"

if PGPASSWORD="$DB_PASS" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Conexión exitosa a PostgreSQL${NC}"
    PG_VERSION=$(PGPASSWORD="$DB_PASS" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT version();" | head -1)
    echo -e "  Versión: $PG_VERSION"
else
    echo -e "${RED}✗ Error: No se puede conectar a PostgreSQL${NC}"
    echo -e "${YELLOW}Intentando con autenticación sudo...${NC}"
    
    if sudo -u postgres psql -d "$DB_NAME" -c "SELECT version();" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Conexión con sudo exitosa${NC}"
        DB_USER="postgres"
        USE_SUDO=true
    else
        echo -e "${RED}✗ Error: No se pudo conectar con ningún método${NC}"
        echo ""
        echo "Soluciones:"
        echo "1. Modificar /etc/postgresql/*/main/pg_hba.conf:"
        echo "   local   all   postgres   md5"
        echo "2. Reiniciar PostgreSQL: sudo systemctl restart postgresql"
        echo "3. Configurar variables: export DB_USER=postgres DB_PASS=Pretoriano."
        exit 1
    fi
fi

echo ""

# ============================================================================
# PASO 2: Backup de Base de Datos
# ============================================================================

echo -e "${YELLOW}[2/5] Creando backup de seguridad...${NC}"

BACKUP_FILE="$SCRIPT_DIR/../backups/sfera_backup_$(date +%Y%m%d_%H%M%S).sql"
mkdir -p "$(dirname "$BACKUP_FILE")"

if [ "$USE_SUDO" = true ]; then
    sudo -u postgres pg_dump "$DB_NAME" > "$BACKUP_FILE"
else
    PGPASSWORD="$DB_PASS" pg_dump -h localhost -U "$DB_USER" "$DB_NAME" > "$BACKUP_FILE"
fi

if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✓ Backup creado: $BACKUP_FILE ($BACKUP_SIZE)${NC}"
else
    echo -e "${RED}✗ Error al crear backup${NC}"
    exit 1
fi

echo ""

# ============================================================================
# PASO 3: Aplicar Mejoras al Schema
# ============================================================================

echo -e "${YELLOW}[3/5] Aplicando mejoras al schema...${NC}"

SCHEMA_IMPROVEMENTS="../schema_improvements_phase2.sql"

if [ ! -f "$SCHEMA_IMPROVEMENTS" ]; then
    echo -e "${RED}✗ Error: No se encuentra $SCHEMA_IMPROVEMENTS${NC}"
    exit 1
fi

if [ "$USE_SUDO" = true ]; then
    sudo -u postgres psql -d "$DB_NAME" -f "$SCHEMA_IMPROVEMENTS" > /tmp/schema_apply.log 2>&1
else
    PGPASSWORD="$DB_PASS" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -f "$SCHEMA_IMPROVEMENTS" > /tmp/schema_apply.log 2>&1
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Mejoras al schema aplicadas correctamente${NC}"
    echo -e "  Log: /tmp/schema_apply.log"
else
    echo -e "${RED}✗ Error al aplicar mejoras${NC}"
    echo -e "${YELLOW}Log de errores:${NC}"
    tail -20 /tmp/schema_apply.log
    exit 1
fi

echo ""

# ============================================================================
# PASO 4: Ejecutar Tests de Compliance (29-36)
# ============================================================================

echo -e "${YELLOW}[4/5] Ejecutando nuevos tests de compliance...${NC}"

TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

for i in {29..36}; do
    TEST_FILE="${i}_test"*.sql
    
    if [ ! -f "$TEST_FILE" ]; then
        echo -e "${YELLOW}  ⊘ Test $i no encontrado: $TEST_FILE${NC}"
        continue
    fi
    
    echo -ne "  Testing $i: $(basename "$TEST_FILE")... "
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if [ "$USE_SUDO" = true ]; then
        sudo -u postgres psql -d "$DB_NAME" -f "$TEST_FILE" > "/tmp/test_${i}.log" 2>&1
    else
        PGPASSWORD="$DB_PASS" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -f "$TEST_FILE" > "/tmp/test_${i}.log" 2>&1
    fi
    
    if [ $? -eq 0 ]; then
        # Contar PASS/FAIL en el log
        PASS_COUNT=$(grep -c "\[PASS\]" "/tmp/test_${i}.log" 2>/dev/null || echo "0")
        FAIL_COUNT=$(grep -c "\[FAIL\]" "/tmp/test_${i}.log" 2>/dev/null || echo "0")
        
        if [ "$FAIL_COUNT" -eq 0 ]; then
            echo -e "${GREEN}✓ PASS${NC} ($PASS_COUNT checks)"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo -e "${YELLOW}⚠ PASS with failures${NC} ($PASS_COUNT ok, $FAIL_COUNT failed)"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    else
        echo -e "${RED}✗ ERROR${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo -e "${RED}     Detalles:${NC}"
        tail -5 "/tmp/test_${i}.log" | sed 's/^/     /'
    fi
done

echo ""
echo -e "${BLUE}Resumen Tests Nuevos (29-36):${NC}"
echo -e "  Total: $TOTAL_TESTS"
echo -e "  ${GREEN}Exitosos: $PASSED_TESTS${NC}"
echo -e "  ${YELLOW}Con fallos: $FAILED_TESTS${NC}"

echo ""

# ============================================================================
# PASO 5: Ejecutar Suite Completa (Opcional)
# ============================================================================

echo -e "${YELLOW}[5/5] ¿Ejecutar suite completa de 36 tests?${NC}"
echo -ne "  Esto puede tomar 2-3 minutos. Continuar? (y/N): "
read -r RESPONSE

if [[ "$RESPONSE" =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Ejecutando suite completa...${NC}"
    
    if [ -f "./run_all_tests.sh" ]; then
        chmod +x ./run_all_tests.sh
        
        if [ "$USE_SUDO" = true ]; then
            sudo -u postgres ./run_all_tests.sh > /tmp/full_suite.log 2>&1
        else
            export DB_USER DB_NAME DB_PASS
            ./run_all_tests.sh > /tmp/full_suite.log 2>&1
        fi
        
        echo -e "${GREEN}✓ Suite completa ejecutada${NC}"
        echo -e "  Log: /tmp/full_suite.log"
        
        # Mostrar resumen
        echo ""
        grep -E "Total|Passed|Failed" /tmp/full_suite.log | tail -10
    else
        echo -e "${YELLOW}  ⊘ run_all_tests.sh no encontrado${NC}"
    fi
else
    echo -e "${YELLOW}  ⊘ Suite completa omitida${NC}"
fi

# ============================================================================
# RESUMEN FINAL
# ============================================================================

echo ""
echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}Deployment Completado${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""
echo -e "${GREEN}✓ Backup creado:${NC} $BACKUP_FILE"
echo -e "${GREEN}✓ Schema mejorado${NC}"
echo -e "${GREEN}✓ Tests 29-36 ejecutados:${NC} $PASSED_TESTS/$TOTAL_TESTS exitosos"
echo ""
echo -e "${YELLOW}Archivos de log:${NC}"
echo "  - Schema: /tmp/schema_apply.log"
echo "  - Tests: /tmp/test_29.log ... /tmp/test_36.log"
if [ -f "/tmp/full_suite.log" ]; then
    echo "  - Suite completa: /tmp/full_suite.log"
fi
echo ""

if [ "$FAILED_TESTS" -gt 0 ]; then
    echo -e "${YELLOW}⚠ ATENCIÓN: $FAILED_TESTS tests con fallos${NC}"
    echo "  Revisa los logs en /tmp/test_*.log para detalles"
    echo ""
    exit 1
else
    echo -e "${GREEN}✓ Todos los tests pasaron correctamente${NC}"
    echo ""
    exit 0
fi
