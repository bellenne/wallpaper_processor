# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import requests
from PySide6.QtWidgets import QMessageBox

from app.core.app_meta import (
    APP_DIR_NAME,
    APP_EXECUTABLE,
    APP_NAME,
    APP_VERSION,
    GITHUB_REPO,
    RELEASE_ASSET_NAME,
)


class AppUpdater:
    RELEASE_URL = f'https://api.github.com/repos/{GITHUB_REPO}/releases/latest'

    def __init__(self, timeout: int = 8) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                'Accept': 'application/vnd.github+json',
                'User-Agent': f'{APP_NAME}/{APP_VERSION}',
            }
        )

    def process_startup_update(self) -> bool:
        if not getattr(sys, 'frozen', False):
            return False

        try:
            release = self._fetch_latest_release()
            latest_version = self._normalize_version(release.get('tag_name', ''))
            if not latest_version or self._compare_versions(latest_version, APP_VERSION) <= 0:
                return False

            asset = self._find_release_asset(release.get('assets', []))
            if asset is None:
                return False
        except Exception:
            return False

        question = (
            f'Доступна новая версия {latest_version}.\n'
            f'Текущая версия: {APP_VERSION}.\n\n'
            'Скачать и установить обновление сейчас?'
        )
        answer = QMessageBox.question(
            None,
            'Обновление приложения',
            question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False

        try:
            archive_path = self._download_release_asset(asset['browser_download_url'])
            self._launch_update_installer(archive_path)
        except Exception as exc:
            QMessageBox.warning(
                None,
                'Ошибка обновления',
                f'Не удалось скачать или установить обновление.\n\n{exc}',
            )
            return False

        QMessageBox.information(
            None,
            'Обновление приложения',
            'Обновление скачано. Приложение закроется и запустит новую версию после установки.',
        )
        return True

    def _fetch_latest_release(self) -> dict:
        response = self.session.get(self.RELEASE_URL, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _find_release_asset(self, assets: list[dict]) -> dict | None:
        for asset in assets:
            if asset.get('name') == RELEASE_ASSET_NAME:
                return asset

        for asset in assets:
            name = str(asset.get('name', ''))
            if name.lower().endswith('.zip'):
                return asset

        return None

    def _download_release_asset(self, asset_url: str) -> Path:
        work_dir = Path(tempfile.mkdtemp(prefix='wallpaper_processor_update_'))
        archive_path = work_dir / RELEASE_ASSET_NAME

        with self.session.get(asset_url, timeout=60, stream=True) as response:
            response.raise_for_status()
            with archive_path.open('wb') as file_handle:
                for chunk in response.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        file_handle.write(chunk)

        return archive_path

    def _launch_update_installer(self, archive_path: Path) -> None:
        install_dir = Path(sys.executable).resolve().parent
        script_path = archive_path.with_name('apply_update.ps1')
        script_path.write_text(self._build_update_script(), encoding='utf-8')

        creation_flags = 0
        for flag_name in ('CREATE_NO_WINDOW', 'DETACHED_PROCESS', 'CREATE_NEW_PROCESS_GROUP'):
            creation_flags |= getattr(subprocess, flag_name, 0)

        subprocess.Popen(
            [
                'powershell.exe',
                '-NoProfile',
                '-ExecutionPolicy',
                'Bypass',
                '-File',
                str(script_path),
                '-ArchivePath',
                str(archive_path),
                '-InstallDir',
                str(install_dir),
                '-ExecutableName',
                APP_EXECUTABLE,
                '-AppDirName',
                APP_DIR_NAME,
                '-CurrentPid',
                str(os.getpid()),
            ],
            creationflags=creation_flags,
            close_fds=True,
        )

    @staticmethod
    def _normalize_version(raw_version: str) -> str:
        return raw_version.strip().removeprefix('v')

    @classmethod
    def _compare_versions(cls, left: str, right: str) -> int:
        left_parts = cls._parse_version_parts(left)
        right_parts = cls._parse_version_parts(right)
        if left_parts < right_parts:
            return -1
        if left_parts > right_parts:
            return 1
        return 0

    @staticmethod
    def _parse_version_parts(version: str) -> tuple[int, ...]:
        cleaned = version.strip().removeprefix('v')
        if not cleaned:
            return (0,)
        parts: list[int] = []
        for chunk in cleaned.split('.'):
            digits = ''.join(char for char in chunk if char.isdigit())
            parts.append(int(digits or '0'))
        return tuple(parts)

    @staticmethod
    def _build_update_script() -> str:
        return r'''param(
    [Parameter(Mandatory = $true)][string]$ArchivePath,
    [Parameter(Mandatory = $true)][string]$InstallDir,
    [Parameter(Mandatory = $true)][string]$ExecutableName,
    [Parameter(Mandatory = $true)][string]$AppDirName,
    [Parameter(Mandatory = $true)][int]$CurrentPid
)

$ErrorActionPreference = 'Stop'

for ($i = 0; $i -lt 120; $i++) {
    if (-not (Get-Process -Id $CurrentPid -ErrorAction SilentlyContinue)) {
        break
    }
    Start-Sleep -Seconds 1
}

$stageDir = Join-Path ([System.IO.Path]::GetTempPath()) ('wallpaper_processor_stage_' + [guid]::NewGuid().ToString('N'))
Expand-Archive -Path $ArchivePath -DestinationPath $stageDir -Force

$packageDir = Join-Path $stageDir $AppDirName
if (-not (Test-Path $packageDir)) {
    $packageDir = $stageDir
}

Copy-Item -Path (Join-Path $packageDir '*') -Destination $InstallDir -Recurse -Force
Start-Sleep -Milliseconds 500
Start-Process -FilePath (Join-Path $InstallDir $ExecutableName)
'''
