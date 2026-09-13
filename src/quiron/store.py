"""Durable, serialized filesystem primitives used by mutating commands."""

from __future__ import annotations

import os
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, cast

if TYPE_CHECKING:
    from .vault import Vault

LOCK_NAME = ".quiron.lock"
LOCK_TIMEOUT_SECONDS = 30.0
_held_locks = threading.local()


def atomic_write_text(path: Path, content: str) -> None:
    """Replace a text file only after its complete contents are durable."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
        _fsync_directory(path.parent)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def _fsync_directory(directory: Path) -> None:
    if os.name == "nt":
        return
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def vault_lock(vault: Vault, timeout: float = LOCK_TIMEOUT_SECONDS) -> Iterator[None]:
    """Serialize read-modify-write operations across processes."""
    key = str(vault.root.resolve())
    locks = getattr(_held_locks, "values", {})
    held = locks.get(key)
    if held is not None:
        locks[key] = (held[0], held[1] + 1)
        try:
            yield
        finally:
            handle, count = locks[key]
            if count == 1:
                del locks[key]
            else:
                locks[key] = (handle, count - 1)
        return

    lock_path = vault.root / LOCK_NAME
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    _held_locks.values = locks
    with lock_path.open("a+b") as handle:
        if os.name == "nt":
            _lock_windows(handle, timeout)
        else:
            _lock_posix(handle, timeout)
        locks[key] = (handle, 1)
        try:
            yield
        finally:
            del locks[key]
            if os.name == "nt":
                import msvcrt

                msvcrt_api = cast(Any, msvcrt)
                handle.seek(0)
                msvcrt_api.locking(handle.fileno(), msvcrt_api.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _lock_windows(handle, timeout: float) -> None:
    import msvcrt

    msvcrt_api = cast(Any, msvcrt)
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
    deadline = time.monotonic() + timeout
    while True:
        handle.seek(0)
        try:
            msvcrt_api.locking(handle.fileno(), msvcrt_api.LK_NBLCK, 1)
            return
        except OSError:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"could not acquire vault lock: {handle.name}")
            time.sleep(0.05)


def _lock_posix(handle, timeout: float) -> None:
    import fcntl

    fcntl_api = cast(Any, fcntl)
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl_api.flock(handle.fileno(), fcntl_api.LOCK_EX | fcntl_api.LOCK_NB)
            return
        except BlockingIOError:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"could not acquire vault lock: {handle.name}")
            time.sleep(0.05)
