#!/usr/bin/python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Prepare the qualified binary outputs from the pinned Ubuntu source inputs."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

CORE_VERSION = "0.1.0+rogdv8"
GTK_VERSION = "0.15.2-1ubuntu2+rogdv5.3"
SHOWTIME_VERSION = "50.0-2+rogdv5.5"
FIXED_GTK = "4.24.1+ds-1+rogdv5"
FEATURES = "gtk_v4_20,x11egl,x11glx,waylandegl,dmabuf,v1_28"
INPUT_DIR = Path(__file__).with_name("package-inputs")
INPUT_FILES = ("control", "rules", "changelog")
GTK_SOURCE_PACKAGES = ("librust-gst-plugin-gtk4-dev", "gstreamer1.0-gtk4")
OUTPUT_INVENTORY = {
    "gtk": {
        "source": "rust-gst-plugin-gtk4",
        "binary_packages": ["gstreamer1.0-gtk4"],
        "excluded_packages": {
            "librust-gst-plugin-gtk4-dev":
                "This recipe builds the native plugin, not a Debian Rust crate SDK."
        },
    },
    "showtime": {"source": "showtime", "binary_packages": ["showtime"]},
}

CARGO_CONFIG = '''[source.crates-io]
replace-with = "vendored-sources"
[source.vendored-sources]
directory = "debian/missing-sources"
'''

GTK_RULES = '''#!/usr/bin/make -f
include /usr/share/dpkg/architecture.mk

# Defaults are source-owned and removed by clean. External overrides must name
# task-owned absolute paths; their owner is responsible for cache retention.
ifneq ($(strip $(GTK_DOVI_CARGO_HOME)),)
ifeq ($(filter /%,$(GTK_DOVI_CARGO_HOME)),)
$(error GTK_DOVI_CARGO_HOME must be an absolute task-owned path)
endif
export CARGO_HOME = $(GTK_DOVI_CARGO_HOME)
else
export CARGO_HOME = $(CURDIR)/debian/cargo_home
endif
ifneq ($(strip $(GTK_DOVI_CARGO_TARGET_DIR)),)
ifeq ($(filter /%,$(GTK_DOVI_CARGO_TARGET_DIR)),)
$(error GTK_DOVI_CARGO_TARGET_DIR must be an absolute task-owned path)
endif
export CARGO_TARGET_DIR = $(GTK_DOVI_CARGO_TARGET_DIR)
else
export CARGO_TARGET_DIR = $(CURDIR)/target
endif
export CARGO_BUILD_JOBS = 1
export CARGO_PROFILE_RELEASE_LTO = false
FEATURES = @FEATURES@

%:
\tdh $@ --buildsystem=cargo

override_dh_auto_configure:
\ttest -f .cargo/config.toml
\ttest -d debian/missing-sources

override_dh_auto_build:
\tcargo build --offline --release -j1 --features $(FEATURES)

override_dh_auto_install:
\tinstall -D "$(CARGO_TARGET_DIR)/release/libgstgtk4.so" debian/tmp/usr/lib/$(DEB_HOST_MULTIARCH)/gstreamer-1.0/libgstgtk4.so

override_dh_auto_test:
ifeq (,$(filter nocheck,$(DEB_BUILD_OPTIONS)))
\tcargo test --offline --release -j1 --features $(FEATURES)
else
\t@echo "Skipping unit tests (DEB_BUILD_OPTIONS=nocheck)"
endif

override_dh_auto_clean:
\trm -rf -- target debian/cargo_home

override_dh_clean:
\t# Vendor Cargo.toml.orig files are authenticated source/checksum inputs.
\tdh_clean --exclude=debian/missing-sources

override_dh_shlibdeps:
\tdh_shlibdeps $(if $(GTK_DOVI_CORE_LIBDIR),-l$(GTK_DOVI_CORE_LIBDIR))
'''.replace("@FEATURES@", FEATURES)


class PreparationError(Exception):
    pass


def qualified_pipeline():
    """Use actual binary metadata, grouped by its independently built source."""
    expected = {
        "gst-plugins-base1.0": {
            "gstreamer1.0-gl", "libgstreamer-gl1.0-0",
            "libgstreamer-plugins-base1.0-0",
        },
        "gst-plugins-good1.0": {"gstreamer1.0-plugins-good"},
        "gst-plugins-bad1.0": {
            "gstreamer1.0-plugins-bad", "gstreamer1.0-plugins-extra",
        },
        "gst-libav1.0": {"gstreamer1.0-libav"},
    }
    families = json.loads((INPUT_DIR / "qualified-pipeline.json").read_text())["source_families"]
    if set(families) != set(expected):
        raise PreparationError("unrecognized qualified GStreamer source families")
    versions = {}
    for source, names in expected.items():
        family = families[source]
        if not family["source_version"] or set(family["binary_packages"]) != names:
            raise PreparationError(f"unrecognized binary inventory for {source}")
        for name, binary in family["binary_packages"].items():
            if not binary["version"] or not re.fullmatch(r"[0-9a-f]{64}", binary["deb_sha256"]):
                raise PreparationError(f"incomplete qualified binary metadata: {name}")
            versions[name] = binary["version"]
    return versions


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise PreparationError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def field_pattern(name):
    return re.compile(rf"^{re.escape(name)}:[^\n]*(?:\n[ \t][^\n]*)*", re.M)


