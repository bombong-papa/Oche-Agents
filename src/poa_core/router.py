from typing import List, Optional, Tuple

from poa_core.models import (
    ProjectPolicy,
    ProviderPolicy,
    RoutePlan,
    TaskClassification,
)


class RoutingError(ValueError):
    """Raised when no policy-compliant route can be planned."""


def plan_route(
    policy: ProjectPolicy,
    classification: TaskClassification,
    requested_provider: Optional[str] = None,
) -> RoutePlan:
    providers = {provider.provider_id: provider for provider in policy.providers}
    required = set(classification.required_capabilities)

    def supports(provider: ProviderPolicy) -> bool:
        return provider.enabled and required.issubset(set(provider.capabilities))

    if requested_provider is not None:
        provider = providers.get(requested_provider)
        if provider is None:
            raise RoutingError("Requested provider is not registered in this policy.")
        if not supports(provider):
            raise RoutingError(
                "Requested provider is disabled or lacks required capabilities."
            )
        return RoutePlan(
            provider_id=provider.provider_id,
            candidate_ids=(provider.provider_id,),
            reason="explicit_user_selection",
            requires_confirmation=False,
        )

    eligible = [provider for provider in policy.providers if supports(provider)]
    if not eligible:
        raise RoutingError("No enabled provider supports the classified task.")

    eligible.sort(key=lambda provider: (provider.priority, provider.provider_id))
    by_id = {provider.provider_id: provider for provider in eligible}
    preferred = by_id.get(policy.routing.default_provider)
    if preferred is None:
        preferred = eligible[0]
        reason = "capability_match_priority"
    else:
        reason = "policy_default"

    ordered_candidates = [preferred.provider_id]
    for provider_id in policy.routing.fallback_order:
        if provider_id in by_id and provider_id not in ordered_candidates:
            ordered_candidates.append(provider_id)
    for provider in eligible:
        if provider.provider_id not in ordered_candidates:
            ordered_candidates.append(provider.provider_id)

    return RoutePlan(
        provider_id=preferred.provider_id,
        candidate_ids=tuple(ordered_candidates),
        reason=reason,
        requires_confirmation=(
            classification.confidence
            < policy.routing.require_confirmation_below
        ),
    )
