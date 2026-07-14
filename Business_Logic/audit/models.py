import enum
from dataclasses import dataclass


class Severity(enum.Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: Severity
    kind: str
    namespace: str
    name: str
    message: str
