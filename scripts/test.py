"""Run the complete pytest collection in fresh processes per test module.

Qt application state must not accumulate between unrelated modules. Assert that
the executed JUnit case count equals the original full-suite collection.
"""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


def main():
    os.chdir(Path(__file__).resolve().parents[1])
    collected = subprocess.run([sys.executable, '-m', 'pytest', '--collect-only', '-q'],
                               capture_output=True, text=True, check=True)
    nodes = [line for line in collected.stdout.splitlines()
             if '::' in line and Path(line.partition('::')[0]).is_file()]
    modules = list(dict.fromkeys(node.partition('::')[0] for node in nodes))
    if not modules:
        raise RuntimeError('Pytest did not collect any test modules: ' + collected.stdout + collected.stderr)
    print(f'Collected {len(nodes)} tests in {len(modules)} isolated modules', flush=True)
    total = skipped = 0
    with tempfile.TemporaryDirectory(prefix='ilias-test-reports-') as temporary:
        for index, module in enumerate(modules):
            print(f'\n[{index + 1}/{len(modules)}] {module}', flush=True)
            report = Path(temporary)/f'{index}.xml'
            subprocess.run([sys.executable, '-m', 'pytest', '-q', module, '--junitxml', str(report)],
                           check=True, timeout=300)
            cases = list(ET.parse(report).iter('testcase'))
            total += len(cases)
            skipped += sum(case.find('skipped') is not None for case in cases)
    if total != len(nodes):
        raise RuntimeError(f'Executed {total} test cases, but collected {len(nodes)}')
    print(f'\nComplete collection verified: {total - skipped} passed, {skipped} skipped ({total} total)', flush=True)


if __name__ == '__main__':
    main()
