"""Recording service for call audio processing.

Pipeline: Download WAV from Ultravox → Transcode to Opus/OGG → Encrypt with Fernet → Store on filesystem.

Compliance:
- RGPD Art. 32: Encryption at rest (Fernet AES-128-CBC + HMAC-SHA256)
- RGPD Art. 5.1.e: Storage limitation (retention_days auto-cleanup)
"""

import asyncio
import logging
import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from cryptography.fernet import Fernet

from app.config.settings import Settings

logger = logging.getLogger(__name__)


class RecordingService:
    """Handles recording download, transcoding, encryption, and lifecycle."""

    def __init__(self, settings: Settings):
        self._semaphore = asyncio.Semaphore(settings.recording_max_concurrent)
        self._base_path = Path(settings.recordings_base_path)
        self._client_id = settings.recording_client_id
        self._retention_days = settings.recording_retention_days
        self._fernet: Fernet | None = None
        if settings.recording_encryption_key:
            self._fernet = Fernet(settings.recording_encryption_key.encode())

    def get_recording_dir(self) -> Path:
        """Build directory path: base/{client_id}/{YYYY-MM}/"""
        now = datetime.now(UTC)
        return self._base_path / self._client_id / now.strftime("%Y-%m")

    def get_recording_path(self, db_call_id: str) -> Path:
        """Build full file path for a recording."""
        ext = ".ogg.enc" if self._fernet else ".ogg"
        return self.get_recording_dir() / f"{db_call_id}{ext}"

    async def download_and_process(
        self,
        ultravox_call_id: str,
        db_call_id: str,
        ultravox_api_key: str,
    ) -> str | None:
        """Full pipeline: download WAV -> transcode OGG -> encrypt -> save.

        Returns the relative file path for DB storage, or None on failure.
        """
        async with self._semaphore:
            tmp_wav = None
            tmp_ogg = None
            try:
                # 1. Download WAV from Ultravox (follows 302 to GCS signed URL)
                tmp_wav = await self._download_wav(ultravox_call_id, ultravox_api_key)
                if not tmp_wav:
                    return None

                # 2. Transcode WAV -> OGG Opus 32kbps mono
                tmp_ogg = await self._transcode_to_ogg(tmp_wav, db_call_id)
                if not tmp_ogg:
                    return None

                # 3. Encrypt and save to final path
                final_path = self.get_recording_path(db_call_id)
                final_path.parent.mkdir(parents=True, exist_ok=True)

                ogg_bytes = await asyncio.to_thread(Path(tmp_ogg).read_bytes)
                if self._fernet:
                    encrypted = await asyncio.to_thread(self._fernet.encrypt, ogg_bytes)
                    await asyncio.to_thread(final_path.write_bytes, encrypted)
                else:
                    await asyncio.to_thread(final_path.write_bytes, ogg_bytes)

                logger.info(
                    "Recording saved: %s (%d bytes OGG, %d bytes on disk)",
                    final_path,
                    len(ogg_bytes),
                    final_path.stat().st_size,
                )
                return str(final_path)

            except (OSError, ValueError, RuntimeError) as e:
                logger.error("Recording pipeline failed for call %s: %s", db_call_id, e)
                return None
            finally:
                # Cleanup temp files
                for tmp in (tmp_wav, tmp_ogg):
                    if tmp and os.path.exists(tmp):
                        try:
                            os.unlink(tmp)
                        except OSError:
                            pass

    async def _download_wav(self, ultravox_call_id: str, api_key: str) -> str | None:
        """Download WAV recording from Ultravox API."""
        try:
            from app.core.http_clients import recording_client

            response = await recording_client.get(
                f"https://api.ultravox.ai/api/calls/{ultravox_call_id}/recording",
                headers={"X-API-Key": api_key},
            )
            if response.status_code != 200:
                logger.warning("Ultravox recording download failed: %d", response.status_code)
                return None

            # Save to temp file
            fd, tmp_path = tempfile.mkstemp(
                prefix=f"sferaai_rec_{ultravox_call_id[:8]}_", suffix=".wav"
            )
            with os.fdopen(fd, "wb") as f:
                f.write(response.content)

            size_mb = len(response.content) / (1024 * 1024)
            logger.info(
                "Recording downloaded WAV %.1f MB for call %s", size_mb, ultravox_call_id[:8]
            )
            return tmp_path

        except (httpx.HTTPError, OSError) as e:
            logger.error("Recording download failed: %s", e)
            return None

    async def _transcode_to_ogg(self, wav_path: str, call_id: str) -> str | None:
        """Transcode WAV to OGG Opus 32kbps mono using ffmpeg with low priority."""
        fd, ogg_path = tempfile.mkstemp(prefix=f"sferaai_rec_{call_id[:8]}_", suffix=".ogg")
        os.close(fd)

        try:
            process = await asyncio.create_subprocess_exec(
                "nice",
                "-n",
                "19",
                "ffmpeg",
                "-i",
                wav_path,
                "-c:a",
                "libopus",
                "-b:a",
                "32k",
                "-ac",
                "1",
                "-y",
                ogg_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(
                    "Recording ffmpeg failed (code %d): %s",
                    process.returncode,
                    stderr.decode()[:200],
                )
                os.unlink(ogg_path)
                return None

            wav_size = os.path.getsize(wav_path)
            ogg_size = os.path.getsize(ogg_path)
            ratio = wav_size / ogg_size if ogg_size > 0 else 0
            logger.info(
                "Recording transcoded %d -> %d bytes (ratio %.0f:1)", wav_size, ogg_size, ratio
            )
            return ogg_path

        except (OSError, RuntimeError) as e:
            logger.error("Recording transcode failed: %s", e)
            if os.path.exists(ogg_path):
                os.unlink(ogg_path)
            return None

    async def decrypt_recording(self, file_path: str) -> bytes:
        """Decrypt an encrypted recording file and return OGG bytes."""
        raw = await asyncio.to_thread(Path(file_path).read_bytes)
        if self._fernet and file_path.endswith(".enc"):
            return await asyncio.to_thread(self._fernet.decrypt, raw)
        return raw

    def get_expiration_date(self, file_path: str) -> datetime | None:
        """Return when this recording will be deleted (mtime + retention_days)."""
        path = Path(file_path)
        if not path.exists():
            return None
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        return mtime + timedelta(days=self._retention_days)

    async def cleanup_expired(self) -> tuple[int, int]:
        """Delete recordings older than retention_days.

        Returns (files_deleted, bytes_freed).
        """
        return await asyncio.to_thread(self._cleanup_expired_sync)

    def _cleanup_expired_sync(self) -> tuple[int, int]:
        """Synchronous cleanup logic (runs in thread to avoid blocking event loop)."""
        if not self._base_path.exists():
            return 0, 0

        cutoff = datetime.now(UTC) - timedelta(days=self._retention_days)
        deleted = 0
        freed = 0

        for recording_file in self._base_path.rglob("*.*"):
            if not recording_file.is_file():
                continue
            if recording_file.suffix not in (".ogg", ".enc"):
                continue

            mtime = datetime.fromtimestamp(recording_file.stat().st_mtime, tz=UTC)
            if mtime < cutoff:
                size = recording_file.stat().st_size
                try:
                    recording_file.unlink()
                    deleted += 1
                    freed += size
                except OSError as e:
                    logger.warning("Recording cleanup: failed to delete %s: %s", recording_file, e)

        if deleted > 0:
            logger.info(
                "Recording cleanup: deleted %d expired recordings (%.1f MB freed)",
                deleted,
                freed / 1024 / 1024,
            )

        # Remove empty month directories
        for month_dir in self._base_path.rglob("*"):
            if month_dir.is_dir() and not any(month_dir.iterdir()):
                try:
                    month_dir.rmdir()
                except OSError:
                    pass

        return deleted, freed
