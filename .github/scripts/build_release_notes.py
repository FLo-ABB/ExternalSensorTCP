"""Build the Markdown release notes for a given version.

The notes combine a generated header with the matching ``## X.Y`` section of
``CHANGELOG.md``. The result is written to the requested output file so that it can
be published next to the ZIP archive in the GitHub release.

Usage::

    python .github/scripts/build_release_notes.py <version> <output-path>
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHANGELOG = ROOT / "CHANGELOG.md"


def extract_section(version: str) -> str:
    if not CHANGELOG.is_file():
        raise SystemExit("ERROR: {} not found".format(CHANGELOG))
    text = CHANGELOG.read_text(encoding="utf-8")
    pattern = re.compile(
        r'^##\s+{}\s*$(?P<body>.*?)(?=^##\s+\S|\Z)'.format(re.escape(version)),
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        raise SystemExit(
            "ERROR: no '## {}' section in {}. Add one before releasing.".format(version, CHANGELOG)
        )
    body = match.group("body").strip()
    if not body:
        raise SystemExit("ERROR: the '## {}' section in {} is empty.".format(version, CHANGELOG))
    return body


def build_notes(version: str) -> str:
    return "\n".join([
        "# ExternalSensorTCP v{}".format(version),
        "",
        "Version **{}** as declared in `scripts/ExternalSensorTCP.py` (Sensor Information).".format(version),
        "",
        "## Package",
        "",
        "`ExternalSensorTCP-{}.zip` contains the content of the `scripts/` folder. Extract it into".format(version),
        "`%PROGRAMDATA%\\ABB\\PickMaster\\PMScripts\\`, then declare `ExternalSensorTCP.py` as the",
        "External Sensor script in PickMaster.",
        "",
        "## Changes",
        "",
        extract_section(version),
        "",
    ])


def main(argv) -> int:
    if len(argv) != 3:
        raise SystemExit("Usage: build_release_notes.py <version> <output-path>")
    version, output = argv[1], Path(argv[2])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_notes(version), encoding="utf-8")
    print("Release notes written to {}".format(output))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
