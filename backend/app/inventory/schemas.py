"""M1.1 input contracts and explicit Resource serialization."""

import re
from datetime import timezone
from uuid import UUID


RESOURCE_TYPES = frozenset({
    "physical_host", "virtual_machine", "container", "network_device",
    "storage_device", "iot_device", "service", "cluster",
})
ADMINISTRATIVE_STATES = frozenset({"active", "maintenance", "disabled", "archived"})
EDITABLE_STATES = ADMINISTRATIVE_STATES - {"archived"}


class InventoryValidationError(ValueError):
    pass


def validate_creation(payload):
    if not isinstance(payload, dict):
        raise InventoryValidationError("O corpo JSON deve ser um objeto.")
    if set(payload) - {"resource_type", "display_name", "description", "attributes", "administrative_state"}:
        raise InventoryValidationError("O corpo contém campos não permitidos.")
    resource_type = payload.get("resource_type")
    if not isinstance(resource_type, str) or resource_type not in RESOURCE_TYPES:
        raise InventoryValidationError("resource_type inválido.")
    name = payload.get("display_name")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 255:
        raise InventoryValidationError("display_name deve conter entre 1 e 255 caracteres.")
    description = payload.get("description")
    if description is not None and not isinstance(description, str):
        raise InventoryValidationError("description deve ser texto ou null.")
    attributes = payload.get("attributes", {})
    if not isinstance(attributes, dict) or attributes:
        raise InventoryValidationError("attributes apenas admite um objeto vazio nesta fase.")
    result = {"resource_type": resource_type, "display_name": name.strip(),
              "description": description, "attributes": {}}
    if "administrative_state" in payload:
        state = payload["administrative_state"]
        if not isinstance(state, str) or state not in EDITABLE_STATES:
            raise InventoryValidationError("Estado administrativo inválido; arquivo não permitido.")
        result["administrative_state"] = state
    return result


def validate_update(payload):
    if not isinstance(payload, dict) or set(payload) != {
        "resource_type", "display_name", "description", "administrative_state", "row_version",
    }:
        raise InventoryValidationError("Indique os quatro campos editáveis e a versão do registo.")
    version = payload["row_version"]
    if type(version) is not int or not 1 <= version < 2147483647:
        raise InventoryValidationError("Versão do registo inválida.")
    data = validate_creation({key: value for key, value in payload.items() if key != "row_version"})
    data.pop("attributes")
    return {**data, "row_version": version}


def validate_query(args):
    allowed = {"page", "per_page", "resource_type", "administrative_state"}
    if set(args) - allowed or any(len(args.getlist(key)) != 1 for key in args):
        raise InventoryValidationError("Parâmetros de consulta inválidos.")
    result = {}
    for key, default, maximum in (("page", "1", 2**31 - 1), ("per_page", "50", 100)):
        raw = args.get(key, default)
        if (not isinstance(raw, str) or len(raw) > 10
                or not re.fullmatch(r"[1-9][0-9]*", raw) or int(raw) > maximum):
            raise InventoryValidationError("Paginação inválida.")
        result[key] = int(raw)
    for key, catalogue in (("resource_type", RESOURCE_TYPES),
                           ("administrative_state", ADMINISTRATIVE_STATES)):
        value = args.get(key)
        if value is not None and value not in catalogue:
            raise InventoryValidationError("Filtro inválido.")
        result[key] = value
    return result


def validate_resource_id(value):
    try:
        return UUID(value)
    except (ValueError, TypeError, AttributeError):
        raise InventoryValidationError("Identificador de recurso inválido.") from None


def _timestamp(value):
    if value is None:
        return None
    if value.tzinfo is None:
        raise ValueError("Resource timestamp must have timezone")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def serialize_resource(resource):
    return {
        "id": str(resource.id), "resource_type": resource.resource_type,
        "display_name": resource.display_name, "description": resource.description,
        "administrative_state": resource.administrative_state,
        "attributes": resource.attributes, "created_at": _timestamp(resource.created_at),
        "updated_at": _timestamp(resource.updated_at),
        "archived_at": _timestamp(resource.archived_at), "row_version": resource.row_version,
    }
