from Business_Logic.audit.engine import run_audit
from Business_Logic.audit.models import Severity


def _pod(name, containers, overrides=None):
    pod = {
        "kind": "Pod",
        "metadata": {"name": name, "namespace": "default"},
        "spec": {"containers": containers},
    }
    if overrides:
        pod["spec"].update(overrides)
    return pod


def _container(**kwargs):
    c = {"name": "c1", "image": "nginx:1.21"}
    c.update(kwargs)
    return c


class TestNoMemoryLimit:
    def test_positive(self):
        resource = _pod("mem-pos", [_container()])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "no-memory-limit"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.WARNING

    def test_negative(self):
        resource = _pod(
            "mem-neg",
            [_container(resources={"limits": {"memory": "256Mi"}})],
        )
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "no-memory-limit"]
        assert len(matches) == 0


class TestImageLatest:
    def test_positive_no_tag(self):
        resource = _pod("img-pos1", [_container(image="nginx")])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "image-latest"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.WARNING

    def test_positive_latest_tag(self):
        resource = _pod("img-pos2", [_container(image="nginx:latest")])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "image-latest"]
        assert len(matches) == 1

    def test_negative(self):
        resource = _pod("img-neg", [_container(image="nginx:1.21")])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "image-latest"]
        assert len(matches) == 0

    def test_registry_port_not_mistaken_for_tag(self):
        resource = _pod("img-reg", [_container(image="localhost:5000/nginx:1.21")])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "image-latest"]
        assert len(matches) == 0


class TestRunsAsRoot:
    def test_positive_no_security_context(self):
        resource = _pod("root-pos", [_container()])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "runs-as-root"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.CRITICAL

    def test_negative_pod_level(self):
        resource = _pod(
            "root-neg",
            [_container()],
            overrides={"securityContext": {"runAsNonRoot": True}},
        )
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "runs-as-root"]
        assert len(matches) == 0

    def test_negative_container_level(self):
        resource = _pod(
            "root-neg2",
            [_container(securityContext={"runAsNonRoot": True})],
        )
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "runs-as-root"]
        assert len(matches) == 0


class TestPrivileged:
    def test_positive(self):
        resource = _pod(
            "priv-pos",
            [_container(securityContext={"privileged": True})],
        )
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "privileged"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.CRITICAL

    def test_negative(self):
        resource = _pod("priv-neg", [_container()])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "privileged"]
        assert len(matches) == 0


class TestNoLivenessProbe:
    def test_positive(self):
        resource = _pod("probe-pos", [_container()])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "no-liveness-probe"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.WARNING

    def test_negative(self):
        resource = _pod(
            "probe-neg",
            [_container(livenessProbe={"httpGet": {"path": "/health"}})],
        )
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "no-liveness-probe"]
        assert len(matches) == 0


class TestNoCpuRequest:
    def test_positive(self):
        resource = _pod("cpu-pos", [_container()])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "no-cpu-request"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.WARNING

    def test_negative(self):
        resource = _pod(
            "cpu-neg",
            [_container(resources={"requests": {"cpu": "100m"}})],
        )
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "no-cpu-request"]
        assert len(matches) == 0


class TestHostNetwork:
    def test_positive(self):
        resource = _pod("hn-pos", [_container()], overrides={"hostNetwork": True})
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "host-network"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.CRITICAL

    def test_negative(self):
        resource = _pod("hn-neg", [_container()])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "host-network"]
        assert len(matches) == 0


class TestAllowPrivilegeEscalation:
    def test_positive(self):
        resource = _pod("ape", [_container()])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "allow-privilege-escalation"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.WARNING

    def test_negative(self):
        resource = _pod(
            "ape-neg",
            [_container(securityContext={"allowPrivilegeEscalation": False})],
        )
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "allow-privilege-escalation"]
        assert len(matches) == 0


class TestReadOnlyRootFs:
    def test_positive(self):
        resource = _pod("ror-pos", [_container()])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "read-only-root-fs"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.WARNING

    def test_negative(self):
        resource = _pod(
            "ror-neg",
            [_container(securityContext={"readOnlyRootFilesystem": True})],
        )
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "read-only-root-fs"]
        assert len(matches) == 0


