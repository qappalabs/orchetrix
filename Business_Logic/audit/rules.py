from Business_Logic.audit.engine import (
    RULES,
    containers,
    make_finding,
    meta,
    pod_spec,
    register,
    register_corpus,
)
from Business_Logic.audit.models import Finding, Severity


# apiVersion -> {Kind: "message"} for kinds removed/deprecated in that group/version.
DEPRECATED_APIS = {
    "extensions/v1beta1": {
        "Deployment": "use apps/v1", "DaemonSet": "use apps/v1",
        "ReplicaSet": "use apps/v1", "Ingress": "use networking.k8s.io/v1",
        "NetworkPolicy": "use networking.k8s.io/v1",
    },
    "apps/v1beta1": {"Deployment": "use apps/v1", "StatefulSet": "use apps/v1"},
    "apps/v1beta2": {"Deployment": "use apps/v1", "StatefulSet": "use apps/v1"},
    "networking.k8s.io/v1beta1": {"Ingress": "use networking.k8s.io/v1"},
    "policy/v1beta1": {"PodDisruptionBudget": "use policy/v1"},
    "batch/v1beta1": {"CronJob": "use batch/v1"},
}


@register
def no_memory_limit(resource: dict) -> list[Finding]:
    findings = []
    for container in containers(resource):
        limits = container.get("resources", {}).get("limits", {})
        if not limits.get("memory"):
            name = container.get("name", "?")
            findings.append(
                make_finding(
                    resource,
                    "no-memory-limit",
                    Severity.WARNING,
                    f"container '{name}' has no memory limit",
                )
            )
    return findings


@register
def image_latest(resource: dict) -> list[Finding]:
    findings = []
    for container in containers(resource):
        image = container.get("image", "")
        last_slash = image.rfind("/")
        if last_slash >= 0:
            image_tag_part = image[last_slash + 1:]
        else:
            image_tag_part = image
        if ":" in image_tag_part:
            tag = image_tag_part.rsplit(":", 1)[1]
        else:
            tag = ""
        if not tag or tag == "latest":
            name = container.get("name", "?")
            findings.append(
                make_finding(
                    resource,
                    "image-latest",
                    Severity.WARNING,
                    f"container '{name}' uses mutable image tag: {image or '<none>'}",
                )
            )
    return findings


@register
def runs_as_root(resource: dict) -> list[Finding]:
    findings = []
    pod_sec = pod_spec(resource).get("securityContext", {})
    if pod_sec.get("runAsNonRoot") is True:
        return findings
    for container in containers(resource):
        sec = container.get("securityContext", {})
        if sec.get("runAsNonRoot") is not True:
            name = container.get("name", "?")
            findings.append(
                make_finding(
                    resource,
                    "runs-as-root",
                    Severity.CRITICAL,
                    f"container '{name}' may run as root (no runAsNonRoot=true)",
                )
            )
    return findings


@register
def privileged_container(resource: dict) -> list[Finding]:
    findings = []
    for container in containers(resource):
        sec = container.get("securityContext", {})
        if sec.get("privileged") is True:
            name = container.get("name", "?")
            findings.append(
                make_finding(
                    resource,
                    "privileged",
                    Severity.CRITICAL,
                    f"container '{name}' is privileged",
                )
            )
    return findings


@register
def no_liveness_probe(resource: dict) -> list[Finding]:
    findings = []
    for container in containers(resource):
        if not container.get("livenessProbe"):
            name = container.get("name", "?")
            findings.append(
                make_finding(
                    resource,
                    "no-liveness-probe",
                    Severity.WARNING,
                    f"container '{name}' has no liveness probe",
                )
            )
    return findings


@register
def no_cpu_request(resource: dict) -> list[Finding]:
    findings = []
    for container in containers(resource):
        cpu = container.get("resources", {}).get("requests", {}).get("cpu")
        if not cpu:
            name = container.get("name", "?")
            findings.append(
                make_finding(
                    resource,
                    "no-cpu-request",
                    Severity.WARNING,
                    f"container '{name}' has no CPU request",
                )
            )
    return findings


@register
def host_network(resource: dict) -> list[Finding]:
    findings = []
    if pod_spec(resource).get("hostNetwork") is True:
        findings.append(
            make_finding(
                resource,
                "host-network",
                Severity.CRITICAL,
                "pod uses hostNetwork (shares the node's network namespace)",
            )
        )
    return findings


