#!/usr/bin/env python3
"""Generate the apt preferences file for the rog-hdr origin from the manifest.

    packaging/delivery/pins.py              # print it
    packaging/delivery/pins.py --write      # update rog-apt-config/preferences.d/rog-hdr
    packaging/delivery/pins.py --check      # fail if the checked-in file differs

Listed binaries that shadow Ubuntu get 1001, other listed binaries 500, and
every other name from the origin -1. The output depends only on the manifest.
"""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import delivery  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", default=str(delivery.MANIFEST))
    parser.add_argument("--output", default=str(delivery.PIN_FILE))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    manifest = delivery.load_manifest(args.manifest)
    errors = delivery.validate(manifest)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    pins = delivery.generate_pins(manifest)
    output = Path(args.output)
    if args.write:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(pins, encoding="utf-8")
    elif args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != pins:
            print(f"{output} differs from the manifest: run packaging/delivery/pins.py --write", file=sys.stderr)
            return 1
    else:
        sys.stdout.write(pins)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