class TestDropAllCapabilities:
    def test_positive(self):
        resource = _pod("dac-pos", [_container()])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "drop-all-capabilities"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.WARNING

    def test_negative(self):
        resource = _pod(
            "dac-neg",
            [_container(securityContext={"capabilities": {"drop": ["ALL"]}})],
        )
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "drop-all-capabilities"]
        assert len(matches) == 0


class TestAddedCapabilities:
    def test_positive(self):
        resource = _pod(
            "ac-pos",
            [_container(securityContext={"capabilities": {"add": ["SYS_ADMIN"]}})],
        )
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "added-capabilities"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.CRITICAL

    def test_negative(self):
        resource = _pod(
            "ac-neg",
            [_container(securityContext={"capabilities": {"add": ["NET_BIND_SERVICE"]}})],
        )
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "added-capabilities"]
        assert len(matches) == 0


class TestHostPid:
    def test_positive(self):
        resource = _pod("hp", [_container()], overrides={"hostPID": True})
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "host-pid"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.CRITICAL

    def test_negative(self):
        resource = _pod("hp2", [_container()])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "host-pid"]
        assert len(matches) == 0


class TestHostIpc:
    def test_positive(self):
        resource = _pod("hipc", [_container()], overrides={"hostIPC": True})
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "host-ipc"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.CRITICAL

    def test_negative(self):
        resource = _pod("hipc2", [_container()])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "host-ipc"]
        assert len(matches) == 0


class TestNoSeccompProfile:
    def test_positive(self):
        resource = _pod("sc", [_container()])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "no-seccomp-profile"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.WARNING

    def test_negative(self):
        resource = _pod(
            "sc2",
            [_container()],
            overrides={"securityContext": {"seccompProfile": {"type": "RuntimeDefault"}}},
        )
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "no-seccomp-profile"]
        assert len(matches) == 0


class TestNoReadinessProbe:
    def test_positive(self):
        resource = _pod("rp-pos", [_container()])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "no-readiness-probe"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.WARNING

    def test_negative(self):
        resource = _pod(
            "rp-neg",
            [_container(readinessProbe={"httpGet": {"path": "/ready"}})],
        )
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "no-readiness-probe"]
        assert len(matches) == 0


class TestNoMemoryRequest:
    def test_positive(self):
        resource = _pod("mr-pos", [_container()])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "no-memory-request"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.WARNING

    def test_negative(self):
        resource = _pod(
            "mr-neg",
            [_container(resources={"requests": {"memory": "64Mi"}})],
        )
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "no-memory-request"]
        assert len(matches) == 0


class TestNoCpuLimit:
    def test_positive(self):
        resource = _pod("cl-pos", [_container()])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "no-cpu-limit"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.INFO

    def test_negative(self):
        resource = _pod(
            "cl-neg",
            [_container(resources={"limits": {"cpu": "500m"}})],
        )
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "no-cpu-limit"]
        assert len(matches) == 0


class TestSingleReplica:
    def test_positive(self):
        resource = {
            "kind": "Deployment",
            "metadata": {"name": "d", "namespace": "default"},
            "spec": {
                "replicas": 1,
                "template": {"spec": {"containers": [_container()]}},
            },
        }
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "single-replica"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.WARNING

    def test_negative_multi_replica(self):
        resource = {
            "kind": "Deployment",
            "metadata": {"name": "d", "namespace": "default"},
            "spec": {
                "replicas": 3,
                "template": {"spec": {"containers": [_container()]}},
            },
        }
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "single-replica"]
        assert len(matches) == 0

    def test_negative_pod(self):
        resource = _pod("sr-pod", [_container()])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "single-replica"]
        assert len(matches) == 0


class TestDefaultNamespace:
    def test_positive(self):
        resource = _pod("dn", [_container()])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "default-namespace"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.INFO

    def test_negative(self):
        resource = {
            "kind": "Pod",
            "metadata": {"name": "x", "namespace": "prod"},
            "spec": {"containers": [_container()]},
        }
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "default-namespace"]
        assert len(matches) == 0


