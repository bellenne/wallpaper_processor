from __future__ import annotations

import re
import sys
from pathlib import Path


APP_META_PATH = Path('app/core/app_meta.py')
VERSION_PATTERN = re.compile(r"^APP_VERSION = '.*'$", re.MULTILINE)


def main() -> int:
    if len(sys.argv) != 2:
        print('Usage: python scripts/set_version.py <version>')
        return 1

    version = sys.argv[1].strip().removeprefix('v')
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        print(f'Invalid version: {version}')
        return 1

    content = APP_META_PATH.read_text(encoding='utf-8')
    updated = VERSION_PATTERN.sub(f"APP_VERSION = '{version}'", content, count=1)
    APP_META_PATH.write_text(updated, encoding='utf-8')
    print(f'Updated version to {version}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
