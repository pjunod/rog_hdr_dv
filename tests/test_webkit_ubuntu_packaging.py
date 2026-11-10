"""Source/cache refusal controls and actual Ubuntu packaging-overlay replay."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / 'packaging/webkitgtk-native-hdr'
spec = importlib.util.spec_from_file_location('webkit_verify', RECIPE / 'verify-build.py')
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


class WebKitPackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ['TMPDIR'])
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.build = self.root / 'build'
        self.build.mkdir()
        self.profile = json.loads((RECIPE / 'cmake-profile.json').read_text())
        self.features = json.loads((RECIPE / 'cmake-features.json').read_text())['feature_map']
        self.cache = dict(self.profile, CMAKE_HOME_DIRECTORY=str(self.source),
                          CMAKE_GENERATOR='Ninja',
                          GTK_DOVI_SDK_ROOT='/usr/include',
                          GTK_NATIVE_VIDEO_GDK_SDK_ROOT='/usr/include/gtk-4.0')
        self.env = patch.dict(os.environ, ROG_WEBKIT_DOVI_SDK_ROOT='/usr/include',
                              ROG_WEBKIT_GDK_SDK_ROOT='/usr/include/gtk-4.0')
        self.env.start()
        self.addCleanup(self.env.stop)
        (self.build / 'build.ninja').touch()

    def save_cache(self):
        (self.build / 'CMakeCache.txt').write_text(''.join(
            f'{key}:{"BOOL" if key in self.features or key == "ENABLE_UNREVIEWED_FEATURE" else "STRING"}={value}\n'
            for key, value in self.cache.items()))

    def test_cache_accepts_compiler_discovery_and_ignores_gi_search_roots(self):
        self.cache.update(CMAKE_C_COMPILER='/usr/bin/clang',
                          CMAKE_CXX_COMPILER='/usr/bin/clang++',
                          GI_GIRDIR='/usr/local/share/gir-1.0',
                          GI_TYPELIBDIR='/usr/local/lib/girepository-1.0')
        self.save_cache()
        verify.verify_cache(self.source, self.build, self.profile)

    def test_rejects_each_changed_profile_value(self):
        for key in self.cache:
            with self.subTest(key=key):
                value = self.cache[key]
                self.cache[key] = 'unexpected'
                self.save_cache()
                with self.assertRaisesRegex(verify.VerificationError, key):
                    verify.verify_cache(self.source, self.build, self.profile)
                self.cache[key] = value

    def test_rejects_new_unreviewed_boolean_feature(self):
        self.cache['ENABLE_UNREVIEWED_FEATURE'] = 'ON'
        self.save_cache()
        with self.assertRaisesRegex(verify.VerificationError, 'ENABLE_UNREVIEWED_FEATURE'):
            verify.verify_cache(self.source, self.build, self.profile)

    def test_rejects_old_usr_local_helper_path(self):
        self.cache['LIBEXEC_INSTALL_DIR'] = '/usr/local/libexec/webkitgtk-6.0'
        self.save_cache()
        with self.assertRaisesRegex(verify.VerificationError, 'LIBEXEC_INSTALL_DIR'):
            verify.verify_cache(self.source, self.build, self.profile)

    def test_rejects_unconfigured_cache_and_duplicate_key(self):
        self.save_cache()
        (self.build / 'build.ninja').unlink()
        with self.assertRaisesRegex(verify.VerificationError, 'Ninja graph'):
            verify.verify_cache(self.source, self.build, self.profile)
        with (self.build / 'CMakeCache.txt').open('a') as handle:
            handle.write('PORT:STRING=GTK\n')
        with self.assertRaisesRegex(verify.VerificationError, 'duplicate'):
            verify.verify_cache(self.source, self.build, self.profile)

    def test_source_corruption_mode_and_extra_input_are_rejected(self):
        child = self.source / 'Source'
        child.mkdir()
        code = child / 'code.cpp'
        code.write_text('reviewed source\n')
        pin = {'common': {}, 'candidate': {'Source': verify.object_id(child)}}
        verify.verify_source(self.source, pin)
        code.write_text('different source\n')
        with self.assertRaises(verify.VerificationError):
            verify.verify_source(self.source, pin)
        code.write_text('reviewed source\n')
        code.chmod(0o755)
        with self.assertRaises(verify.VerificationError):
            verify.verify_source(self.source, pin)
        code.chmod(0o644)
        extra = child / 'unexpected.h'
        extra.touch()
        with self.assertRaises(verify.VerificationError):
            verify.verify_source(self.source, pin)
        extra.unlink()
        # The distribution build executes Python scripts in the source tree.
        (child / '__pycache__').mkdir()
        (child / '__pycache__/ignored.pyc').write_bytes(b'cache')
        verify.verify_source(self.source, pin)

    def test_cache_directory_refusals_preserve_sentinel(self):
        sentinel = self.build / 'warm-object.o'
        sentinel.write_bytes(b'retain')
        link = self.root / 'link'
        link.symlink_to(self.build, target_is_directory=True)
        for value in (str(link), str(self.source), str(self.root), 'other-relative',
                      str(self.source / 'cache'), '/path with spaces'):
            with self.subTest(value=value), self.assertRaises(verify.VerificationError):
                verify.build_path(self.source, value)
        self.assertEqual(verify.build_path(self.source, 'build-gtk4'), self.source / 'build-gtk4')
        self.assertEqual(verify.build_path(self.source, str(self.build)), self.build)
        self.assertEqual(sentinel.read_bytes(), b'retain')

    def overlay(self):
        debian = self.source / 'debian'
        debian.mkdir()
        pin = json.loads((RECIPE / 'source-pin.json').read_text())
        for name, digest in pin['packaging_inputs_sha256'].items():
            original = RECIPE / 'ubuntu-inputs' / name
            self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(), digest)
            shutil.copy2(original, debian / name)
        subprocess.run(['patch', '--batch', '-p1', '-i', str(RECIPE / 'ubuntu-packaging.diff')],
                       cwd=self.source, check=True, capture_output=True)
        return debian

    def test_overlay_preserves_upstream_debhelper_and_external_cache_refusals(self):
        debian = self.overlay()
        rules = (debian / 'rules').read_text()
        self.assertIn('ENABLE_GTK3=NO', rules)
        self.assertIn('ENABLE_GTK4=YES', rules)
        self.assertIn('dh $@ --with gir --buildsystem=cmake+ninja', rules)
        self.assertIn('dh_makeshlibs -plibwebkitgtk-6.0-4', rules)
        self.assertIn('dh_makeshlibs -plibjavascriptcoregtk-6.0-1', rules)
        self.assertIn('WEBKIT_DH_CONVERT_GTK4', rules)
        self.assertIn('Use dpkg-buildpackage -b -nc', rules)
        self.assertIn('External warm cache clean is refused', rules)
        self.assertEqual((debian / 'control.in').read_text().count('\nPackage:'), 0)

    @unittest.skipUnless(Path('/usr/share/dpkg/architecture.mk').exists(),
                         'actual control generation requires Ubuntu dpkg/debhelper')
    def test_generated_control_selects_exact_six_gtk4_packages(self):
        debian = self.overlay()
        # Upstream rules require these normal source-owned templates.
        (debian / 'control-transitional.in').touch()
        subprocess.run(['make', '-f', 'debian/rules', 'debian/control'],
                       cwd=self.source, check=True, capture_output=True)
        control = (debian / 'control').read_text()
        names = [line.split(': ', 1)[1] for line in control.splitlines()
                 if line.startswith('Package: ')]
        pin = json.loads((RECIPE / 'source-pin.json').read_text())
        self.assertEqual(names, pin['binary_packages'])
        self.assertNotIn('libwebkit2gtk-4.1-0', control)
        self.assertNotIn('webkitgtk-webdriver', control)
        self.assertIn('${shlibs:Depends}', control)
        self.assertIn('${gir:Depends}', control)
        self.assertIn('gstreamer1.0-gtk-dovi (>= 0.1.0+rogdv5)', control)


if __name__ == '__main__':
    unittest.main()