class TestBestEffortQos:
    def test_positive(self):
        resource = _pod("be", [_container()])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "best-effort-qos"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.WARNING

    def test_negative(self):
        resource = _pod(
            "be2",
            [_container(resources={"requests": {"cpu": "100m"}})],
        )
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "best-effort-qos"]
        assert len(matches) == 0


class TestImageNoDigest:
    def test_positive(self):
        resource = _pod("ind-pos", [_container()])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "image-no-digest"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.INFO

    def test_negative(self):
        resource = _pod("ind-neg", [_container(image="nginx@sha256:abc123")])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "image-no-digest"]
        assert len(matches) == 0


class TestMissingRecommendedLabels:
    def test_positive(self):
        resource = _pod("ml", [_container()])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "missing-recommended-labels"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.INFO

    def test_negative(self):
        resource = {
            "kind": "Pod",
            "metadata": {"name": "x", "namespace": "default", "labels": {"app.kubernetes.io/name": "web"}},
            "spec": {"containers": [_container()]},
        }
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "missing-recommended-labels"]
        assert len(matches) == 0


class TestLivenessEqualsReadiness:
    def test_positive(self):
        resource = _pod("ler-pos", [_container(livenessProbe={"httpGet": {"path": "/h"}}, readinessProbe={"httpGet": {"path": "/h"}})])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "liveness-equals-readiness"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.WARNING

    def test_negative(self):
        resource = _pod("ler-neg", [_container(livenessProbe={"httpGet": {"path": "/live"}}, readinessProbe={"httpGet": {"path": "/ready"}})])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "liveness-equals-readiness"]
        assert len(matches) == 0


class TestDeprecatedApiVersion:
    def test_positive(self):
        resource = {"apiVersion": "extensions/v1beta1", "kind": "Ingress", "metadata": {"name": "i", "namespace": "default"}, "spec": {}}
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "deprecated-api-version"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.WARNING

    def test_negative(self):
        resource = {"apiVersion": "networking.k8s.io/v1", "kind": "Ingress", "metadata": {"name": "i", "namespace": "default"}, "spec": {}}
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "deprecated-api-version"]
        assert len(matches) == 0


class TestIngressNoTls:
    def test_positive(self):
        resource = {"kind": "Ingress", "metadata": {"name": "i", "namespace": "default"}, "spec": {}}
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "ingress-no-tls"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.WARNING

    def test_negative(self):
        resource = {"kind": "Ingress", "metadata": {"name": "i", "namespace": "default"}, "spec": {"tls": [{"hosts": ["x"]}]}}
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "ingress-no-tls"]
        assert len(matches) == 0


class TestHostPathVolume:
    def test_positive(self):
        resource = _pod("hpv", [_container()], overrides={"volumes": [{"name": "v", "hostPath": {"path": "/etc"}}]})
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "host-path-volume"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.CRITICAL

    def test_negative(self):
        resource = _pod("hpv2", [_container()], overrides={"volumes": [{"name": "v", "emptyDir": {}}]})
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "host-path-volume"]
        assert len(matches) == 0


class TestRunAsUserZero:
    def test_positive(self):
        resource = _pod("ruz", [_container(securityContext={"runAsUser": 0})])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "run-as-user-zero"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.CRITICAL

    def test_negative(self):
        resource = _pod("ruz2", [_container(securityContext={"runAsUser": 1000})])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "run-as-user-zero"]
        assert len(matches) == 0


class TestAutomountSaToken:
    def test_positive(self):
        resource = _pod("amt", [_container()])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "automount-sa-token"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.INFO

    def test_negative(self):
        resource = _pod("amt2", [_container()], overrides={"automountServiceAccountToken": False})
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "automount-sa-token"]
        assert len(matches) == 0


class TestServiceExternalExposure:
    def test_positive(self):
        resource = {"kind": "Service", "metadata": {"name": "s", "namespace": "default"}, "spec": {"type": "LoadBalancer"}}
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "service-external-exposure"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.INFO

    def test_negative(self):
        resource = {"kind": "Service", "metadata": {"name": "s", "namespace": "default"}, "spec": {"type": "ClusterIP"}}
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "service-external-exposure"]
        assert len(matches) == 0


