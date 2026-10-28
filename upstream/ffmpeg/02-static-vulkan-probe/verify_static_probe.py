#!/usr/bin/env python3
"""Compare the real FFmpeg configure using a static-only Vulkan link fixture."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


def run(command, **kwargs):
    return subprocess.run(command, check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='read-only local FFmpeg Git source')
    parser.add_argument('--headers', type=Path, required=True, help='Khronos include directory containing vulkan/vulkan.h')
    parser.add_argument('--work-root', type=Path, default=Path('work/ffmpeg-static-probe'))
    args = parser.parse_args()
    kit = Path(__file__).resolve().parent
    manifest = json.loads((kit.parent / 'manifest.json').read_text())
    headers = args.headers.resolve()
    if not (headers / 'vulkan/vulkan.h').is_file():
        parser.error('headers must contain vulkan/vulkan.h')
    args.work_root.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='probe-', dir=args.work_root.resolve()))
    source = work / 'source'
    run(['git', 'clone', '--quiet', '--shared', '--no-checkout', str(args.source.resolve()), str(source)])
    run(['git', '-C', str(source), 'checkout', '--quiet', '--detach', manifest['base']])
    prefix = work / 'prefix'
    (prefix / 'lib/pkgconfig').mkdir(parents=True)
    stub = work / 'stub.c'
    stub.write_text('#include <vulkan/vulkan.h>\nVKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL vkGetInstanceProcAddr(VkInstance instance, const char *name) { (void)instance; (void)name; return 0; }\n')
    run(['cc', '-I' + str(headers), '-c', str(stub), '-o', str(work / 'stub.o')])
    run(['ar', 'rcs', str(prefix / 'lib/libvulkan_stub.a'), str(work / 'stub.o')])
    (prefix / 'lib/pkgconfig/vulkan.pc').write_text(
        f'prefix={prefix}\nlibdir=${{prefix}}/lib\nincludedir={headers}\n'
        'Name: vulkan\nDescription: Static-only link-probe regression fixture\nVersion: 1.3.277\n'
        'Libs: -L"${libdir}" -lvulkan_stub\nCflags: -I"${includedir}"\n')
    results = {}
    for label in ['baseline', 'fixed']:
        if label == 'fixed':
            patch = next(kit.glob('*.patch'))
            run(['git', '-C', str(source), 'apply', str(patch)])
        build = work / label
        build.mkdir()
        env = os.environ | {'PKG_CONFIG_PATH': str(prefix / 'lib/pkgconfig'), 'TMPDIR': str(build)}
        command = [str(source / 'configure'), '--disable-everything', '--disable-programs',
                   '--disable-doc', '--disable-autodetect', '--disable-x86asm',
                   '--enable-vulkan', '--enable-vulkan-static']
        with (build / 'configure-output.log').open('w') as output:
            result = subprocess.run(command, cwd=build, env=env, stdout=output, stderr=subprocess.STDOUT)
        results[label] = result.returncode
    (work / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps({'results': results, 'retained_work': str(work)}))
    if results['baseline'] == 0 or results['fixed'] != 0:
        raise SystemExit('Expected the original probe to fail and the corrected probe to pass; inspect retained logs.')


if __name__ == '__main__':
    main()
