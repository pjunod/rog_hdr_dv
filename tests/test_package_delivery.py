"""Manifest, pins and publisher for the rog-hdr APT repository.

The publisher runs against tests/delivery_fakes.py: a local ssh and an aptly
double whose state lives in a scratch directory. No test contacts a host.
"""

import base64
import copy
import datetime
import hashlib
import io
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

REPOSITORY = Path(__file__).resolve().parents[1]
DELIVERY = REPOSITORY / "packaging" / "delivery"
FAKES = Path(__file__).resolve().parent / "delivery_fakes.py"
sys.path.insert(0, str(DELIVERY))
import delivery  # noqa: E402
import publish  # noqa: E402


def tar_bytes(members, compression="gz"):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode=f"w:{compression}") as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size, info.mtime = len(data), 0
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def ar_member(name, data):
    header = f"{name:<16}{0:<12}{0:<6}{0:<6}{100644:<8}{len(data):<10}`\n".encode()
    return header + data + (b"\n" if len(data) & 1 else b"")


def make_deb(directory, name, version, arch, source=None, depends=None, multiarch=None,
             files=None, compression="gz"):
    control = [f"Package: {name}", f"Version: {version}", f"Architecture: {arch}",
               "Maintainer: Test <test@invalid>", "Description: test package", " Long text."]
    if source:
        control.insert(1, f"Source: {source}")
    if depends:
        control.append(f"Depends: {depends}")
    if multiarch:
        control.append(f"Multi-Arch: {multiarch}")
    files = files if files is not None else {f"./usr/share/doc/{name}/copyright": b"text\n"}
    body = (b"!<arch>\n" + ar_member("debian-binary", b"2.0\n")
            + ar_member(f"control.tar.{compression}", tar_bytes({"./control": ("\n".join(control) + "\n").encode()}, compression))
            + ar_member(f"data.tar.{compression}", tar_bytes(files, compression)))
    path = Path(directory) / f"{name}_{version.split(':')[-1]}_{arch}.deb"
    path.write_bytes(body)
    return path


class ReleaseIntakeTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("fetch_release", DELIVERY / "forgejo-release.py")
        self.fetch = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.fetch)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.output = root / "received"
        self.package = make_deb(root, "plurx-player", "0.5.8-1", "amd64")
        self.server = "https://forge.example.invalid"
        self.tag = "plurx-player-deb-0.5.8-1"
        self.receipt = "0" * 40
        api = f"{self.server}/api/v1/repos/noirr/plurx"
        download_path = f"{self.server}/noirr/plurx/releases/download/{self.tag}"
        self.asset = f"{download_path}/{self.package.name}"
        self.checksums = f"{download_path}/SHA256SUMS"
        self.release_url = f"{api}/releases/tags/{self.tag}"
        self.routes = {
            self.release_url: json.dumps({
                "draft": False, "tag_name": self.tag, "body": f"Source commit `{self.receipt}`.",
                "assets": [
                    {"name": self.package.name, "type": "attachment"},
                    {"name": "SHA256SUMS", "type": "attachment"},
                ],
            }).encode(),
            f"{api}/tags/{self.tag}": json.dumps({"commit": {"sha": self.receipt}}).encode(),
            self.checksums: f"{publish.sha256(self.package)}  {self.package.name}\n".encode(),
            self.asset: self.package.read_bytes(),
        }

    def retrieve(self):
        def response(request, timeout):
            self.assertEqual(request.get_header("Authorization"), "token local-fixture")
            return io.BytesIO(self.routes[request.full_url])

        with patch.object(self.fetch, "build_opener") as opener:
            opener.return_value.open.side_effect = response
            self.fetch.retrieve(delivery.load_manifest(), "plurx", self.tag, self.output,
                                self.server, "local-fixture")

    def test_release_preserves_verified_bytes_and_commit(self):
        self.retrieve()
        self.assertEqual((self.output / self.package.name).read_bytes(), self.package.read_bytes())
        receipt = json.loads((self.output / "release.json").read_text())
        self.assertEqual(receipt["source_commit"], self.receipt)

    def test_failed_checksum_keeps_output_absent(self):
        self.routes[self.asset] = b"changed bytes"
        with self.assertRaisesRegex(ValueError, "differs from the released digest"):
            self.retrieve()
        self.assertFalse(self.output.exists())

    def test_link_asset_is_rejected_before_request(self):
        release = json.loads(self.routes[self.release_url])
        release["assets"][0]["type"] = "external"
        self.routes[self.release_url] = json.dumps(release).encode()
        with self.assertRaisesRegex(ValueError, "not an uploaded Forgejo asset"):
            self.retrieve()
        self.assertFalse(self.output.exists())


    def test_publisher_refuses_modified_fetched_bytes(self):
        self.retrieve()
        package = self.output / self.package.name
        package.write_bytes(b"changed after receipt")
        with self.assertRaisesRegex(ValueError, "differ from the verified release receipt"):
            publish.verify_release_receipt(self.output, [package], delivery.load_manifest(), "plurx", required=True)


    def test_attach_publishes_only_after_the_package_and_checksum_upload(self):
        commit = "a" * 40
        checksums = self.package.parent / "SHA256SUMS"
        checksums.write_text(f"{publish.sha256(self.package)}  {self.package.name}\n")
        calls = []
        api = f"{self.server}/api/v1/repos/noirr/plurx"
        uploads = []
        draft = True

        def response(request, timeout):
            nonlocal draft
            self.assertEqual(request.get_header("Authorization"), "token local-fixture")
            url, method = request.full_url, request.get_method()
            calls.append((method, url))
            if url == api:
                return io.BytesIO(b'{"private":true}')
            if url == f"{api}/tags/{self.tag}":
                if draft:
                    raise HTTPError(url, 404, "not published", {}, io.BytesIO())
                return io.BytesIO(json.dumps({"commit": {"sha": commit}}).encode())
            if url == self.release_url:
                raise HTTPError(url, 404, "no release", {}, io.BytesIO())
            if url == f"{api}/releases" and method == "POST":
                request_body = json.loads(request.data)
                self.assertEqual(request_body["target_commitish"], commit)
                self.assertTrue(request_body["draft"])
                return io.BytesIO(json.dumps({"id": 1, "assets": [], **request_body}).encode())
            if url.startswith(f"{api}/releases/1/assets?name=") and method == "POST":
                uploads.append(url.rsplit("=", 1)[-1])
                return io.BytesIO()
            if url == f"{api}/releases/1" and method == "PATCH":
                self.assertEqual(uploads, [self.package.name, "SHA256SUMS"])
                self.assertEqual(json.loads(request.data), {"draft": False})
                draft = False
                return io.BytesIO()
            self.fail(f"Unexpected fixture request {method} {url}")

        with patch.dict(os.environ, FORGEJO_SHA=commit, FORGEJO_REPOSITORY="noirr/plurx"):
            with patch.object(self.fetch, "build_opener") as opener:
                opener.return_value.open.side_effect = response
                self.fetch.attach(delivery.load_manifest(), "plurx", self.package.parent, commit,
                                  self.server, "local-fixture")
        self.assertFalse(draft)
        self.assertEqual(calls[-1], ("GET", f"{api}/tags/{self.tag}"))


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.manifest = delivery.load_manifest()

    def test_checked_in_manifest_is_valid(self):
        self.assertEqual(delivery.validate(self.manifest, root=REPOSITORY), [])

    def test_binaries_are_unique(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["packages"][1]["binaries"].append(manifest["packages"][0]["binaries"][0])
        self.assertTrue(any("more than one source" in e for e in delivery.validate(manifest)))

    def test_unconfirmed_name_cannot_also_be_published(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["packages"][0]["binaries"].append("network-manager")
        self.assertTrue(any("both published and unconfirmed" in e for e in delivery.validate(manifest)))

    def test_schema_rejects_unknown_class_and_missing_series(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["packages"][0]["class"] = "vendored"
        built = next(e for e in manifest["packages"] if e["class"] == "built" and e["source"] != manifest["packages"][0]["source"])
        del built["series"]
        errors = delivery.validate(manifest)
        self.assertTrue(any("class must be" in e for e in errors))
        self.assertTrue(any("needs a series" in e for e in errors))

    def test_kernels_are_imported_without_shadowing(self):
        kernels = [e for e in self.manifest["packages"] if e.get("kernel")]
        self.assertTrue(kernels)
        for entry in kernels:
            self.assertEqual(entry["class"], "imported")
            self.assertFalse(any(n in ("linux-image-generic", "linux-generic") for n in entry["binaries"]))

    def test_vendor_and_unowned_packages_are_not_published(self):
        index = delivery.binary_index(self.manifest)
        for name in ("google-chrome-stable", "steam-launcher", "mullvad-vpn", "mainline", "libbz2-1.0",
                     "nvidia-container-toolkit", "asus-rog-tools", "network-manager", "libnm0"):
            self.assertNotIn(name, index)

    def test_pins_are_deterministic_and_match_checked_in(self):
        first = delivery.generate_pins(self.manifest)
        shuffled = copy.deepcopy(self.manifest)
        shuffled["packages"].reverse()
        for entry in shuffled["packages"]:
            entry["binaries"].reverse()
        self.assertEqual(first, delivery.generate_pins(shuffled))
        self.assertEqual(first, delivery.PIN_FILE.read_text(encoding="utf-8"))

    def test_pin_priorities(self):
        pins = delivery.generate_pins(self.manifest)
        stanzas = [dict(line.split(": ", 1) for line in block.splitlines() if ": " in line and not line.startswith("#"))
                   for block in pins.split("\n\n") if "Pin-Priority" in block]
        by_priority = {s["Pin-Priority"]: s["Package"].split() for s in stanzas}
        self.assertIn("mutter:amd64", by_priority["1001"])
        self.assertIn("mutter-common:any", by_priority["1001"])
        self.assertIn("libdisplay-info3:i386", by_priority["1001"])
        self.assertNotIn("libavfilter11:i386", by_priority["1001"])
        self.assertIn("plurx-player:amd64", by_priority["500"])
        self.assertIn("linux-image-7.3.0-nativehdr3:amd64", by_priority["500"])
        self.assertEqual(by_priority["-1"], ["*"])
        self.assertTrue(all(s["Pin"] == "release o=rog-hdr" for s in stanzas))

    def test_config_package_carries_no_credential_and_runs_no_apt(self):
        package = DELIVERY / "rog-apt-config"
        debian = package / "debian"
        for script in ("preinst", "postinst", "prerm", "postrm"):
            self.assertFalse((debian / script).exists(), script)
        sources = (debian / "rog-hdr.sources.in").read_text()
        fingerprint = self.manifest["repository"]["signing_key"]
        self.assertIn(f"Signed-By: /usr/share/keyrings/rog-hdr-archive-keyring.asc {fingerprint}\n", sources)
        self.assertIn("URIs: @REPOSITORY_URL@", sources)
        self.assertNotIn("http:", sources)
        self.assertNotIn("https:", sources)
        self.assertEqual((debian / "signing-key-fingerprint").read_text().strip(),
                         self.manifest["repository"]["signing_key"])


    def test_config_source_uses_a_supplied_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            debian = DELIVERY / "rog-apt-config" / "debian"
            for name in ("render-source.py", "rog-hdr.sources.in"):
                (root / name).write_bytes((debian / name).read_bytes())
            script = [sys.executable, str(root / "render-source.py")]
            env = dict(os.environ, ROG_APT_REPOSITORY_URL="https://apt.example.invalid/rog")
            subprocess.run(script, env=env, check=True)
            self.assertIn("URIs: https://apt.example.invalid/rog/\n", (root / "rog-hdr.sources").read_text())
            for invalid in ("", "https://user:pw@apt.example.invalid", "https://apt.example.invalid\nEnabled: no"):
                with self.subTest(uri=invalid):
                    env["ROG_APT_REPOSITORY_URL"] = invalid
                    result = subprocess.run(script, env=env, capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0)


class OpenPGPTests(unittest.TestCase):
    def test_fingerprint_of_a_v4_key_packet(self):
        body = bytes([4]) + (0).to_bytes(4, "big") + bytes([22]) + b"\x09+\x06\x01\x04\x01\xdaG\x0f\x01" + b"\x01\x07" + b"@" + bytes(32)
        packet = bytes([0x99]) + len(body).to_bytes(2, "big") + body  # old-format tag 6, two-byte length
        armored = ("-----BEGIN PGP PUBLIC KEY BLOCK-----\n\n"
                   + base64.b64encode(packet).decode() + "\n=AAAA\n-----END PGP PUBLIC KEY BLOCK-----\n")
        expected = hashlib.sha1(b"\x99" + len(body).to_bytes(2, "big") + body).hexdigest().upper()
        self.assertEqual(delivery.openpgp_fingerprint(armored), expected)


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.dir = Path(self.temporary.name)
        self.manifest = delivery.load_manifest()

    def check(self, paths, project="rog_hdr_dv", allow=False):
        return publish.verify(self.manifest, project, [delivery.Deb(p) for p in paths], allow)

    def libdisplay(self, version="0.3.0-1+nativehdr18", i386_files=None, compression="gz"):
        shared = {"./usr/share/doc/libdisplay-info3/copyright": b"same\n"}
        pair = [make_deb(self.dir, "libdisplay-info3", version, "amd64", "libdisplay-info", multiarch="same",
                         files=dict(shared, **{"./usr/lib/x86_64-linux-gnu/libdisplay-info.so.3": b"64"}),
                         compression=compression),
                make_deb(self.dir, "libdisplay-info3", version, "i386", "libdisplay-info", multiarch="same",
                         files=i386_files or dict(shared, **{"./usr/lib/i386-linux-gnu/libdisplay-info.so.3": b"32"}),
                         compression=compression)]
        return pair + [make_deb(self.dir, name, version, arch, "libdisplay-info")
                       for name in ("libdisplay-info-bin", "libdisplay-info-dev")
                       for arch in ("amd64", "i386")]

    def test_complete_identical_pair_passes(self):
        errors, _ = self.check(self.libdisplay())
        self.assertEqual(errors, [])

    def test_xz_and_zstd_members_are_read(self):
        self.assertEqual(self.check(self.libdisplay(compression="xz"))[0], [])
        if sys.version_info >= (3, 14):
            other = Path(self.temporary.name) / "zst"
            other.mkdir()
            self.dir = other
            self.assertEqual(self.check(self.libdisplay(compression="zst"))[0], [])

    def test_incomplete_pair_is_rejected(self):
        errors, _ = self.check(self.libdisplay()[:1])
        self.assertTrue(any("pair is incomplete, missing i386" in e for e in errors), errors)

    def test_differing_shared_file_is_rejected(self):
        files = {"./usr/share/doc/libdisplay-info3/copyright": b"different\n"}
        errors, _ = self.check(self.libdisplay(i386_files=files))
        self.assertTrue(any("copyright differs between amd64 and i386" in e for e in errors), errors)

    def test_unlisted_unconfirmed_wrong_project_arch_and_source(self):
        paths = [make_deb(self.dir, "unknown-tool", "1", "amd64"),
                 make_deb(self.dir, "network-manager", "1.58.1-1ubuntu3+rogsleep2", "amd64"),
                 make_deb(self.dir, "plurx-player", "0.5.7-1", "amd64"),
                 make_deb(self.dir, "mutter", "51.0-1ubuntu3+nativehdr18", "i386"),
                 make_deb(self.dir, "libdovi3", "3.3.2-3+rogdv2", "amd64", source="other-source")]
        errors, _ = self.check(paths)
        text = "\n".join(errors)
        self.assertIn("unknown-tool is not published (not in the manifest)", text)
        self.assertIn("network-manager is not published (unconfirmed:", text)
        self.assertIn("plurx-player belongs to project plurx, not rog_hdr_dv", text)
        self.assertIn("architecture i386 is not listed for mutter", text)
        self.assertIn("Source other-source is not the manifest's rust-dolby-vision", text)

    def test_source_architectures_do_not_extend_sibling_binaries(self):
        paths = [make_deb(self.dir, "mutter-common", "1", "amd64", "mutter"),
                 make_deb(self.dir, "libavformat62", "1", "i386", "ffmpeg"),
                 make_deb(self.dir, "mutter-common-bin", "1", "amd64", "mutter"),
                 make_deb(self.dir, "libgtk-4-common", "1", "all", "gtk4")]
        errors, _ = self.check(paths)
        self.assertGreaterEqual(len(errors), 2, errors)
        self.assertIn("binary mutter-common", errors[0])
        self.assertIn("binary libavformat62", errors[1])

    def test_unknown_project_is_rejected(self):
        errors, _ = self.check([make_deb(self.dir, "plurx-player", "1", "amd64")], project="someone")
        self.assertIn("unknown project", errors[0])

    def test_duplicate_name_and_architecture(self):
        paths = [make_deb(self.dir, "libdovi3", "3.3.2-3+rogdv2", "amd64", "rust-dolby-vision"),
                 make_deb(self.dir, "libdovi3", "3.3.2-3+rogdv3", "amd64", "rust-dolby-vision")]
        errors, _ = self.check(paths)
        self.assertTrue(any("is also in" in e for e in errors), errors)

    def test_exact_dependency_on_another_source(self):
        built = make_deb(self.dir, "mutter", "51.0-1ubuntu3+nativehdr18", "amd64",
                         depends="libmutter-51-0 (= 51.0-1ubuntu3+nativehdr18), libdisplay-info3 (= 0.3.0-1+nativehdr18)")
        imported = make_deb(self.dir, "showtime", "50.0-2+rogdv5.16", "all",
                            depends="python3-gi, libgtk-4-1 (= 4.24.1+ds-1+rogdv6) | foo, rog-dv-hevc-runtime (= 2)")
        errors, notes = self.check([built, imported])
        self.assertEqual(len(errors), 3, errors)
        self.assertTrue(any("mutter" in e and "libdisplay-info" in e for e in errors))
        errors, notes = self.check([built, imported], allow=True)
        self.assertEqual(len(errors), 2, errors)
        self.assertIn("libdisplay-info3", errors[1])
        self.assertTrue(any("libgtk-4-1" in n and "accepted for the baseline" in n for n in notes))
        self.assertTrue(any("rog-dv-hevc-runtime" in n and "unlisted" in n for n in notes))
        self.assertFalse(any("Depends libmutter-51-0" in error for error in errors))


class PublisherTests(unittest.TestCase):
    """End to end against the fake aptly, as the publisher's CLI."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.home, self.root, self.debs = base / "home", base / "aptly", base / "debs"
        for d in (self.home, self.debs):
            d.mkdir()
        self.config = base / "aptly.conf"
        self.config.write_text(json.dumps({"rootDir": str(self.root)}))
        self.manifest_path = base / "manifest.json"
        manifest = delivery.load_manifest()
        manifest["repository"]["keep_snapshots"] = 2
        self.manifest_path.write_text(json.dumps(manifest))
        self.environment = dict(
            os.environ, ROG_APT_HOST="aptly@repository.test", FAKE_HOME=str(self.home),
            ROG_APT_SSH=f"{shlex.quote(sys.executable)} {shlex.quote(str(FAKES))} ssh",
            ROG_APT_APTLY=f"{shlex.quote(sys.executable)} {shlex.quote(str(FAKES))} aptly -config={self.config}")

    def run_publisher(self, directory, *extra, project="rog_hdr_dv", environment=None):
        return subprocess.run([sys.executable, str(DELIVERY / "publish.py"), str(directory),
                               "--project", project, "--manifest", str(self.manifest_path), *extra],
                              capture_output=True, text=True, timeout=60, env=environment or self.environment)

    def state(self):
        return json.loads((self.root / "state.json").read_text())

    def release(self, name, version):
        directory = self.debs / name
        directory.mkdir()
        files = {"./usr/share/doc/libdisplay-info3/copyright": b"same\n"}
        make_deb(directory, "libdisplay-info3", f"0.3.0-1+{version}", "amd64", "libdisplay-info", multiarch="same", files=files)
        make_deb(directory, "libdisplay-info3", f"0.3.0-1+{version}", "i386", "libdisplay-info", multiarch="same", files=files)
        for name in ("libdisplay-info-bin", "libdisplay-info-dev"):
            for arch in ("amd64", "i386"):
                make_deb(directory, name, f"0.3.0-1+{version}", arch, "libdisplay-info")
        return directory

    def test_dry_run_checks_and_touches_nothing(self):
        environment = dict(self.environment)
        del environment["ROG_APT_HOST"]
        result = self.run_publisher(self.release("a", "nativehdr18"), "--dry-run", environment=environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("verified 6 package(s)", result.stdout)
        self.assertIn("repo add rog-stonking-incoming-", result.stdout)
        self.assertIn("publish switch -batch -gpg-key=2DA6B7DE09D5671941650C1A36DDB628371F0745 stonking", result.stdout)
        self.assertFalse(self.root.exists())
        self.assertFalse((self.home / "ssh.log").exists())

    def test_rejected_release_never_contacts_the_host(self):
        directory = self.release("a", "nativehdr18")
        (directory / "libdisplay-info3_0.3.0-1+nativehdr18_i386.deb").unlink()
        result = self.run_publisher(directory)
        self.assertEqual(result.returncode, 1)
        self.assertIn("pair is incomplete", result.stderr)
        self.assertIn("nothing was published", result.stderr)
        self.assertFalse((self.home / "ssh.log").exists())

    def test_missing_host_is_an_error(self):
        environment = dict(self.environment)
        del environment["ROG_APT_HOST"]
        result = self.run_publisher(self.release("a", "nativehdr18"), environment=environment)
        self.assertEqual(result.returncode, 2)
        self.assertIn("set ROG_APT_HOST", result.stderr)

    def test_publish_replace_same_name_only_keep_kernels_and_prune(self):
        # Another name, and a kernel, published first.
        other = self.debs / "other"
        other.mkdir()
        make_deb(other, "libdovi3", "3.3.2-3+rogdv1", "amd64", "rust-dolby-vision")
        make_deb(other, "linux-image-7.3.0-nativehdr3", "7.3.0-10.10+nativehdr3", "amd64", "linux-upstream")
        self.assertEqual(self.run_publisher(other).returncode, 0)

        kernel = self.debs / "kernel"
        kernel.mkdir()
        make_deb(kernel, "linux-image-7.3.0-nativehdr3", "7.3.0-10.10+nativehdr3.1", "amd64", "linux-upstream")
        self.assertEqual(self.run_publisher(kernel).returncode, 0)

        first = self.run_publisher(self.release("v18", "nativehdr18"))
        self.assertEqual(first.returncode, 0, first.stderr)
        second = self.run_publisher(self.release("v19", "nativehdr19"))
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("removed libdisplay-info3 0.3.0-1+nativehdr18 amd64", second.stdout)
        self.assertIn("removed libdisplay-info3 0.3.0-1+nativehdr18 i386", second.stdout)

        state = self.state()
        self.assertEqual(state["repos"], {})
        published = state["published"]["stonking"]
        refs = set(next(s["refs"] for s in state["snapshots"] if s["name"] == published))
        self.assertEqual(refs, {
            "libdovi3_3.3.2-3+rogdv1_amd64",
            "linux-image-7.3.0-nativehdr3_7.3.0-10.10+nativehdr3_amd64",
            "linux-image-7.3.0-nativehdr3_7.3.0-10.10+nativehdr3.1_amd64",
            "libdisplay-info3_0.3.0-1+nativehdr19_amd64",
            "libdisplay-info3_0.3.0-1+nativehdr19_i386",
            "libdisplay-info-bin_0.3.0-1+nativehdr19_amd64",
            "libdisplay-info-bin_0.3.0-1+nativehdr19_i386",
            "libdisplay-info-dev_0.3.0-1+nativehdr19_amd64",
            "libdisplay-info-dev_0.3.0-1+nativehdr19_i386",
        })
        names = [s["name"] for s in state["snapshots"] if s["name"] != "rog-stonking-0000-empty"]
        self.assertEqual(len(names), 2, names)  # keep_snapshots is 2 here
        self.assertTrue(all(n.startswith("rog-stonking-") and n.endswith("-rog_hdr_dv") for n in names))
        self.assertEqual(state["published"]["stonking"], names[-1])
        self.assertEqual(state["signing_key"], "2DA6B7DE09D5671941650C1A36DDB628371F0745")
        # The previous release stays in the pool for rollback, through the kept snapshot.
        self.assertIn("libdisplay-info3_0.3.0-1+nativehdr18_amd64", next(s["refs"] for s in state["snapshots"] if s["name"] == names[0]))
        self.assertIn("libdisplay-info3_0.3.0-1+nativehdr18_amd64", state["pool"])
        leftovers = sorted(p.name for p in self.home.iterdir() if not p.name.startswith((".fake-bin", "ssh.log")))
        self.assertEqual(leftovers, [])  # staging removed, lock released

    def test_switch_status_is_verified_after_a_cleanup_error(self):
        result = self.run_publisher(self.release("a", "nativehdr18"),
                                    environment=dict(self.environment, FAKE_SWITCH_CLEANUP_FAIL="1"))
        self.assertEqual(result.returncode, 0, result.stderr)
        active = self.state()["published"]["stonking"]
        self.assertIn(f"published {active}", result.stdout)
        self.assertIn(f"{active} is live", result.stderr)

    def test_failed_release_cannot_leak_into_a_later_snapshot(self):
        failed = self.release("failed", "nativehdr18")
        result = self.run_publisher(failed, environment=dict(self.environment, FAKE_SWITCH_FAIL="1"))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.state()["published"]["stonking"], "rog-stonking-0000-empty")

        other = self.debs / "other"
        other.mkdir()
        make_deb(other, "plurx-player", "0.5.8-1", "amd64")
        result = self.run_publisher(other, project="plurx")
        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.state()
        published = state["published"]["stonking"]
        refs = next(s["refs"] for s in state["snapshots"] if s["name"] == published)
        self.assertEqual(refs, ["plurx-player_0.5.8-1_amd64"])

    def test_conflicting_bytes_for_a_published_version_fail(self):
        self.assertEqual(self.run_publisher(self.release("a", "nativehdr18")).returncode, 0)
        directory = self.release("b", "nativehdr18")
        make_deb(directory, "libdisplay-info-bin", "0.3.0-1+nativehdr18", "amd64", "libdisplay-info",
                 files={"./usr/bin/di-edid-decode": b"changed"})
        result = self.run_publisher(directory)
        self.assertEqual(result.returncode, 1)
        self.assertIn("conflict", result.stderr)
        self.assertEqual(len(self.state()["snapshots"]), 2)
        self.assertFalse((self.home / publish.LOCK).exists())

    def test_held_lock_stops_a_second_publisher(self):
        (self.home / publish.LOCK).mkdir()
        result = self.run_publisher(self.release("a", "nativehdr18"))
        self.assertEqual(result.returncode, 1)
        self.assertIn(publish.LOCK, result.stderr)
        self.assertFalse(self.root.exists())
        self.assertTrue((self.home / publish.LOCK).exists())

    def test_snapshot_name_format(self):
        remote = publish.Remote("host", dry_run=True)
        manifest = delivery.load_manifest()
        when = datetime.datetime(2026, 11, 27, 13, 4, 5, tzinfo=datetime.timezone.utc)
        with open(os.devnull, "w") as sink:
            stdout, sys.stdout = sys.stdout, sink
            try:
                name = publish.publish(manifest, "plurx", [], remote, now=when)
            finally:
                sys.stdout = stdout
        self.assertEqual(name, "rog-stonking-20261127T130405000000Z-plurx")


if __name__ == "__main__":
    unittest.main()