@register
def allow_privilege_escalation(resource: dict) -> list[Finding]:
    findings = []
    for container in containers(resource):
        sec = container.get("securityContext", {})
        if sec.get("allowPrivilegeEscalation") is not False:
            name = container.get("name", "?")
            findings.append(
                make_finding(
                    resource,
                    "allow-privilege-escalation",
                    Severity.WARNING,
                    f"container '{name}' allows privilege escalation (set allowPrivilegeEscalation: false)",
                )
            )
    return findings


@register
def read_only_root_fs(resource: dict) -> list[Finding]:
    findings = []
    for container in containers(resource):
        sec = container.get("securityContext", {})
        if sec.get("readOnlyRootFilesystem") is not True:
            name = container.get("name", "?")
            findings.append(
                make_finding(
                    resource,
                    "read-only-root-fs",
                    Severity.WARNING,
                    f"container '{name}' has a writable root filesystem",
                )
            )
    return findings


@register
def drop_all_capabilities(resource: dict) -> list[Finding]:
    findings = []
    for container in containers(resource):
        sec = container.get("securityContext", {})
        drop = sec.get("capabilities", {}).get("drop", []) or []
        if "ALL" not in drop:
            name = container.get("name", "?")
            findings.append(
                make_finding(
                    resource,
                    "drop-all-capabilities",
                    Severity.WARNING,
                    f"container '{name}' does not drop ALL capabilities",
                )
            )
    return findings


@register
def added_capabilities(resource: dict) -> list[Finding]:
    findings = []
    dangerous = {"ALL", "NET_ADMIN", "SYS_ADMIN", "SYS_PTRACE", "SYS_MODULE", "NET_RAW"}
    for container in containers(resource):
        sec = container.get("securityContext", {})
        adds = sec.get("capabilities", {}).get("add", []) or []
        for cap in adds:
            if cap in dangerous:
                name = container.get("name", "?")
                findings.append(
                    make_finding(
                        resource,
                        "added-capabilities",
                        Severity.CRITICAL,
                        f"container '{name}' adds dangerous capability {cap}",
                    )
                )
    return findings


@register
def host_pid(resource: dict) -> list[Finding]:
    findings = []
    if pod_spec(resource).get("hostPID") is True:
        findings.append(
            make_finding(
                resource,
                "host-pid",
                Severity.CRITICAL,
                "pod shares the host PID namespace (hostPID: true)",
            )
        )
    return findings


@register
def host_ipc(resource: dict) -> list[Finding]:
    findings = []
    if pod_spec(resource).get("hostIPC") is True:
        findings.append(
            make_finding(
                resource,
                "host-ipc",
                Severity.CRITICAL,
                "pod shares the host IPC namespace (hostIPC: true)",
            )
        )
    return findings


@register
def no_seccomp_profile(resource: dict) -> list[Finding]:
    findings = []
    sec = pod_spec(resource).get("securityContext", {})
    sec_type = sec.get("seccompProfile", {}).get("type")
    if sec_type not in ("RuntimeDefault", "Localhost"):
        findings.append(
            make_finding(
                resource,
                "no-seccomp-profile",
                Severity.WARNING,
                "pod does not set a seccompProfile (RuntimeDefault recommended)",
            )
        )
    return findings


@register
def no_readiness_probe(resource: dict) -> list[Finding]:
    findings = []
    for container in containers(resource):
        if not container.get("readinessProbe"):
            name = container.get("name", "?")
            findings.append(
                make_finding(
                    resource,
                    "no-readiness-probe",
                    Severity.WARNING,
                    f"container '{name}' has no readiness probe",
                )
            )
    return findings


@register
def no_memory_request(resource: dict) -> list[Finding]:
    findings = []
    for container in containers(resource):
        if not container.get("resources", {}).get("requests", {}).get("memory"):
            name = container.get("name", "?")
            findings.append(
                make_finding(
                    resource,
                    "no-memory-request",
                    Severity.WARNING,
                    f"container '{name}' has no memory request",
                )
            )
    return findings


@register
def no_cpu_limit(resource: dict) -> list[Finding]:
    findings = []
    for container in containers(resource):
        if not container.get("resources", {}).get("limits", {}).get("cpu"):
            name = container.get("name", "?")
            findings.append(
                make_finding(
                    resource,
                    "no-cpu-limit",
                    Severity.INFO,
                    f"container '{name}' has no CPU limit",
                )
            )
    return findings


