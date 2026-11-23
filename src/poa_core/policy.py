from pathlib import Path
from typing import Any, List, Mapping, Tuple

import yaml

from poa_core.models import (
    ProjectPolicy,
    ProviderPolicy,
    RoutingPolicy,
)


class PolicyError(ValueError):
    """Raised when a project policy is missing or invalid."""


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise PolicyError("{} must be a mapping.".format(name))
    return value


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PolicyError("{} must be a non-empty string.".format(name))
    return value.strip()


def _string_list(value: Any, name: str) -> Tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise PolicyError("{} must be a list of non-empty strings.".format(name))
    if len(set(value)) != len(value):
        raise PolicyError("{} must not contain duplicates.".format(name))
    return tuple(item.strip() for item in value)


def load_policy(path: Path) -> ProjectPolicy:
    try:
        with path.open("r", encoding="utf-8") as policy_file:
            document = yaml.safe_load(policy_file)
    except OSError as exc:
        raise PolicyError("Cannot read policy file: {}".format(path)) from exc
    except yaml.YAMLError as exc:
        raise PolicyError("Policy file is not valid YAML.") from exc

    root = _mapping(document, "policy")
    if root.get("schema_version") != 1:
        raise PolicyError("schema_version must be 1.")
    project_id = _string(root.get("project_id"), "project_id")

    raw_providers = root.get("providers")
    if not isinstance(raw_providers, list) or not raw_providers:
        raise PolicyError("providers must be a non-empty list.")

    providers: List[ProviderPolicy] = []
    seen_ids = set()
    for index, raw_provider in enumerate(raw_providers):
        provider_data = _mapping(raw_provider, "providers[{}]".format(index))
        provider_id = _string(
            provider_data.get("id"), "providers[{}].id".format(index)
        )
        if provider_id in seen_ids:
            raise PolicyError("Provider IDs must be unique.")
        seen_ids.add(provider_id)

        capabilities = _string_list(
            provider_data.get("capabilities"),
            "providers[{}].capabilities".format(index),
        )
        priority = provider_data.get("priority")
        if isinstance(priority, bool) or not isinstance(priority, int):
            raise PolicyError(
                "providers[{}].priority must be an integer.".format(index)
            )
        enabled = provider_data.get("enabled", True)
        if not isinstance(enabled, bool):
            raise PolicyError(
                "providers[{}].enabled must be a boolean.".format(index)
            )
        providers.append(
            ProviderPolicy(
                provider_id=provider_id,
                capabilities=capabilities,
                priority=priority,
                enabled=enabled,
            )
        )

    routing_data = _mapping(root.get("routing"), "routing")
    default_provider = _string(routing_data.get("default"), "routing.default")
    fallback_order = _string_list(
        routing_data.get("fallback_order", []), "routing.fallback_order"
    )
    threshold = routing_data.get("require_confirmation_below", 0.8)
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0.0 <= float(threshold) <= 1.0
    ):
        raise PolicyError(
            "routing.require_confirmation_below must be between 0 and 1."
        )

    provider_ids = {provider.provider_id for provider in providers}
    referenced_ids = {default_provider}.union(fallback_order)
    if not referenced_ids.issubset(provider_ids):
        raise PolicyError("routing references an unregistered provider.")

    return ProjectPolicy(
        project_id=project_id,
        providers=tuple(providers),
        routing=RoutingPolicy(
            default_provider=default_provider,
            fallback_order=fallback_order,
            require_confirmation_below=float(threshold),
        ),
    )
