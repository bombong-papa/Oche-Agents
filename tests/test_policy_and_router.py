import tempfile
import unittest
from pathlib import Path

from poa_core.models import TaskClassification
from poa_core.policy import PolicyError, load_policy
from poa_core.router import RoutingError, plan_route


POLICY = """\
schema_version: 1
project_id: demo
providers:
  - id: default-writer
    capabilities: [writing, analysis]
    priority: 10
  - id: researcher
    capabilities: [research, analysis]
    priority: 20
routing:
  default: default-writer
  fallback_order: [researcher]
  require_confirmation_below: 0.8
"""


def load_text_policy(text):
    handle = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False)
    try:
        handle.write(text)
        handle.close()
        return load_policy(Path(handle.name))
    finally:
        Path(handle.name).unlink(missing_ok=True)


class PolicyAndRouterTests(unittest.TestCase):
    def test_selects_policy_default_when_capable(self):
        policy = load_text_policy(POLICY)
        classification = TaskClassification(
            task_type="writing",
            required_capabilities=("writing",),
            complexity="medium",
            confidence=0.9,
            reason_codes=("writing_intent",),
        )

        result = plan_route(policy, classification)

        self.assertEqual(result.provider_id, "default-writer")
        self.assertEqual(result.candidate_ids, ("default-writer",))
        self.assertFalse(result.requires_confirmation)
        self.assertFalse(result.execution_started)
        self.assertEqual(result.provider_availability, "unverified")

    def test_uses_capability_match_when_default_cannot_handle_task(self):
        policy = load_text_policy(POLICY)
        classification = TaskClassification(
            task_type="research",
            required_capabilities=("research",),
            complexity="medium",
            confidence=0.9,
            reason_codes=("research_intent",),
        )

        result = plan_route(policy, classification)

        self.assertEqual(result.provider_id, "researcher")
        self.assertEqual(result.reason, "capability_match_priority")

    def test_requires_confirmation_for_low_confidence(self):
        policy = load_text_policy(POLICY)
        classification = TaskClassification(
            task_type="general",
            required_capabilities=("analysis",),
            complexity="unknown",
            confidence=0.4,
            reason_codes=(),
        )

        result = plan_route(policy, classification)

        self.assertTrue(result.requires_confirmation)

    def test_rejects_user_selected_provider_without_required_capability(self):
        policy = load_text_policy(POLICY)
        classification = TaskClassification(
            task_type="research",
            required_capabilities=("research",),
            complexity="low",
            confidence=0.95,
            reason_codes=(),
        )

        with self.assertRaisesRegex(RoutingError, "lacks required capabilities"):
            plan_route(policy, classification, "default-writer")

    def test_rejects_policy_with_unregistered_fallback(self):
        invalid_policy = POLICY.replace(
            "fallback_order: [researcher]", "fallback_order: [missing]"
        )

        with self.assertRaisesRegex(PolicyError, "unregistered provider"):
            load_text_policy(invalid_policy)


if __name__ == "__main__":
    unittest.main()
