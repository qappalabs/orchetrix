from Business_Logic.audit.engine import CORPUS_RULES, RULES, register_corpus, run_audit
from Business_Logic.audit.models import Finding, Severity


def test_empty_resources():
    assert run_audit([]) == []


def test_malformed_resource_does_not_raise():
    results = run_audit([{}])
    assert isinstance(results, list)


def test_rule_registry_not_empty():
    assert len(RULES) >= 5


def test_pod_and_deployment_produce_same_memory_finding():
    bad_container = {
        "name": "web",
        "image": "nginx:1.21",
    }

    pod = {
        "kind": "Pod",
        "metadata": {"name": "my-pod", "namespace": "default"},
        "spec": {"containers": [bad_container]},
    }

    deployment = {
        "kind": "Deployment",
        "metadata": {"name": "my-deploy", "namespace": "default"},
        "spec": {
            "template": {
                "spec": {"containers": [bad_container]},
            }
        },
    }

    pod_findings = run_audit([pod])
    deploy_findings = run_audit([deployment])

    pod_memory = [
        f for f in pod_findings if f.rule_id == "no-memory-limit"
    ]
    deploy_memory = [
        f for f in deploy_findings if f.rule_id == "no-memory-limit"
    ]

    assert len(pod_memory) >= 1
    assert len(deploy_memory) >= 1


def test_corpus_rule_runs_over_all_resources():
    @register_corpus
    def _corpus_rule(resources):
        if len(resources) >= 2:
            return [Finding(rule_id="test-corpus", severity=Severity.WARNING, kind="", namespace="", name="", message="")]
        return []

    try:
        results = run_audit([
            {"kind": "Pod", "metadata": {"name": "a"}},
            {"kind": "Pod", "metadata": {"name": "b"}},
        ])
        assert any(f.rule_id == "test-corpus" for f in results)

        results_empty = run_audit([])
        assert not any(f.rule_id == "test-corpus" for f in results_empty)
    finally:
        CORPUS_RULES.remove(_corpus_rule)