@register
def single_replica(resource: dict) -> list[Finding]:
    kind, _, _ = meta(resource)
    if kind not in ("Deployment", "StatefulSet", "ReplicaSet"):
        return []
    replicas = resource.get("spec", {}).get("replicas", 1)
    if replicas is not None and replicas <= 1:
        return [
            make_finding(
                resource,
                "single-replica",
                Severity.WARNING,
                f"{kind} runs a single replica (no redundancy)",
            )
        ]
    return []


@register
def default_namespace(resource: dict) -> list[Finding]:
    kind, namespace, _ = meta(resource)
    if namespace == "default":
        return [
            make_finding(
                resource,
                "default-namespace",
                Severity.INFO,
                "resource is in the 'default' namespace",
            )
        ]
    return []


@register
def best_effort_qos(resource: dict) -> list[Finding]:
    cs = containers(resource)
    if not cs:
        return []
    for c in cs:
        if c.get("resources", {}).get("requests") or c.get("resources", {}).get("limits"):
            return []
    return [
        make_finding(
            resource,
            "best-effort-qos",
            Severity.WARNING,
            "pod is BestEffort QoS (no requests/limits — first to be evicted under pressure)",
        )
    ]


def _selector_subset(match_labels: dict, target_labels: dict) -> bool:
    return all(target_labels.get(k) == v for k, v in (match_labels or {}).items())


@register_corpus
def pdb_coverage(resources: list[dict]) -> list[Finding]:
    findings = []
    pdbs = [r for r in resources if meta(r)[0] == "PodDisruptionBudget"]
    for w in resources:
        kind, ns, name = meta(w)
        if kind not in ("Deployment", "StatefulSet"):
            continue
        replicas = w.get("spec", {}).get("replicas", 1)
        if not replicas or replicas <= 1:
            continue
        pod_labels = w.get("spec", {}).get("template", {}).get("metadata", {}).get("labels", {}) or {}
        has_pdb = False
        for pdb in pdbs:
            if meta(pdb)[1] != ns:
                continue
            match = pdb.get("spec", {}).get("selector", {}).get("matchLabels", {}) or {}
            if _selector_subset(match, pod_labels):
                has_pdb = True
                break
        if not has_pdb:
            findings.append(
                make_finding(
                    w,
                    "pdb-coverage",
                    Severity.WARNING,
                    f"{kind} '{name}' ({replicas} replicas) has no PodDisruptionBudget",
                )
            )
    return findings


@register_corpus
def networkpolicy_coverage(resources: list[dict]) -> list[Finding]:
    findings = []
    nps = [r for r in resources if meta(r)[0] == "NetworkPolicy"]
    for p in resources:
        kind, ns, name = meta(p)
        if kind != "Pod":
            continue
        pod_labels = p.get("metadata", {}).get("labels", {}) or {}
        has_np = False
        for np in nps:
            if meta(np)[1] != ns:
                continue
            match = np.get("spec", {}).get("podSelector", {}).get("matchLabels", {}) or {}
            if _selector_subset(match, pod_labels):
                has_np = True
                break
        if not has_np:
            findings.append(
                make_finding(
                    p,
                    "networkpolicy-coverage",
                    Severity.WARNING,
                    f"pod '{name}' is not selected by any NetworkPolicy (default-allow traffic)",
                )
            )
    return findings


@register
def image_no_digest(resource: dict) -> list[Finding]:
    findings = []
    for container in containers(resource):
        image = container.get("image", "")
        if "@sha256:" not in image:
            name = container.get("name", "?")
            findings.append(
                make_finding(
                    resource,
                    "image-no-digest",
                    Severity.INFO,
                    f"container '{name}' image is not pinned by digest",
                )
            )
    return findings


@register
def missing_recommended_labels(resource: dict) -> list[Finding]:
    labels = resource.get("metadata", {}).get("labels", {}) or {}
    if "app.kubernetes.io/name" not in labels:
        return [
            make_finding(
                resource,
                "missing-recommended-labels",
                Severity.INFO,
                "missing recommended label 'app.kubernetes.io/name'",
            )
        ]
    return []


