"""Saved pocket metadata and opt-in OS credential-vault integration.

The profiles JSON contains no passwords, hashes, tokens or recovery material.
On Linux the desktop Secret Service/KWallet backend must be configured; a
missing vault is an explicit error, never a plaintext fallback.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4


SERVICE = "io.matt88.pocket-radio-manager"
MAX_PROFILES = 100


class CredentialStoreError(RuntimeError):
    pass


@dataclass(frozen=True)
class PocketProfile:
    id: str
    alias: str
    host: str
    username: str = "admin"
    model: str = ""

    def __post_init__(self):
        from ipaddress import ip_address, IPv4Address
        try:
            value = ip_address(self.host)
        except ValueError as exc:
            raise ValueError("Host deve essere un indirizzo IP valido") from exc
        if not isinstance(value, IPv4Address) or not (value.is_private or value.is_link_local):
            raise ValueError("Consentiti solo indirizzi IPv4 privati/link-local")
        if not self.alias.strip() or not self.username.strip() or not self.id:
            raise ValueError("Alias, username e id non possono essere vuoti")
        if len(self.alias) > 100 or len(self.username) > 100:
            raise ValueError("Alias o username troppo lungo")


class ProfileStore:
    def __init__(self, directory: Path | None = None, vault=None):
        if directory is None:
            from platformdirs import user_data_path
            directory = user_data_path("pocket-radio-manager", "matt88")
        self.directory = Path(directory)
        self.file = self.directory / "devices.json"
        self._vault = vault  # Injectable mock for tests; None means OS keyring.

    @property
    def vault(self):
        if self._vault is None:
            try:
                import keyring
            except ImportError as exc:
                raise CredentialStoreError("Keyring non installato") from exc
            backend = keyring.get_keyring()
            module = type(backend).__module__.lower()
            # Fail closed: third-party plaintext files and chainer fallbacks
            # are NOT equivalent to an operating-system credential vault.
            allowed = (
                "keyring.backends.secretservice",
                "keyring.backends.kwallet",
                "keyring.backends.windows",
                "keyring.backends.macos",
            )
            if not module.startswith(allowed):
                raise CredentialStoreError(
                    "Portachiavi OS protetto non disponibile; nessun salvataggio in chiaro"
                )
            return keyring
        return self._vault

    @staticmethod
    def new_profile(alias: str, host: str, username: str = "admin",
                    model: str = "") -> PocketProfile:
        return PocketProfile(id=uuid4().hex, alias=alias, host=host,
                             username=username, model=model)

    def list(self) -> list[PocketProfile]:
        if not self.file.exists():
            return []
        try:
            raw = json.loads(self.file.read_text(encoding="utf-8"))
            if not isinstance(raw, list) or len(raw) > MAX_PROFILES:
                raise ValueError("Archivio dispositivi non valido")
            return [PocketProfile(**item) for item in raw]
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError("Impossibile leggere archivio pocket; nessun dato sovrascritto") from exc

    def _write(self, profiles: list[PocketProfile]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        if os.name == "posix":
            os.chmod(self.directory, 0o700)
        data = json.dumps([asdict(profile) for profile in profiles], ensure_ascii=False, indent=2)
        fd, name = tempfile.mkstemp(prefix=".devices-", suffix=".tmp", dir=str(self.directory))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as writer:
                writer.write(data)
                writer.write("\n")
            if os.name == "posix":
                os.chmod(name, 0o600)
            os.replace(name, self.file)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def save(self, profile: PocketProfile, *, remember_password: bool = False,
             password: str | None = None) -> None:
        """Persist profile; credential is saved ONLY on explicit opt-in."""
        existing = self.list()
        if remember_password:
            if not password:
                raise ValueError("Password richiesta per salvataggio protetto")
            try:
                self.vault.set_password(SERVICE, profile.id, password)
            except Exception as exc:
                raise CredentialStoreError(
                    "Portachiavi OS non disponibile: credenziali NON salvate"
                ) from exc
        # A profile may be saved without any stored credential.
        existing = [item for item in existing if item.id != profile.id]
        if len(existing) >= MAX_PROFILES:
            raise ValueError("Numero massimo di dispositivi salvati raggiunto")
        existing.append(profile)
        self._write(existing)

    def credential(self, profile_id: str) -> str | None:
        try:
            return self.vault.get_password(SERVICE, profile_id)
        except Exception as exc:
            raise CredentialStoreError("Impossibile leggere il portachiavi OS") from exc

    def forget_credential(self, profile_id: str) -> None:
        try:
            self.vault.delete_password(SERVICE, profile_id)
        except Exception as exc:
            # keyring backends vary; a missing value is not a fatal error.
            if exc.__class__.__name__ not in {"PasswordDeleteError"}:
                raise CredentialStoreError("Impossibile eliminare credenziali salvate") from exc

    def delete(self, profile_id: str) -> None:
        existing = self.list()
        if not any(p.id == profile_id for p in existing):
            return
        # Delete vault entry first so removal cannot orphan credentials.
        self.forget_credential(profile_id)
        self._write([p for p in existing if p.id != profile_id])