def field_text(stanza, name):
    matches = list(field_pattern(name).finditer(stanza))
    if len(matches) != 1:
        raise PreparationError(f"{name}: expected one field, found {len(matches)}")
    return matches[0].group()


def field_value(stanza, name):
    return " ".join(field_text(stanza, name).split(":", 1)[1].split())


def replace_field(stanza, name, replacement):
    # Locate exactly one complete field; never consume following sibling fields.
    old = field_text(stanza, name)
    return replace_once(stanza, old, replacement, name)


def control_stanzas(text, source, expected_packages):
    stanzas = text.rstrip("\n").split("\n\n")
    if field_value(stanzas[0], "Source") != source:
        raise PreparationError(f"expected Source: {source}")
    packages = [field_value(stanza, "Package") for stanza in stanzas[1:]]
    if tuple(packages) != tuple(expected_packages):
        raise PreparationError(f"{source}: unexpected binary inventory {packages!r}")
    return stanzas


def gtk_control(original):
    qualified = qualified_pipeline()
    source, rust_sdk, plugin = control_stanzas(
        original, "rust-gst-plugin-gtk4", GTK_SOURCE_PACKAGES
    )
    # The excluded SDK stanza is named and validated above; no tail slicing.
    source = replace_field(source, "Build-Depends", "Build-Depends: " + ", ".join([
        "debhelper-compat (= 13)", "cargo:native", "rustc:native (>= 1.92)",
        "pkgconf", "libgtk-4-dev (>= 4.20)",
        "libgstreamer-plugins-base1.0-dev (>= 1.28.7)",
        f"libgstgtk-dovi-core-dev (= {CORE_VERSION})",
    ]))
    depends = field_text(plugin, "Depends")
    depends = replace_once(
        depends, " ${misc:Depends},",
        f" libgtk-4-1 (= {FIXED_GTK}),\n"
        f" gstreamer1.0-gl (= {qualified['gstreamer1.0-gl']}),\n"
        f" libgstreamer-gl1.0-0 (= {qualified['libgstreamer-gl1.0-0']}),\n"
        f" libgstreamer-plugins-base1.0-0 (= {qualified['libgstreamer-plugins-base1.0-0']}),\n"
        f" libgstgtk-dovi-core0 (= {CORE_VERSION}),\n ${{misc:Depends}},",
        "gtk plugin runtime dependencies",
    )
    plugin = replace_field(plugin, "Depends", depends)
    return source + "\n\n" + plugin + "\n"


def showtime_control(original):
    qualified = qualified_pipeline()
    source, binary = control_stanzas(original, "showtime", ("showtime",))
    depends = field_text(binary, "Depends")
    depends = replace_once(
        depends, " gstreamer1.0-gtk4,",
        f" gstreamer1.0-gtk4 (= {GTK_VERSION}),\n"
        f" gstreamer1.0-gtk-dovi (= {CORE_VERSION}),\n"
        f" libgtk-4-1 (= {FIXED_GTK}),",
        "showtime sink dependencies",
    )
    depends = replace_once(
        depends, " gir1.2-gtk-4.0 (>= 4.20),",
        f" gir1.2-gtk-4.0 (>= {FIXED_GTK}),", "showtime GTK introspection",
    )
    for name in ("gstreamer1.0-gl", "gstreamer1.0-plugins-good"):
        depends = replace_once(
            depends, f" {name},", f" {name} (= {qualified[name]}),",
            f"qualified {name}",
        )
    producer_lines = []
    for name in ("gstreamer1.0-plugins-bad", "gstreamer1.0-plugins-extra", "gstreamer1.0-libav"):
        if re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", depends):
            raise PreparationError(f"unexpected existing producer dependency: {name}")
        producer_lines.append(f" {name} (= {qualified[name]}),\n")
    depends = replace_once(
        depends, " ${gst-plugins-extra:Depends},",
        "".join(producer_lines) + " ${gst-plugins-extra:Depends},",
        "qualified producer families",
    )
    binary = replace_field(binary, "Depends", depends)
    return source + "\n\n" + binary + "\n"


