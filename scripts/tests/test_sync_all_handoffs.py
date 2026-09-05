from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
WRAPPER_PATH = SCRIPTS_DIR / "sync_all_handoffs.sh"


ICLOUD_HANDOFF_TEMPLATE = """# iCloud HANDOFF
## Completed
- OP-026 COMPLETE

## Current task
- recruiter-facing public demo polish
"""

LOCAL_HANDOFF_TEMPLATE = """# Local HANDOFF
## Completed
- OP-026 COMPLETE
"""


def _run_wrapper(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    full_env = os.environ.copy()
    defaults = {"SYNC_CLOUD_AGENT_REPORT_IMPORT": "false"}
    defaults.update(env)
    full_env.update(defaults)
    return subprocess.run(
        ["bash", str(WRAPPER_PATH)],
        env=full_env,
        cwd=str(Path(env.get("SYNC_ONEPILOT_REPO_ROOT", os.getcwd()))),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _write_sanitizer_stub(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env python3
import argparse
import json
import os
import sys

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--output")
parser.add_argument("--handoff")
parser.add_argument("--repo-root")
args, _unknown = parser.parse_known_args()

record_path = os.environ.get("SYNC_TEST_RECORD_PATH")
if record_path:
    payload = {"output": args.output, "handoff": args.handoff, "repo_root": args.__dict__.get("repo-root")}
    # repo-root isn't a valid python identifier for argparse with hyphen; store argv-derived value as a fallback.
    payload["argv_output"] = args.output
    payload["argv_handoff"] = args.handoff
    try:
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(payload, f)
    except Exception:
        # Record failures should not leak sensitive content; just fail the stub.
        sys.exit(10)

if os.environ.get("SYNC_TEST_SANITIZER_FAIL") == "1":
    # Fail-closed: do not write output.
    sys.exit(2)

if args.output:
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("SANITIZED_STUB\\n")

sys.exit(0)
""",
        encoding="utf-8",
    )


def _write_external_stub(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env bash
set -euo pipefail

if [[ "${SYNC_TEST_EXTERNAL_SHOULD_FAIL:-0}" == "1" ]]; then
  exit "${SYNC_TEST_EXTERNAL_EXIT_CODE:-42}"
fi

local_path="${SYNC_ONEPILOT_LOCAL_HANDOFF_PATH:?}"
icloud_path="${SYNC_ONEPILOT_ICLOUD_HANDOFF_PATH:?}"

mkdir -p "$(dirname "$local_path")"
cat > "$local_path" <<'EOF'
# Local HANDOFF
## Completed
- OP-026 COMPLETE
EOF

if [[ "${SYNC_TEST_EXTERNAL_CREATE_ICLOUD:-1}" == "1" ]]; then
  mkdir -p "$(dirname "$icloud_path")"
  cat > "$icloud_path" <<'EOF'
# iCloud HANDOFF
## Completed
- OP-026 COMPLETE

## Current task
- recruiter-facing public demo polish
EOF

  if [[ "${SYNC_TEST_EXTERNAL_TOUCH_ICLOUD:-1}" == "1" ]]; then
    touch "$icloud_path"
  fi
fi
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


@pytest.mark.parametrize(
    "name, env_overrides",
    [
        (
            "external_sync_failure",
            {
                "SYNC_TEST_EXTERNAL_SHOULD_FAIL": "1",
                "SYNC_TEST_EXTERNAL_EXIT_CODE": "42",
            },
        ),
        (
            "icloud_missing",
            {
                "SYNC_TEST_EXTERNAL_CREATE_ICLOUD": "0",
            },
        ),
        (
            "icloud_mtime_not_updated",
            {
                "SYNC_TEST_EXTERNAL_CREATE_ICLOUD": "0",  # Do not touch existing iCloud file.
            },
        ),
    ],
)
def test_wrapper_fails_failfast_on_sync_or_icloud_problems(
    tmp_path: Path, name: str, env_overrides: dict[str, str]
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    local_handoff = repo_root / "HANDOFF.md"
    icloud_dir = tmp_path / "icloud"
    icloud_handoff = icloud_dir / "HANDOFF.md"
    out_path = tmp_path / "docs" / "agent" / "CLOUD_HANDOFF.md"

    external_stub = tmp_path / "sync-onepilot-handoff-stub.sh"
    _write_external_stub(external_stub)

    sanitizer_stub = tmp_path / "sync_cloud_handoff_stubber.py"
    _write_sanitizer_stub(sanitizer_stub)

    record_path = tmp_path / "sanitizer_record.json"

    # For the mtime test, pre-create iCloud HANDOFF with an old mtime.
    if name == "icloud_mtime_not_updated":
        icloud_dir.mkdir(parents=True, exist_ok=True)
        icloud_handoff.write_text(ICLOUD_HANDOFF_TEMPLATE, encoding="utf-8")
        old_mtime = 1_000_000_000  # stable epoch seconds.
        os.utime(icloud_handoff, (old_mtime, old_mtime))

    result = _run_wrapper(
        {
            "SYNC_ONEPILOT_REPO_ROOT": str(repo_root),
            "SYNC_ONEPILOT_LOCAL_HANDOFF_PATH": str(local_handoff),
            "SYNC_ONEPILOT_ICLOUD_HANDOFF_PATH": str(icloud_handoff),
            "SYNC_ONEPILOT_HANDOFF_SH": str(external_stub),
            "SYNC_CLOUD_HANDOFF_PYTHON_SCRIPT": str(sanitizer_stub),
            "SYNC_CLOUD_HANDOFF_OUTPUT_PATH": str(out_path),
            "SYNC_CLOUD_HANDOFF_FETCH": "false",
            "SYNC_TEST_RECORD_PATH": str(record_path),
            **env_overrides,
        }
    )

    assert result.returncode != 0, f"expected non-zero for {name}, got:\n{result.stdout}\n{result.stderr}"
    assert not out_path.exists(), "wrapper must not write output on failure"
    assert not record_path.exists(), "sanitizer stub must not be invoked on failure"


def test_wrapper_invokes_sanitizer_and_writes_output(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    local_handoff = repo_root / "HANDOFF.md"

    icloud_dir = tmp_path / "icloud"
    icloud_dir.mkdir(parents=True, exist_ok=True)
    icloud_handoff = icloud_dir / "HANDOFF.md"
    out_path = tmp_path / "docs" / "agent" / "CLOUD_HANDOFF.md"

    # Pre-create iCloud HANDOFF so the wrapper enforces mtime update checks.
    icloud_handoff.write_text(ICLOUD_HANDOFF_TEMPLATE, encoding="utf-8")
    old_mtime = 1_000_000_000  # stable epoch seconds.
    os.utime(icloud_handoff, (old_mtime, old_mtime))

    external_stub = tmp_path / "sync-onepilot-handoff-stub.sh"
    _write_external_stub(external_stub)

    sanitizer_stub = tmp_path / "sync_cloud_handoff_stubber.py"
    _write_sanitizer_stub(sanitizer_stub)

    record_path = tmp_path / "sanitizer_record.json"

    result = _run_wrapper(
        {
            "SYNC_ONEPILOT_REPO_ROOT": str(repo_root),
            "SYNC_ONEPILOT_LOCAL_HANDOFF_PATH": str(local_handoff),
            "SYNC_ONEPILOT_ICLOUD_HANDOFF_PATH": str(icloud_handoff),
            "SYNC_ONEPILOT_HANDOFF_SH": str(external_stub),
            "SYNC_CLOUD_HANDOFF_PYTHON_SCRIPT": str(sanitizer_stub),
            "SYNC_CLOUD_HANDOFF_OUTPUT_PATH": str(out_path),
            "SYNC_CLOUD_HANDOFF_FETCH": "false",
            "SYNC_TEST_RECORD_PATH": str(record_path),
            # Ensure external stub overwrites/touches iCloud, making mtime newer.
            "SYNC_TEST_EXTERNAL_CREATE_ICLOUD": "1",
            "SYNC_TEST_EXTERNAL_TOUCH_ICLOUD": "1",
        }
    )

    assert result.returncode == 0, f"expected success, got:\n{result.stdout}\n{result.stderr}"
    assert out_path.exists() and out_path.stat().st_size > 0
    assert record_path.exists()
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    assert payload["argv_output"] == str(out_path)
    assert payload["argv_handoff"] == str(local_handoff)


def test_wrapper_does_not_write_output_on_sanitizer_failure(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    local_handoff = repo_root / "HANDOFF.md"

    icloud_dir = tmp_path / "icloud"
    icloud_dir.mkdir(parents=True, exist_ok=True)
    icloud_handoff = icloud_dir / "HANDOFF.md"
    out_path = tmp_path / "docs" / "agent" / "CLOUD_HANDOFF.md"

    external_stub = tmp_path / "sync-onepilot-handoff-stub.sh"
    _write_external_stub(external_stub)

    sanitizer_stub = tmp_path / "sync_cloud_handoff_stubber.py"
    _write_sanitizer_stub(sanitizer_stub)

    record_path = tmp_path / "sanitizer_record.json"

    # Pre-create iCloud HANDOFF so mtime update check is exercised.
    icloud_handoff.write_text(ICLOUD_HANDOFF_TEMPLATE, encoding="utf-8")
    old_mtime = 1_000_000_000
    os.utime(icloud_handoff, (old_mtime, old_mtime))

    result = _run_wrapper(
        {
            "SYNC_ONEPILOT_REPO_ROOT": str(repo_root),
            "SYNC_ONEPILOT_LOCAL_HANDOFF_PATH": str(local_handoff),
            "SYNC_ONEPILOT_ICLOUD_HANDOFF_PATH": str(icloud_handoff),
            "SYNC_ONEPILOT_HANDOFF_SH": str(external_stub),
            "SYNC_CLOUD_HANDOFF_PYTHON_SCRIPT": str(sanitizer_stub),
            "SYNC_CLOUD_HANDOFF_OUTPUT_PATH": str(out_path),
            "SYNC_CLOUD_HANDOFF_FETCH": "false",
            "SYNC_TEST_RECORD_PATH": str(record_path),
            "SYNC_TEST_SANITIZER_FAIL": "1",
            "SYNC_TEST_EXTERNAL_CREATE_ICLOUD": "1",
            "SYNC_TEST_EXTERNAL_TOUCH_ICLOUD": "1",
        }
    )

    assert result.returncode != 0, "expected wrapper to fail when sanitizer fails"
    assert not out_path.exists(), "output must not exist after sanitizer failure"
    assert record_path.exists(), "sanitizer invocation should have been attempted"


def _write_order_stub(path: Path, label: str) -> None:
    path.write_text(
        f"""#!/usr/bin/env python3
import os
from pathlib import Path
order = os.environ.get("SYNC_TEST_ORDER_PATH")
if order:
    Path(order).parent.mkdir(parents=True, exist_ok=True)
    with open(order, "a", encoding="utf-8") as f:
        f.write("{label}\\n")
""",
        encoding="utf-8",
    )


def test_wrapper_import_runs_before_icloud_and_sanitizer(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    local_handoff = repo_root / "HANDOFF.md"
    local_handoff.write_text(LOCAL_HANDOFF_TEMPLATE, encoding="utf-8")

    icloud_dir = tmp_path / "icloud"
    icloud_dir.mkdir(parents=True, exist_ok=True)
    icloud_handoff = icloud_dir / "HANDOFF.md"
    icloud_handoff.write_text(ICLOUD_HANDOFF_TEMPLATE, encoding="utf-8")
    os.utime(icloud_handoff, (1_000_000_000, 1_000_000_000))

    order_path = tmp_path / "order.log"

    import_stub = tmp_path / "import_stub.py"
    _write_order_stub(import_stub, "import")

    external_stub = tmp_path / "sync-onepilot-handoff-stub.sh"
    _write_executable(
        external_stub,
        f"""#!/usr/bin/env bash
set -euo pipefail
if [[ -n "${{SYNC_TEST_ORDER_PATH:-}}" ]]; then
  echo icloud >> "$SYNC_TEST_ORDER_PATH"
fi
local_path="${{SYNC_ONEPILOT_LOCAL_HANDOFF_PATH:?}}"
icloud_path="${{SYNC_ONEPILOT_ICLOUD_HANDOFF_PATH:?}}"
mkdir -p "$(dirname "$local_path")" "$(dirname "$icloud_path")"
cat > "$local_path" <<'EOF'
{LOCAL_HANDOFF_TEMPLATE}
EOF
cat > "$icloud_path" <<'EOF'
{ICLOUD_HANDOFF_TEMPLATE}
EOF
touch "$icloud_path"
""",
    )

    sanitizer_stub = tmp_path / "sanitizer_order.py"
    sanitizer_stub.write_text(
        """#!/usr/bin/env python3
import argparse
import os
from pathlib import Path

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--output")
parser.add_argument("--handoff")
parser.add_argument("--repo-root")
args, _unknown = parser.parse_known_args()
order = os.environ.get("SYNC_TEST_ORDER_PATH")
if order:
    Path(order).parent.mkdir(parents=True, exist_ok=True)
    with open(order, "a", encoding="utf-8") as f:
        f.write("sanitize\\n")
if args.output:
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text("SANITIZED_STUB\\n", encoding="utf-8")
""",
        encoding="utf-8",
    )

    result = _run_wrapper(
        {
            "SYNC_ONEPILOT_REPO_ROOT": str(repo_root),
            "SYNC_ONEPILOT_LOCAL_HANDOFF_PATH": str(local_handoff),
            "SYNC_ONEPILOT_ICLOUD_HANDOFF_PATH": str(icloud_handoff),
            "SYNC_ONEPILOT_HANDOFF_SH": str(external_stub),
            "SYNC_CLOUD_HANDOFF_PYTHON_SCRIPT": str(sanitizer_stub),
            "SYNC_CLOUD_HANDOFF_OUTPUT_PATH": str(tmp_path / "docs" / "agent" / "CLOUD_HANDOFF.md"),
            "SYNC_CLOUD_HANDOFF_FETCH": "false",
            "SYNC_CLOUD_AGENT_REPORT_IMPORT": "true",
            "SYNC_CLOUD_AGENT_REPORT_SCRIPT": str(import_stub),
            "SYNC_CLOUD_AGENT_REPORT_FETCH": "false",
            "SYNC_TEST_ORDER_PATH": str(order_path),
        }
    )
    assert result.returncode == 0, f"expected success, got:\\n{result.stdout}\\n{result.stderr}"
    assert order_path.read_text(encoding="utf-8").splitlines() == ["import", "icloud", "sanitize"]


def test_wrapper_stops_before_icloud_when_import_is_unsafe(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    local_handoff = repo_root / "HANDOFF.md"
    local_handoff.write_text(LOCAL_HANDOFF_TEMPLATE, encoding="utf-8")
    icloud_dir = tmp_path / "icloud"
    icloud_dir.mkdir(parents=True, exist_ok=True)
    icloud_handoff = icloud_dir / "HANDOFF.md"
    icloud_handoff.write_text(ICLOUD_HANDOFF_TEMPLATE, encoding="utf-8")
    os.utime(icloud_handoff, (1_000_000_000, 1_000_000_000))

    order_path = tmp_path / "order.log"
    import_stub = tmp_path / "import_fail.py"
    import_stub.write_text(
        """#!/usr/bin/env python3
import os
from pathlib import Path
order = os.environ.get("SYNC_TEST_ORDER_PATH")
if order:
    Path(order).write_text("import\\n", encoding="utf-8")
raise SystemExit(2)
""",
        encoding="utf-8",
    )
    external_stub = tmp_path / "external.sh"
    _write_executable(
        external_stub,
        """#!/usr/bin/env bash
set -euo pipefail
echo icloud >> "${SYNC_TEST_ORDER_PATH:?}"
""",
    )
    sanitizer_stub = tmp_path / "sanitizer.py"
    sanitizer_stub.write_text(
        "#!/usr/bin/env python3\nimport os\nfrom pathlib import Path\n"
        "Path(os.environ['SYNC_TEST_ORDER_PATH']).write_text('sanitize\\n')\n",
        encoding="utf-8",
    )

    result = _run_wrapper(
        {
            "SYNC_ONEPILOT_REPO_ROOT": str(repo_root),
            "SYNC_ONEPILOT_LOCAL_HANDOFF_PATH": str(local_handoff),
            "SYNC_ONEPILOT_ICLOUD_HANDOFF_PATH": str(icloud_handoff),
            "SYNC_ONEPILOT_HANDOFF_SH": str(external_stub),
            "SYNC_CLOUD_HANDOFF_PYTHON_SCRIPT": str(sanitizer_stub),
            "SYNC_CLOUD_HANDOFF_OUTPUT_PATH": str(tmp_path / "out.md"),
            "SYNC_CLOUD_HANDOFF_FETCH": "false",
            "SYNC_CLOUD_AGENT_REPORT_IMPORT": "true",
            "SYNC_CLOUD_AGENT_REPORT_SCRIPT": str(import_stub),
            "SYNC_TEST_ORDER_PATH": str(order_path),
        }
    )
    assert result.returncode != 0
    assert order_path.read_text(encoding="utf-8").splitlines() == ["import"]

