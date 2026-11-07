"""Utilidades de caché para respuestas pesadas.

* ``TTLCache``: caché en memoria por proceso con caducidad y tamaño máximo.
* ``cached_bytes_response``: devuelve un cuerpo ya serializado con ``ETag`` y
  ``Cache-Control``, y responde 304 si el navegador ya tiene esa versión.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import OrderedDict
from typing import Any

from fastapi import Request, Response


class TTLCache:
    """Caché LRU con caducidad, seguro entre hilos (se usa desde el threadpool)."""

    def __init__(self, maxsize: int = 128, ttl: float = 600.0) -> None:
        self.maxsize, self.ttl = maxsize, ttl
        self._data: OrderedDict[Any, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()

    _MISSING = object()

    def get(self, key: Any, default: Any = None) -> Any:
        with self._lock:
            item = self._data.get(key, self._MISSING)
            if item is self._MISSING:
                return default
            expires, value = item
            if expires < time.monotonic():
                del self._data[key]
                return default
            self._data.move_to_end(key)
            return value

    def set(self, key: Any, value: Any) -> None:
        with self._lock:
            self._data[key] = (time.monotonic() + self.ttl, value)
            self._data.move_to_end(key)
            while len(self._data) > self.maxsize:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        return len(self._data)


def dumps(obj: Any) -> bytes:
    """JSON compacto en UTF-8 (sin espacios: ~15 % menos bytes que la salida por defecto)."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")


def etag_for(body: bytes) -> str:
    return '"' + hashlib.blake2b(body, digest_size=12).hexdigest() + '"'


def cached_bytes_response(request: Request, body: bytes, etag: str | None = None, *,
                          media_type: str = "application/json", max_age: int = 300) -> Response:
    etag = etag or etag_for(body)
    headers = {"ETag": etag, "Cache-Control": f"public, max-age={max_age}"}
    if etag in request.headers.get("if-none-match", ""):
        return Response(status_code=304, headers=headers)
    return Response(content=body, media_type=media_type, headers=headers)