class TestSecretInEnv:
    def test_positive(self):
        resource = _pod("sie", [_container(env=[{"name": "PW", "valueFrom": {"secretKeyRef": {"name": "db", "key": "pw"}}}])])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "secret-in-env"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.INFO

    def test_negative(self):
        resource = _pod("sie2", [_container(env=[{"name": "LOG", "value": "info"}])])
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "secret-in-env"]
        assert len(matches) == 0


class TestMissingAntiAffinity:
    def test_positive(self):
        resource = {"kind": "Deployment", "metadata": {"name": "d", "namespace": "default"}, "spec": {"replicas": 3, "template": {"spec": {"containers": [_container()]}}}}
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "missing-anti-affinity"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.INFO

    def test_negative_single_replica(self):
        resource = {"kind": "Deployment", "metadata": {"name": "d", "namespace": "default"}, "spec": {"replicas": 1, "template": {"spec": {"containers": [_container()]}}}}
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "missing-anti-affinity"]
        assert len(matches) == 0

    def test_negative_with_anti_affinity(self):
        resource = {"kind": "Deployment", "metadata": {"name": "d", "namespace": "default"}, "spec": {"replicas": 3, "template": {"spec": {"containers": [_container()], "affinity": {"podAntiAffinity": {"requiredDuringSchedulingIgnoredDuringExecution": []}}}}}}
        findings = run_audit([resource])
        matches = [f for f in findings if f.rule_id == "missing-anti-affinity"]
        assert len(matches) == 0


class TestPdbCoverage:
    def _deploy(self, labels, replicas):
        return {
            "kind": "Deployment",
            "metadata": {"name": "web", "namespace": "default"},
            "spec": {
                "replicas": replicas,
                "template": {
                    "metadata": {"labels": labels},
                    "spec": {"containers": [_container()]},
                },
            },
        }

    def _pdb(self, match):
        return {
            "kind": "PodDisruptionBudget",
            "metadata": {"name": "p", "namespace": "default"},
            "spec": {"selector": {"matchLabels": match}},
        }

    def test_positive(self):
        findings = run_audit([self._deploy({"app": "web"}, 3)])
        matches = [f for f in findings if f.rule_id == "pdb-coverage"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.WARNING

    def test_negative_matching_pdb(self):
        findings = run_audit([self._deploy({"app": "web"}, 3), self._pdb({"app": "web"})])
        matches = [f for f in findings if f.rule_id == "pdb-coverage"]
        assert len(matches) == 0

    def test_negative_single_replica(self):
        findings = run_audit([self._deploy({"app": "web"}, 1)])
        matches = [f for f in findings if f.rule_id == "pdb-coverage"]
        assert len(matches) == 0


class TestNetworkPolicyCoverage:
    def _pod2(self, labels):
        return {
            "kind": "Pod",
            "metadata": {"name": "x", "namespace": "default", "labels": labels},
            "spec": {"containers": [_container()]},
        }

    def _np(self, match):
        return {
            "kind": "NetworkPolicy",
            "metadata": {"name": "n", "namespace": "default"},
            "spec": {"podSelector": {"matchLabels": match}},
        }

    def test_positive(self):
        findings = run_audit([self._pod2({"app": "web"})])
        matches = [f for f in findings if f.rule_id == "networkpolicy-coverage"]
        assert len(matches) == 1
        assert matches[0].severity == Severity.WARNING

    def test_negative_matching_np(self):
        findings = run_audit([self._pod2({"app": "web"}), self._np({"app": "web"})])
        matches = [f for f in findings if f.rule_id == "networkpolicy-coverage"]
        assert len(matches) == 0

    def test_negative_empty_selector(self):
        findings = run_audit([self._pod2({"app": "web"}), self._np({})])
        matches = [f for f in findings if f.rule_id == "networkpolicy-coverage"]
        assert len(matches) == 0
