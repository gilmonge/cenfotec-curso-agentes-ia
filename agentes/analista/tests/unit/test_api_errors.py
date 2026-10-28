import pytest

from agentes.analista.api.errors import _status
from agentes.analista.core.models import ErrorCode


@pytest.mark.parametrize(
    ("code", "status"),
    [
        (ErrorCode.OPENCODE_AUTH_FAILED, 503),
        (ErrorCode.OPENCODE_RATE_LIMITED, 503),
        (ErrorCode.MODEL_UNAVAILABLE, 503),
        (ErrorCode.OPENCODE_UNAVAILABLE, 503),
        (ErrorCode.TURN_TIMEOUT, 504),
    ],
)
def test_upstream_failures_use_stable_service_statuses(code, status):
    assert _status(code) == status
