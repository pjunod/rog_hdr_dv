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
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / 'packaging/webkitgtk-native-hdr'
spec = importlib.util.spec_from_file_location('webkit_verify', RECIPE / 'verify-build.py')
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)
prep_spec = importlib.util.spec_from_file_location('webkit_prepare', RECIPE / 'prepare-source.py')
prepare = importlib.util.module_from_spec(prep_spec)
prep_spec.loader.exec_module(prepare)


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
        self.cache = dict(self.profile, CMAKE_HOME_DIRECTORY=str(self.source), CMAKE_CACHEFILE_DIR=str(self.build),
                          CMAKE_GENERATOR='Ninja',
                          GTK_DOVI_SDK_ROOT='/usr/include',
                          GTK_NATIVE_VIDEO_GDK_SDK_ROOT='/usr/include/gtk-4.0')
        self.env = patch.dict(os.environ, ROG_WEBKIT_DOVI_SDK_ROOT='/usr/include',
                              ROG_WEBKIT_GDK_SDK_ROOT='/usr/include/gtk-4.0')
        self.env.start()
        self.addCleanup(self.env.stop)
        (self.build / 'build.ninja').write_text('# CMAKE generated file: DO NOT EDIT!\ninclude CMakeFiles/rules.ninja\nbuild fixture: phony\n')
        (self.build / 'CMakeFiles').mkdir()
        (self.build / 'CMakeFiles/rules.ninja').write_text('# CMAKE generated file: DO NOT EDIT!\nrule fixture\n  command = true\n')

    def save_cache(self):
        (self.build / 'CMakeCache.txt').write_text(''.join(
            f'{key}:{"BOOL" if key in self.features or key == "ENABLE_UNREVIEWED_FEATURE" else "STRING"}={value}\n'
            for key, value in self.cache.items()))

    def test_cache_accepts_compiler_discovery_and_usr_gi_destinations(self):
        self.cache.update(CMAKE_C_COMPILER='/usr/bin/clang',
                          CMAKE_CXX_COMPILER='/usr/bin/clang++')
        self.save_cache()
        verify.verify_cache(self.source, self.build, self.profile)

    def test_rejects_stale_usr_local_gi_install_destinations(self):
        for key, stale in (('GI_GIRDIR', '/usr/local/share/gir-1.0'),
                           ('GI_TYPELIBDIR', '/usr/local/lib/x86_64-linux-gnu/girepository-1.0')):
            with self.subTest(key=key):
                value = self.cache[key]
                self.cache[key] = stale
                self.save_cache()
                with self.assertRaisesRegex(verify.VerificationError, key):
                    verify.verify_cache(self.source, self.build, self.profile)
                self.cache[key] = value

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


    def test_rejects_copied_cache_empty_graph_and_alien_graph(self):
        self.save_cache()
        other = self.root / 'copied-build'
        shutil.copytree(self.build, other)
        with self.assertRaisesRegex(verify.VerificationError, 'CMAKE_CACHEFILE_DIR'):
            verify.verify_cache(self.source, other, self.profile)
        for graph in ('', 'build default: injected-rule\n'):
            (self.build / 'build.ninja').write_text(graph)
            with self.assertRaisesRegex(verify.VerificationError, 'Ninja graph'):
                verify.verify_cache(self.source, self.build, self.profile)

    def test_unexpected_private_top_level_aborts_before_recording(self):
        sentinel = self.source / 'qualification.private.json'
        sentinel.write_text('private evidence')
        pin = {'common': {}, 'candidate': {}}
        with self.assertRaisesRegex(verify.VerificationError, 'unexpected top-level'):
            verify.verify_source(self.source, pin, packaging=True)
        self.assertEqual(sentinel.read_text(), 'private evidence')

    def test_private_sentinel_in_debian_python_cache_fails_strict_packaging_identity(self):
        debian = self.source / 'debian'
        debian.mkdir()
        (debian / 'control').write_text('Source: fixture\n')
        pin = {'common': {}, 'base': {'debian': verify.object_id(debian, ignore_python=False)}}
        verify.verify_source(self.source, pin, 'base', packaging=True)
        cache = debian / '__pycache__'
        cache.mkdir()
        (cache / 'qualification.private.json').write_text('private operator note')
        with self.assertRaisesRegex(verify.VerificationError, 'debian'):
            verify.verify_source(self.source, pin, 'base', packaging=True)

    def test_quilt_metadata_rejects_root_links_descendant_links_and_special_files(self):
        quilt = self.root / 'quilt'
        quilt.mkdir()
        (quilt / 'applied-patches').write_text('ubuntu.patch\n')
        link = self.root / '.pc'
        link.symlink_to(quilt, target_is_directory=True)
        with self.assertRaises(prepare.verify.VerificationError):
            prepare.verify_quilt(link, ['ubuntu.patch'])
        nested = quilt / 'redirect'
        nested.symlink_to(self.build, target_is_directory=True)
        with self.assertRaises(prepare.verify.VerificationError):
            prepare.verify_quilt(quilt, ['ubuntu.patch'])
        nested.unlink()
        os.mkfifo(nested)
        with self.assertRaises(prepare.verify.VerificationError):
            prepare.verify_quilt(quilt, ['ubuntu.patch'])

    def test_recorded_patch_rejects_extra_private_paths_and_renames(self):
        valid = '--- source.orig/Source/code.cpp\n+++ source/Source/code.cpp\n@@ -1 +1 @@\n-old\n+new\n'
        prepare.validate_recorded_patch(valid, ['Source/code.cpp'])
        for addition in ('--- source.orig/private.json\n+++ source/private.json\n',
                         '--- /etc/private\n+++ source/Source/code.cpp\n',
                         '--- source/../private\n+++ source/Source/code.cpp\n',
                         'GIT binary patch\n'):
            with self.subTest(addition=addition), self.assertRaises(prepare.verify.VerificationError):
                prepare.validate_recorded_patch(valid + addition, ['Source/code.cpp'])
        with self.assertRaises(prepare.verify.VerificationError):
            prepare.validate_recorded_patch(valid.replace('+++ source/Source/code.cpp', '+++ /dev/null'), ['Source/code.cpp'])

    def test_public_product_series_matches_packaging_pin(self):
        pin = json.loads((RECIPE / 'source-pin.json').read_text())
        files = prepare.product_patches(pin, series=ROOT / 'patches/ubuntu-webkitgtk-native-hdr/series')
        self.assertEqual(len(files), 8)
        self.assertEqual(files[0].name, '0001-webkitgtk-clear-video-and-native-hdr.patch')

    def product_series_fixture(self):
        directory = self.root / 'product-patches'
        directory.mkdir()
        names = ['0001-first.patch', '0002-second.patch']
        records = []
        for name, old, new in zip(names, ('original', 'middle'), ('middle', 'final')):
            file = directory / name
            file.write_text('--- a/Source/code.cpp\n+++ b/Source/code.cpp\n'
                            '@@ -1 +1 @@\n-' + old + '\n+' + new + '\n')
            records.append({'name': name, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()})
        series = directory / 'series'
        series.write_text(''.join(name + '\n' for name in names))
        return {'product_patch_series': records}, series

    def test_ordered_product_series_replays_sequential_changes(self):
        pin, series = self.product_series_fixture()
        (self.source / 'Source').mkdir()
        code = self.source / 'Source/code.cpp'
        code.write_text('original\n')
        files = prepare.product_patches(pin, series=series)
        prepare.apply_product_patches(self.source, files)
        self.assertEqual(code.read_text(), 'final\n')
        self.assertEqual([file.name for file in files], [item['name'] for item in pin['product_patch_series']])

    def test_product_series_rejects_reordered_missing_duplicate_and_unsafe_entries(self):
        pin, series = self.product_series_fixture()
        names = [item['name'] for item in pin['product_patch_series']]
        for entries in (names[::-1], names[:-1], names + names[:1],
                        ['../' + names[0], names[1]],
                        [str((series.parent / names[0]).resolve()), names[1]],
                        [names[0] + ' -p0', names[1]]):
            with self.subTest(entries=entries), patch.object(prepare, 'run') as run:
                series.write_text(''.join(name + '\n' for name in entries))
                with self.assertRaisesRegex(prepare.verify.VerificationError, 'names and order'):
                    prepare.product_patches(pin, series=series)
                run.assert_not_called()

    def test_product_series_checks_every_file_before_source_mutation(self):
        pin, series = self.product_series_fixture()
        last = series.parent / pin['product_patch_series'][-1]['name']
        saved = last.read_bytes()
        # Exercise the preparation entry point: a late missing/corrupt patch
        # must fail before archive/source checks, quilt recording or GNU patch.
        recipe = self.root / 'recipe'
        recipe.mkdir()
        (recipe / 'source-pin.json').write_text(json.dumps(pin))
        for bad in ('missing', 'digest', 'symlink'):
            with self.subTest(bad=bad):
                last.unlink()
                if bad == 'digest':
                    last.write_bytes(saved + b'changed')
                elif bad == 'symlink':
                    target = self.root / 'redirect.patch'
                    target.write_bytes(saved)
                    last.symlink_to(target)
                with patch.object(prepare, 'HERE', recipe), patch.object(prepare, 'run') as run, \
                        patch.object(prepare.verify, 'verify_source') as verify_source:
                    with self.assertRaises(prepare.verify.VerificationError):
                        prepare.prepare(self.source, product_series=series)
                    run.assert_not_called()
                    verify_source.assert_not_called()
                if last.is_symlink() or last.exists():
                    last.unlink()
                last.write_bytes(saved)

    def test_product_series_refuses_manifest_symlink_and_unsafe_pin_names(self):
        pin, series = self.product_series_fixture()
        link = self.root / 'series-link'
        link.symlink_to(series)
        with self.assertRaisesRegex(prepare.verify.VerificationError, 'regular file'):
            prepare.product_patches(pin, series=link)
        for name in ('../outside.patch', '/outside.patch', 'nested/file.patch', 'file.patch -p0'):
            pin['product_patch_series'][0]['name'] = name
            with self.subTest(name=name), self.assertRaisesRegex(prepare.verify.VerificationError, 'manifest'):
                prepare.product_patches(pin, series=series)

    def test_legacy_single_product_patch_remains_digest_pinned(self):
        pin, series = self.product_series_fixture()
        file = series.parent / pin['product_patch_series'][0]['name']
        legacy = {'product_patch_sha256': pin['product_patch_series'][0]['sha256']}
        self.assertEqual(prepare.product_patches(legacy, patch=file), [file])
        with self.assertRaisesRegex(prepare.verify.VerificationError, '--product-series'):
            prepare.product_patches(pin, patch=file)
        file.write_text('unreviewed replacement')
        with self.assertRaisesRegex(prepare.verify.VerificationError, 'reviewed source pin'):
            prepare.product_patches(legacy, patch=file)

    def producer_fixture(self):
        pin = json.loads((RECIPE / 'source-pin.json').read_text())
        def record(path):
            return {'path': str(path), 'sha256': verify.sha256_file(path)}
        controls = self.root / 'retained'
        controls.mkdir()
        inputs = {}
        for name in ('guard', 'source_archive', 'sdk_controls'):
            file = controls / name
            file.write_text('retained trusted local operator input: ' + name)
            inputs[name] = record(file)
        sdk = self.root / 'sdk'
        mapper = sdk / 'gst-gtk-dovi-1.0/mapper.h'
        gdk = sdk / 'gdk/wayland/gdkwaylandsurface.h'
        for file in (mapper, gdk):
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text('public SDK header fixture')
        os.environ['ROG_WEBKIT_DOVI_SDK_ROOT'] = str(sdk)
        os.environ['ROG_WEBKIT_GDK_SDK_ROOT'] = str(sdk)
        receipt = {'schema': 'rog-webkit-local-producer-v1', 'trust': 'local-operator',
                   'source_directory': str(self.source), 'build_directory': str(self.build),
                   'candidate_commit': pin['candidate_commit'],
                   'feature_map_sha256': json.loads((RECIPE / 'cmake-features.json').read_text())['feature_map_sha256'],
                   'cmake_profile_sha256': hashlib.sha256(json.dumps(self.profile, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                   'completed_guard': True,
                   'sdk_compile_checks': dict(gdk_native_hdr=True, mapper_destination_abi=True, mapper_source_lease_abi=True),
                   'files': {key: record(path) for key, path in dict(cache=self.build / 'CMakeCache.txt', graph=self.build / 'build.ninja', rules=self.build / 'CMakeFiles/rules.ninja').items()},
                   'inputs': inputs, 'sdk_headers': {'mapper': record(mapper), 'gdkwayland': record(gdk)},
                   'ninja_commands_sha256': hashlib.sha256(b'reviewed producer commands\n').hexdigest()}
        file = self.root / 'producer.private.json'
        file.write_text(json.dumps(receipt))
        return pin, receipt, file, gdk

    def test_external_producer_binds_guard_graph_commands_and_headers(self):
        self.save_cache()
        pin, receipt, file, header = self.producer_fixture()
        with patch.object(verify.subprocess, 'check_output', return_value=b'reviewed producer commands\n'):
            verify.verify_producer(self.source, self.build, self.profile, pin, file)
            for mutate in ('guard', 'graph', 'header', 'commands'):
                with self.subTest(mutate=mutate):
                    changed = (Path(receipt['inputs']['guard']['path']) if mutate == 'guard' else
                               self.build / 'build.ninja' if mutate == 'graph' else header)
                    saved = changed.read_bytes()
                    if mutate == 'commands':
                        receipt['ninja_commands_sha256'] = '0' * 64
                        file.write_text(json.dumps(receipt))
                    else:
                        changed.write_bytes(saved + b'changed')
                    with self.assertRaises(verify.VerificationError):
                        verify.verify_producer(self.source, self.build, self.profile, pin, file)
                    changed.write_bytes(saved)

    def populate_manifest_inputs(self, debian):
        for name in ('gir1.2-javascriptcoregtk-4.1.install', 'gir1.2-webkit2-4.1.install',
                     'libjavascriptcoregtk-4.1-0.install', 'libjavascriptcoregtk-4.1-dev.install',
                     'libwebkit2gtk-4.1-0.docs', 'libwebkit2gtk-4.1-0.install',
                     'libwebkit2gtk-4.1-0.symbols', 'libwebkit2gtk-4.1-dev.install'):
            (debian / name).write_text('usr/lib/*/webkit2gtk-4.1/fixture\n')
        (debian / 'control-transitional.in').touch()

    @unittest.skipUnless(Path('/usr/share/dpkg/architecture.mk').exists(),
                         'actual make/debhelper lifecycle requires Ubuntu')
    def test_unstamped_external_configure_only_verifies_and_generates_manifests(self):
        debian = self.overlay()
        self.populate_manifest_inputs(debian)
        tools = debian / 'rog-native-hdr'
        tools.mkdir()
        (tools / 'verify-build.py').write_text(
            'from pathlib import Path\nimport sys\n'
            'with Path("verify.calls").open("a") as f: f.write(repr(sys.argv[1:])+"\\n")\n')
        sentinel = self.build / 'completed.o'
        sentinel.write_bytes(b'retain')
        stamp = sentinel.stat().st_mtime_ns
        env = dict(os.environ, ROG_WEBKIT_BUILD_DIR=str(self.build))
        result = subprocess.run(['make', '-f', 'debian/rules', 'override_dh_auto_configure'],
                                cwd=self.source, env=env, check=True, capture_output=True, text=True)
        self.assertNotIn('dh_auto_configure -B', result.stdout)
        self.assertEqual((self.source / 'verify.calls').read_text().splitlines(), ["['--path-only']", '[]'])
        self.assertTrue((debian / 'libwebkitgtk-6.0-4.install').is_file())
        self.assertEqual(sentinel.read_bytes(), b'retain')
        self.assertEqual(sentinel.stat().st_mtime_ns, stamp)
        self.assertFalse((debian / 'debhelper-build-stamp').exists())
        (debian / 'changelog').write_text('webkit2gtk (2.52.6-1ubuntu1+rogdv1) stonking; urgency=medium\n\n  * Packaging lifecycle fixture.\n\n -- ROG HDR contributors <rog-hdr@example.invalid>  Mon, 09 Nov 2026 00:00:00 +0000\n')
        subprocess.run(['make', '-f', 'debian/rules', 'debian/control'],
                       cwd=self.source, env=env, check=True, capture_output=True, text=True)
        sequence = subprocess.run(['dh', 'build', '--no-act', '--with', 'gir', '--buildsystem=cmake+ninja'],
                                  cwd=self.source, env=env, capture_output=True, text=True)
        self.assertEqual(sequence.returncode, 0, sequence.stderr)
        self.assertIn('override_dh_auto_configure', sequence.stdout)
        self.assertIn('override_dh_auto_build', sequence.stdout)

    @unittest.skipUnless(Path('/usr/share/dpkg/architecture.mk').exists(),
                         'actual make lifecycle requires Ubuntu')
    def test_default_clean_refuses_symlink_before_any_clean_tool(self):
        debian = self.overlay()
        tools = debian / 'rog-native-hdr'
        tools.mkdir()
        for name in ('verify-build.py', 'cmake-features.json'):
            shutil.copy2(RECIPE / name, tools / name)
        self.populate_manifest_inputs(debian)
        (self.source / 'build-gtk4').symlink_to(self.build, target_is_directory=True)
        sentinel = self.build / 'completed.o'
        sentinel.write_bytes(b'retain')
        env = dict(os.environ)
        env.pop('ROG_WEBKIT_BUILD_DIR', None)
        result = subprocess.run(['make', '-f', 'debian/rules', 'override_dh_auto_clean'],
                                cwd=self.source, env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('symlink', result.stderr)
        self.assertNotIn('dh_auto_clean -B', result.stdout)
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
        self.assertIn('Verify the existing graph and generate package metadata only', rules)
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
        parsed = subprocess.run(['dh_listpackages'], cwd=self.source,
                                capture_output=True, text=True)
        self.assertEqual(parsed.returncode, 0, parsed.stderr)
        self.assertEqual(parsed.stdout.splitlines(), pin['binary_packages'])
        self.assertNotIn('libwebkit2gtk-4.1-0', control)
        self.assertNotIn('webkitgtk-webdriver', control)
        self.assertIn('${shlibs:Depends}', control)
        self.assertIn('${gir:Depends}', control)
        self.assertIn('gstreamer1.0-gtk-dovi (>= 0.1.0+rogdv5)', control)
        self.assertIn('libgtk-4-1 (>= 4.24.1+ds-1+rogdv6)', control)
        self.assertIn('libgtk-4-dev (>= 4.24.1+ds-1+rogdv5)', control)


if __name__ == '__main__':
    unittest.main()
