import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

from poa_core.classifier import ClassifierError, OllamaClassifier
from poa_core.policy import PolicyError, load_policy
from poa_core.router import RoutingError, plan_route


def _classifier_from_args(args: argparse.Namespace) -> OllamaClassifier:
    return OllamaClassifier(
        base_url=args.ollama_url,
        model=args.model,
        timeout=args.timeout,
    )


def _read_request_text() -> str:
    if sys.stdin.isatty():
        return input("요청을 입력하세요: ").strip()
    return sys.stdin.read().strip()


def _doctor(args: argparse.Namespace) -> int:
    classifier = _classifier_from_args(args)
    models = classifier.installed_models()
    result = {
        "ollama": "ready",
        "endpoint": classifier.base_url,
        "configured_model": classifier.model,
        "model_installed": classifier.model in models,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if classifier.model not in models:
        print(
            "모델이 설치되어 있지 않습니다. `ollama pull {}`을 실행하세요.".format(
                classifier.model
            ),
            file=sys.stderr,
        )
        return 1
    return 0


def _route(args: argparse.Namespace) -> int:
    text = _read_request_text()
    if not text:
        raise ValueError("요청 내용이 비어 있습니다.")

    policy = load_policy(Path(args.policy))
    classifier = _classifier_from_args(args)
    classification = classifier.classify(text, policy.capabilities)
    route_plan = plan_route(policy, classification, args.provider)

    result = {
        "project_id": policy.project_id,
        "classification": classification.to_dict(),
        "route_plan": route_plan.to_dict(),
        "notice": (
            "계획만 생성했습니다. provider 호출은 아직 구현되지 않았습니다."
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="poa",
        description="개인용 로컬 AI 라우팅 의사결정 도구",
    )
    parser.add_argument(
        "--ollama-url",
        default=os.environ.get("POA_OLLAMA_URL", "http://127.0.0.1:11434"),
        help="loopback Ollama base URL (default: http://127.0.0.1:11434)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("POA_DECISION_MODEL", "gemma3:1b"),
        help="installed local decision model (default: gemma3:1b)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=12.0,
        help="local inference timeout in seconds",
    )

    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="check Ollama and local model")
    doctor.set_defaults(handler=_doctor)

    route = commands.add_parser(
        "route", help="classify a request and print a policy-only route plan"
    )
    route.add_argument("--policy", required=True, help="project policy YAML path")
    route.add_argument(
        "--provider",
        help="explicit provider ID; must be enabled and support the task",
    )
    route.set_defaults(handler=_route)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (ClassifierError, PolicyError, RoutingError, ValueError) as exc:
        print("poa: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
