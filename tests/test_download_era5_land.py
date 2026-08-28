import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from download_era5_land import _retrieve_with_retries


class FakeClient:
    def __init__(self, failures: int):
        self.failures = failures
        self.calls = 0

    def retrieve(self, _dataset, _request, target):
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("synthetic terminal CDS job failure")
        Path(target).write_bytes(b"valid payload")


def test_month_job_resubmits_after_terminal_failure(tmp_path):
    target = tmp_path / "era5_land_2022_10.nc"
    client = FakeClient(failures=2)
    _retrieve_with_retries(client, {}, target, request_retries=2, retry_delay_seconds=0)
    assert client.calls == 3
    assert target.read_bytes() == b"valid payload"
    assert not target.with_name(target.name + ".part").exists()


def test_month_job_refuses_to_leave_partial_payload(tmp_path):
    target = tmp_path / "era5_land_2022_10.nc"
    client = FakeClient(failures=3)
    with pytest.raises(RuntimeError, match="synthetic terminal"):
        _retrieve_with_retries(client, {}, target, request_retries=2, retry_delay_seconds=0)
    assert not target.exists()
    assert not target.with_name(target.name + ".part").exists()
