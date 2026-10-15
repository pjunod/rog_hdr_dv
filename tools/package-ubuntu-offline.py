#!/usr/bin/env python3
"""Build an amd64 Ubuntu Mutter candidate without APT or host installation.

Use in an owned native x86_64 disposable builder. Exact source trees and library
package SHA256s are mandatory. This constructs packages with nocheck; it neither
runs acceptance tests nor installs anything. The only supported staged dependency
exception is libdisplay-info-dev, verified from the matching supplied packages.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tarfile
import time

ORIG_SHA256 = "5d28f3ae225692428fcafb96500d673f34328b698b86960c9c1460d0b1d983b3"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def output(argv, cwd=None):
    return subprocess.check_output(argv, cwd=cwd, text=True).strip()


def control(path, field):
    return output(["dpkg-deb", "-f", str(path), field])


def staged_dependency_exception(returncode, stdout, version):
    if returncode == 0:
        return None
    match = re.fullmatch(r"dpkg-checkbuilddeps: error: unmet build dependencies: libdisplay-info-dev \(>= ([^)]+)\)\s*", stdout)
    if not match:
        raise ValueError("Unmet dependencies beyond the privately staged library: " + stdout)
    floor = match[1]
    subprocess.run(["dpkg", "--compare-versions", version, "ge", floor], check=True)
    return {"package": "libdisplay-info-dev", "minimum": floor,
            "staged_version": version, "installed_status_changed": False}


def build(args):
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ValueError("Requires native x86_64 Linux, not emulation")
    if os.geteuid() == 0:
        raise ValueError("Run unprivileged in the isolated builder")
    source = args.source.resolve()
    out = args.out.resolve()
    if out.exists() or out == source or source in out.parents or out in source.parents:
        raise ValueError("Use a fresh, separate owned output directory")
    if output(["git", "-C", str(source), "rev-parse", "HEAD^{tree}"]) != args.tree:
        raise ValueError("Source tree differs from the explicit pin")
    if output(["git", "-C", str(source), "diff", "--name-only", "HEAD"]):
        raise ValueError("Tracked source changes must be committed first")
    if sha256(args.orig) != ORIG_SHA256:
        raise ValueError("Mutter orig source differs from the pinned archive")
    packages = [(args.library_dev, args.dev_sha256, "libdisplay-info-dev"),
                (args.library_runtime, args.runtime_sha256, "libdisplay-info3")]
    for path, digest, package in packages:
        if sha256(path) != digest or control(path, "Package") != package:
            raise ValueError("Supplied library package does not match its hash/name")
        if control(path, "Architecture") != "amd64":
            raise ValueError("Native compiler needs matching amd64 library inputs")
    version = control(args.library_dev, "Version")
    if control(args.library_runtime, "Version") != version:
        raise ValueError("Development/runtime library package versions differ")
    if control(args.library_runtime, "Provides") != "libdisplay-info3-native-hdr-api (= 2)":
        raise ValueError("Matching native HDR API virtual dependency is required")
    out.mkdir(parents=True)
    work = out / "work"
    work.mkdir()
    tree = work / "mutter-51.0"
    tree.mkdir()
    source_tar = out / "source.tar"
    with source_tar.open("wb") as target:
        subprocess.run(["git", "-C", str(source), "archive", "HEAD"], stdout=target, check=True)
    with tarfile.open(source_tar) as archive:
        archive.extractall(tree, filter="data")
    # The imported source is already quilt-applied; preserve its actual state,
    # not fabricated applied-patch markers or a modified host package database.
    if not (source / ".pc/applied-patches").is_file():
        raise ValueError("Actual dpkg-source quilt metadata is required")
    shutil.copytree(source / ".pc", tree / ".pc")
    with tarfile.open(args.orig) as archive:
        for member in archive.getmembers():
            if not member.name.startswith("mutter-51.0/subprojects/gvdb/"):
                continue
            member.name = member.name.removeprefix("mutter-51.0/")
            archive.extract(member, tree, filter="data")
    prefix = out / "library-prefix"
    for path, _, _ in packages:
        subprocess.run(["dpkg-deb", "-x", str(path), str(prefix)], check=True)
    pcs = prefix / "usr/lib/x86_64-linux-gnu/pkgconfig"
    if not (pcs / "libdisplay-info.pc").is_file():
        raise ValueError("Staged package lacks libdisplay-info pkg-config metadata")
    # Relocate extracted build metadata only. The .deb bytes stay immutable.
    for pc in pcs.glob("*.pc"):
        pc.write_text(pc.read_text().replace("prefix=/usr\n", "prefix=" + str(prefix / "usr") + "\n"))
    env = os.environ.copy()
    env.update(LC_ALL="C", DEB_BUILD_OPTIONS="nocheck parallel=2",
               DEB_BUILD_PROFILES="nocheck", PKG_CONFIG_PATH=str(pcs),
               LD_LIBRARY_PATH=str(prefix / "usr/lib/x86_64-linux-gnu"))
    # No private rpath may be introduced into the delivered packages.
    env.pop("LDFLAGS", None)
    env.pop("CFLAGS", None)
    audit = subprocess.run(["dpkg-checkbuilddeps", "-Pnocheck"], cwd=tree,
                           env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / "build-dependencies.txt").write_text(audit.stdout)
    exception = staged_dependency_exception(audit.returncode, audit.stdout, version)
    # dh_shlibdeps resolves this private library via LD_LIBRARY_PATH. Bind its
    # dependency to the actual supplied hdr9 package, not the stock host version.
    shlibs = tree / "debian/shlibs.local"
    if shlibs.exists():
        raise ValueError("Do not overwrite existing shlibs.local policy")
    shlibs.write_text("libdisplay-info 3 libdisplay-info3 (>= " + version + ")\n")
    command = ["dpkg-buildpackage", "-b", "-us", "-uc"]
    if exception is not None:
        command.append("-d")  # Only after the exact, independently verified audit above.
    start = time.monotonic()
    with (out / "build.log").open("w") as log:
        result = subprocess.run(command, cwd=tree, env=env, stdout=log, stderr=subprocess.STDOUT)
    receipt = {"schema": 1, "source_tree": args.tree, "source_tar_sha256": sha256(source_tar),
               "architecture": "x86_64", "units_executed": 0, "installed": False,
               "command": command, "seconds": time.monotonic() - start,
               "exit_code": result.returncode, "build_log_sha256": sha256(out / "build.log"),
               "dependency_exception": exception, "shlibs_local": shlibs.read_text(),
               "library_inputs": [{"file": p.name, "sha256": h} for p, h, _ in packages],
               "packages": []}
    if result.returncode == 0:
        for deb in sorted(work.glob("*.deb")):
            target = out / deb.name
            shutil.copy2(deb, target)
            receipt["packages"].append({"file": target.name, "bytes": target.stat().st_size,
                                         "sha256": sha256(target),
                                         "control": output(["dpkg-deb", "-f", str(target)])})
        for artifact in sorted(work.glob("*.changes")) + sorted(work.glob("*.buildinfo")):
            shutil.copy2(artifact, out / artifact.name)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    if result.returncode:
        raise subprocess.CalledProcessError(result.returncode, command)
    if not receipt["packages"]:
        raise ValueError("Successful command did not produce binary packages")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("tree")
    parser.add_argument("orig", type=Path)
    parser.add_argument("library_dev", type=Path)
    parser.add_argument("dev_sha256")
    parser.add_argument("library_runtime", type=Path)
    parser.add_argument("runtime_sha256")
    parser.add_argument("out", type=Path)
    build(parser.parse_args())


if __name__ == "__main__":
    main()
