"""Extract and validate the ExternalSensorTCP version declared in the source code.

The single source of truth is the ``version`` attribute of the ``ExternalSensorTCP``
class in ``scripts/ExternalSensorTCP.py`` (the value exposed as Sensor Information in
PickMaster). The version must follow the ``X.Y`` scheme:

* ``X`` (major): new features
* ``Y`` (minor): bug fixes

Prints the version on stdout and, when running inside GitHub Actions, writes it to
``$GITHUB_OUTPUT`` as ``version``.
"""
import os
import re
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "scripts" / "ExternalSensorTCP.py"
VERSION_PATTERN = re.compile(r'^\s{4}version\s*=\s*["\'](?P<version>[^"\']+)["\']', re.MULTILINE)
VERSION_XY = re.compile(r'^\d+\.\d+$')


def read_version() -> str:
    text = SOURCE.read_text(encoding="utf-8")
    match = VERSION_PATTERN.search(text)
    if match is None:
        raise SystemExit("ERROR: no 'version' attribute found in {}".format(SOURCE))
    version = match.group("version").strip()
    if not VERSION_XY.match(version):
        raise SystemExit("ERROR: version '{}' in {} does not match the X.Y scheme".format(version, SOURCE))
    return version


def main() -> int:
    version = read_version()
    print(version)
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write("version={}\n".format(version))
    return 0


if __name__ == "__main__":
    sys.exit(main())
