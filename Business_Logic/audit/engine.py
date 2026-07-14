from Business_Logic.audit.models import Finding, Severity


def meta(resource: dict) -> tuple[str, str, str]:
    kind = resource.get("kind", "")
    metadata = resource.get("metadata", {})
    name = metadata.get("name", "") if metadata else ""
    namespace = metadata.get("namespace", "") if metadata else ""
    return kind, namespace, name


def pod_spec(resource: dict) -> dict:
    if "template" in resource.get("spec", {}):
        template_spec = resource["spec"]["template"].get("spec")
        if template_spec is not None:
            return template_spec
    return resource.get("spec", {})


def containers(resource: dict) -> list[dict]:
    return pod_spec(resource).get("containers", []) or []


def make_finding(
    resource: dict, rule_id: str, severity: Severity, message: str
) -> Finding:
    kind, namespace, name = meta(resource)
    return Finding(
        rule_id=rule_id,
        severity=severity,
        kind=kind,
        namespace=namespace,
        name=name,
        message=message,
    )


RULES: list = []
CORPUS_RULES: list = []


def register(fn):
    RULES.append(fn)
    return fn


def register_corpus(fn):
    CORPUS_RULES.append(fn)
    return fn


def run_audit(resources: list[dict]) -> list[Finding]:
    results = []
    for resource in resources:
        for rule in RULES:
            try:
                results.extend(rule(resource))
            except Exception:
                pass
    for crule in CORPUS_RULES:
        try:
            results.extend(crule(resources))
        except Exception:
            pass
    return results


from . import rules  # noqa: E402, F811
