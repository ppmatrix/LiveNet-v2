#!/usr/bin/env bash
set -euo pipefail

echo "BLOQUEADO: executor F0.66C antigo desativado; utilizar f066c_admin_psql.sh." >&2
exit 3

EXPECTED_ID="8d005f6c658e7e0a5d6512eb5333c6c936c19b227f1e5d51f02ce3cf2c770ce3"
EXPECTED_PROJECT="livenetv2-f066c"
EXPECTED_NETWORK="livenetv2-f066c_f066c_backend"
EXPECTED_IMAGE="postgres:16-alpine"
EXPECTED_DATABASE="livenet_f0_test"

MODE="${1:-preflight}"

if [[ "$#" -gt 1 ]]; then
    echo "Uso: $0 [preflight|--execute-transfer|--execute-rollback|--execute-grant-app|--execute-revoke-app|--execute-revoke-public-functions|--execute-restore-public-functions]" >&2
    exit 2
fi

case "$MODE" in
    preflight|--execute-transfer|--execute-rollback|--execute-grant-app|--execute-revoke-app|--execute-revoke-public-functions|--execute-restore-public-functions) ;;
    *)
        echo "ERRO: operacao nao autorizada: $MODE" >&2
        exit 2
        ;;
esac

cd "$(dirname "$0")/../.."

container_id="$(
    docker compose -f compose.f066c-test.yaml ps -q db
)"

if [[ -z "$container_id" || "$container_id" != "$EXPECTED_ID" ]]; then
    echo "ERRO: ID do contentor nao corresponde ao validado." >&2
    exit 1
fi

inspect_format='{{.State.Running}}|{{.State.Health.Status}}|{{index .Config.Labels "com.docker.compose.project"}}|{{index .Config.Labels "com.docker.compose.service"}}|{{.Config.Image}}'

details="$(docker inspect "$container_id" --format "$inspect_format")"
IFS='|' read -r running health project service image <<< "$details"

if [[ "$running" != "true" ||
      "$health" != "healthy" ||
      "$project" != "$EXPECTED_PROJECT" ||
      "$service" != "db" ||
      "$image" != "$EXPECTED_IMAGE" ]]; then
    echo "ERRO: estado ou identidade do contentor invalido." >&2
    exit 1
fi

network="$(
    docker inspect "$container_id" \
      --format '{{range $name, $_ := .NetworkSettings.Networks}}{{$name}}{{end}}'
)"

if [[ "$network" != "$EXPECTED_NETWORK" ]]; then
    echo "ERRO: rede Docker inesperada." >&2
    exit 1
fi

database="$(
    docker exec "$container_id" \
      psql -X -At -v ON_ERROR_STOP=1 \
      -U livenet -d "$EXPECTED_DATABASE" \
      -c 'SELECT current_database()'
)"

if [[ "$database" != "$EXPECTED_DATABASE" ]]; then
    echo "ERRO: base de dados inesperada." >&2
    exit 1
fi

echo "PASS: identidade Docker, rede e base de dados validadas."

if [[ "$MODE" == "preflight" ]]; then
    echo "Modo preflight: nenhuma operacao administrativa executada."
    exit 0
fi

case "$MODE" in
    --execute-transfer)
        sql_file="scripts/postgres/f066c_transfer_ownership.sql"
        operation="transferencia de propriedade"
        ;;
    --execute-rollback)
        sql_file="scripts/postgres/f066c_rollback_ownership.sql"
        operation="rollback de propriedade"
        ;;
    --execute-grant-app)
        sql_file="scripts/postgres/f066c_grant_app_privileges.sql"
        operation="concessao de privilegios aplicacionais"
        ;;
    --execute-revoke-app)
        sql_file="scripts/postgres/f066c_revoke_app_privileges.sql"
        operation="reversao de privilegios aplicacionais"
        ;;
    --execute-revoke-public-functions)
        sql_file="scripts/postgres/f066c_revoke_public_function_execute.sql"
        operation="revogacao de EXECUTE a PUBLIC nas funcoes"
        ;;
    --execute-restore-public-functions)
        sql_file="scripts/postgres/f066c_restore_public_function_execute.sql"
        operation="restauro de EXECUTE a PUBLIC nas funcoes"
        ;;
esac

echo "Operacao autorizada: $operation"
echo "SQL fixo: $sql_file"

docker exec -i "$container_id" \
    psql -X -v ON_ERROR_STOP=1 \
    -U livenet -d "$EXPECTED_DATABASE" \
    < "$sql_file"
