import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from poa_core.classifier import ClassifierError, OllamaClassifier


class _Response:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(self.value).encode("utf-8")


class OllamaClassifierTests(unittest.TestCase):
    def test_rejects_non_loopback_endpoint(self):
        with self.assertRaisesRegex(ValueError, "loopback-only"):
            OllamaClassifier(base_url="http://192.0.2.10:11434")

    @patch("poa_core.classifier.urlopen")
    def test_sends_schema_and_returns_validated_local_classification(self, urlopen):
        urlopen.return_value = _Response(
            {
                "message": {
                    "content": json.dumps(
                        {
                            "task_type": "writing",
                            "complexity": "medium",
                            "confidence": 0.91,
                            "reason_codes": ["writing_intent"],
                        }
                    )
                }
            }
        )
        classifier = OllamaClassifier()

        result = classifier.classify("제안서 초안을 작성해줘", ("writing", "analysis"))

        self.assertEqual(result.task_type, "writing")
        self.assertEqual(result.source, "local_classifier")
        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "gemma3:1b")
        self.assertEqual(payload["options"]["temperature"], 0)
        self.assertIn("format", payload)
        self.assertIn("제안서 초안을 작성해줘", payload["messages"][1]["content"])

    @patch("poa_core.classifier.urlopen", side_effect=URLError("offline"))
    def test_reports_local_runtime_failure(self, _urlopen):
        classifier = OllamaClassifier()

        with self.assertRaisesRegex(ClassifierError, "Local classification failed"):
            classifier.classify("요청", ())

    @patch("poa_core.classifier.urlopen")
    def test_derives_capability_from_policy_allowlist(self, urlopen):
        urlopen.return_value = _Response(
            {
                "message": {
                    "content": json.dumps(
                        {
                            "task_type": "coding",
                            "complexity": "low",
                            "confidence": 0.99,
                            "reason_codes": [],
                        }
                    )
                }
            }
        )

        result = OllamaClassifier().classify("파이썬 오류를 고쳐줘", ("writing", "coding"))

        self.assertEqual(result.task_type, "coding")
        self.assertEqual(result.required_capabilities, ("coding",))


if __name__ == "__main__":
    unittest.main()