@register
def liveness_equals_readiness(resource: dict) -> list[Finding]:
    findings = []
    for container in containers(resource):
        lp = container.get("livenessProbe")
        rp = container.get("readinessProbe")
        if lp and rp and lp == rp:
            name = container.get("name", "?")
            findings.append(
                make_finding(
                    resource,
                    "liveness-equals-readiness",
                    Severity.WARNING,
                    f"container '{name}' has identical liveness and readiness probes",
                )
            )
    return findings


@register
def deprecated_api_version(resource: dict) -> list[Finding]:
    kind, _, _ = meta(resource)
    av = resource.get("apiVersion", "")
    if av in DEPRECATED_APIS and kind in DEPRECATED_APIS[av]:
        return [
            make_finding(
                resource,
                "deprecated-api-version",
                Severity.WARNING,
                f"{av} {kind} is deprecated/removed ({DEPRECATED_APIS[av][kind]})",
            )
        ]
    return []


@register
def ingress_no_tls(resource: dict) -> list[Finding]:
    kind, _, _ = meta(resource)
    if kind == "Ingress" and not resource.get("spec", {}).get("tls"):
        return [
            make_finding(
                resource,
                "ingress-no-tls",
                Severity.WARNING,
                "Ingress has no TLS configured",
            )
        ]
    return []


@register
def host_path_volume(resource: dict) -> list[Finding]:
    findings = []
    for volume in pod_spec(resource).get("volumes", []) or []:
        if "hostPath" in volume:
            findings.append(
                make_finding(
                    resource,
                    "host-path-volume",
                    Severity.CRITICAL,
                    f"pod mounts hostPath volume '{volume.get('name','?')}' (host filesystem access)",
                )
            )
    return findings


@register
def run_as_user_zero(resource: dict) -> list[Finding]:
    findings = []
    pod_uid = pod_spec(resource).get("securityContext", {}).get("runAsUser")
    for container in containers(resource):
        c_uid = container.get("securityContext", {}).get("runAsUser")
        effective = c_uid if c_uid is not None else pod_uid
        if effective == 0:
            name = container.get("name", "?")
            findings.append(
                make_finding(
                    resource,
                    "run-as-user-zero",
                    Severity.CRITICAL,
                    f"container '{name}' runs as UID 0 (root)",
                )
            )
    return findings


@register
def automount_sa_token(resource: dict) -> list[Finding]:
    if not containers(resource):
        return []
    if pod_spec(resource).get("automountServiceAccountToken") is not False:
        return [
            make_finding(
                resource,
                "automount-sa-token",
                Severity.INFO,
                "pod auto-mounts the ServiceAccount token (set automountServiceAccountToken: false if unused)",
            )
        ]
    return []


@register
def service_external_exposure(resource: dict) -> list[Finding]:
    kind, _, _ = meta(resource)
    if kind == "Service":
        st = resource.get("spec", {}).get("type")
        if st in ("LoadBalancer", "NodePort"):
            return [
                make_finding(
                    resource,
                    "service-external-exposure",
                    Severity.INFO,
                    f"Service is externally exposed (type {st})",
                )
            ]
    return []


@register
def secret_in_env(resource: dict) -> list[Finding]:
    findings = []
    for container in containers(resource):
        name = container.get("name", "?")
        found = False
        for e in container.get("env", []) or []:
            if e.get("valueFrom", {}).get("secretKeyRef"):
                found = True
                break
        if not found:
            for ef in container.get("envFrom", []) or []:
                if ef.get("secretRef"):
                    found = True
                    break
        if found:
            findings.append(
                make_finding(
                    resource,
                    "secret-in-env",
                    Severity.INFO,
                    f"container '{name}' exposes a Secret via environment variable",
                )
            )
    return findings


@register
def missing_anti_affinity(resource: dict) -> list[Finding]:
    kind, _, _ = meta(resource)
    if kind not in ("Deployment", "StatefulSet", "ReplicaSet"):
        return []
    replicas = resource.get("spec", {}).get("replicas", 1)
    if replicas and replicas > 1:
        ps = pod_spec(resource)
        if not ps.get("affinity", {}).get("podAntiAffinity") and not ps.get("topologySpreadConstraints"):
            return [
                make_finding(
                    resource,
                    "missing-anti-affinity",
                    Severity.INFO,
                    f"{kind} with {replicas} replicas has no anti-affinity or topology spread (replicas may co-locate)",
                )
            ]
    return []
