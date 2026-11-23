from dataclasses import dataclass
from typing import Any, Dict, Tuple


TASK_TYPES = {"research", "writing", "coding", "analysis", "general"}
COMPLEXITIES = {"low", "medium", "high", "unknown"}


class ContractError(ValueError):
    """Raised when policy or model output violates the local contract."""


@dataclass(frozen=True)
class TaskClassification:
    task_type: str
    required_capabilities: Tuple[str, ...]
    complexity: str
    confidence: float
    reason_codes: Tuple[str, ...]
    source: str = "local_classifier"

    @classmethod
    def from_model_output(
        cls, value: Any, allowed_capabilities: Tuple[str, ...]
    ) -> "TaskClassification":
        if not isinstance(value, dict):
            raise ContractError("Classifier output must be a JSON object.")

        required_fields = {
            "task_type",
            "complexity",
            "confidence",
            "reason_codes",
        }
        if set(value) != required_fields:
            raise ContractError("Classifier output fields do not match the schema.")

        task_type = value["task_type"]
        if not isinstance(task_type, str) or task_type not in TASK_TYPES:
            raise ContractError("Classifier returned an unsupported task_type.")

        complexity = value["complexity"]
        if not isinstance(complexity, str) or complexity not in COMPLEXITIES:
            raise ContractError("Classifier returned an unsupported complexity.")

        confidence = value["confidence"]
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not 0.0 <= float(confidence) <= 1.0
        ):
            raise ContractError("Classifier confidence must be a number from 0 to 1.")

        reason_codes = value["reason_codes"]
        if not isinstance(reason_codes, list) or not all(
            isinstance(item, str) and item for item in reason_codes
        ):
            raise ContractError("reason_codes must be a list of non-empty strings.")
        if len(reason_codes) > 8:
            raise ContractError("Classifier returned too many reason codes.")

        return cls(
            task_type=task_type,
            required_capabilities=(
                (task_type,) if task_type in allowed_capabilities else ()
            ),
            complexity=complexity,
            confidence=float(confidence),
            reason_codes=tuple(reason_codes),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type,
            "required_capabilities": list(self.required_capabilities),
            "complexity": self.complexity,
            "confidence": self.confidence,
            "reason_codes": list(self.reason_codes),
            "source": self.source,
        }


@dataclass(frozen=True)
class ProviderPolicy:
    provider_id: str
    capabilities: Tuple[str, ...]
    priority: int
    enabled: bool = True


@dataclass(frozen=True)
class RoutingPolicy:
    default_provider: str
    fallback_order: Tuple[str, ...]
    require_confirmation_below: float = 0.8


@dataclass(frozen=True)
class ProjectPolicy:
    project_id: str
    providers: Tuple[ProviderPolicy, ...]
    routing: RoutingPolicy

    @property
    def capabilities(self) -> Tuple[str, ...]:
        return tuple(
            sorted(
                {
                    capability
                    for provider in self.providers
                    for capability in provider.capabilities
                }
            )
        )


@dataclass(frozen=True)
class RoutePlan:
    provider_id: str
    candidate_ids: Tuple[str, ...]
    reason: str
    requires_confirmation: bool
    provider_availability: str = "unverified"
    execution_started: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "candidate_ids": list(self.candidate_ids),
            "reason": self.reason,
            "requires_confirmation": self.requires_confirmation,
            "provider_availability": self.provider_availability,
            "execution_started": self.execution_started,
        }
