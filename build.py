"""Build a standalone Windows executable using the current virtual environment."""
from pathlib import Path
import shutil
import subprocess
import sys


def main() -> None:
    root = Path(__file__).resolve().parent
    if sys.platform != 'win32':
        raise SystemExit('Build the Windows executable on Windows')
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile',
        '--name', 'CallTelegramApi', 'call_telegram.py',
    ], cwd=root, check=True)
    # Always package the blank example, never the user's real credentials.
    shutil.copy2(root / 'CallTelegram.ini.example', root / 'dist/CallTelegram.ini')
    shutil.copy2(root / 'README.md', root / 'dist/README.md')
    shutil.copy2(root / 'LICENSE', root / 'dist/LICENSE')
    shutil.make_archive(str(root / 'dist/CallTelegramApi-Python-Windows'), 'zip',
                        root_dir=root / 'dist', base_dir='CallTelegramApi.exe')
    # Include adjacent configuration and instructions in the same archive.
    from zipfile import ZipFile
    with ZipFile(root / 'dist/CallTelegramApi-Python-Windows.zip', 'a') as archive:
        for name in ('CallTelegram.ini', 'README.md', 'LICENSE'):
            archive.write(root / 'dist' / name, name)


if __name__ == '__main__':
    main()