def changelog(source, version, bullets, original):
    entries = "".join(f"  * {line}\n" for line in bullets)
    return (f"{source} ({version}) unstable; urgency=medium\n\n" + entries +
            "\n -- ROG HDR contributors <rog-hdr@invalid>  Sun, 08 Nov 2026 00:00:00 +0000\n\n" + original)


def pinned_inputs():
    manifest = json.loads((INPUT_DIR / "provenance.json").read_text())
    result = {}
    for label in ("gtk", "showtime"):
        result[label] = {}
        for name in INPUT_FILES:
            data = (INPUT_DIR / label / name).read_bytes()
            expected = manifest[label]["files_sha256"][name]
            if hashlib.sha256(data).hexdigest() != expected:
                raise PreparationError(f"modified input fixture: {label}/{name}")
            result[label][name] = data.decode()
    return result


def require_known_current(path, original, generated):
    if not path.is_file():
        raise PreparationError(f"missing source input: {path}")
    if path.read_text() not in (original, generated):
        raise PreparationError(
            f"unrecognized edits in {path}; review them, then restore the pinned "
            "original before preparation (including when migrating the old recipe)"
        )


def prepare(workspace):
    inputs = pinned_inputs()
    gtk = workspace / "source"
    showtime = workspace / "showtime-50.0"
    backups = workspace / "package-originals"
    outputs = {
        gtk / "debian/control": gtk_control(inputs["gtk"]["control"]),
        gtk / "debian/rules": GTK_RULES,
        gtk / "debian/changelog": changelog(
            "rust-gst-plugin-gtk4", GTK_VERSION, [
                "Preserve native 16-bit mapped pictures and retarget visible paused frames.",
                "Publish completed pictures to each view's declared HDR or SDR destination.",
                "Build full plugin features offline from the Ubuntu vendored source.",
            ], inputs["gtk"]["changelog"]),
        showtime / "debian/control": showtime_control(inputs["showtime"]["control"]),
        showtime / "debian/rules": inputs["showtime"]["rules"],
        showtime / "debian/changelog": changelog(
            "showtime", SHOWTIME_VERSION,
            ["Bind Dolby streams to their native surface target and HDR lease.",
             "Require the matching sink and mapper with paused overlay preservation.",
             "Start the shared producer with an explicit SDR destination."],
            inputs["showtime"]["changelog"]),
    }
    # Complete all validation before creating backups or changing source files.
    for label, source in (("gtk", gtk), ("showtime", showtime)):
        for name in INPUT_FILES:
            original = inputs[label][name]
            path = source / "debian" / name
            require_known_current(path, original, outputs[path])
            backup = backups / f"{label}-{name}"
            if backup.exists() and backup.read_text() != original:
                raise PreparationError(f"unrecognized original backup: {backup}")
    cargo_config = gtk / ".cargo/config.toml"
    if cargo_config.exists() and cargo_config.read_text() != CARGO_CONFIG:
        raise PreparationError(f"unexpected Cargo source configuration: {cargo_config}")
    shlibs = gtk / "debian/shlibs.local"
    shlibs_text = shlibs.read_text() if shlibs.exists() else ""
    core_line = f"libgstgtkdovicore 0 libgstgtk-dovi-core0 (= {CORE_VERSION})"
    existing = [line for line in shlibs_text.splitlines()
                if re.match(r"^libgstgtkdovicore\s", line)]
    if existing not in ([], [core_line]):
        raise PreparationError(f"unexpected core shlibs declaration: {shlibs}")
    if not existing:
        shlibs_text = shlibs_text.rstrip("\n") + ("\n" if shlibs_text else "") + core_line + "\n"
    outputs[cargo_config] = CARGO_CONFIG
    outputs[shlibs] = shlibs_text

    backups.mkdir(exist_ok=True)
    for label, source in (("gtk", gtk), ("showtime", showtime)):
        for name in INPUT_FILES:
            backup = backups / f"{label}-{name}"
            if not backup.exists():
                # Current input can already equal a generated file on rerun.
                backup.write_text(inputs[label][name])
                shutil.copymode(source / "debian" / name, backup)
    for path, text in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    (gtk / "debian/rules").chmod(0o755)
    inventory = {
        "outputs": OUTPUT_INVENTORY,
        "source_metadata_sha256": {
            str(path.relative_to(workspace)): hashlib.sha256(text.encode()).hexdigest()
            for path, text in outputs.items()
        },
    }
    (workspace / "package-output-inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
    print("Prepared declared GTK plugin and Showtime binary outputs from pinned Ubuntu inputs.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    args = parser.parse_args()
    try:
        prepare(args.workspace.resolve())
    except (PreparationError, OSError, ValueError) as error:
        parser.exit(1, f"package preparation refused: {error}\n")


if __name__ == "__main__":
    main()
