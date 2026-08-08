from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

OUTPUT = Path(os.environ.get("OIDC_FIXTURE_DIR", "/fixture"))
FIXTURE_FILES = {
    "ca.pem",
    "server-cert.pem",
    "server-key.pem",
    "signing-key.pem",
    "fixture.json",
}


def _write_private_key(path: Path, key: rsa.RSAPrivateKey) -> None:
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    path.chmod(0o600)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if all((OUTPUT / name).is_file() for name in FIXTURE_FILES):
        return
    now = datetime.now(UTC)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Janus test OIDC CA")])
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(ca_key, hashes.SHA256())
    )

    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "idp.test")])
    server_cert = (
        x509.CertificateBuilder()
        .subject_name(server_name)
        .issuer_name(ca_name)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("idp.test"),
                    x509.DNSName("localhost"),
                    x509.IPAddress(__import__("ipaddress").ip_address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    _write_private_key(OUTPUT / "server-key.pem", server_key)
    _write_private_key(OUTPUT / "signing-key.pem", signing_key)
    (OUTPUT / "ca.pem").write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
    (OUTPUT / "server-cert.pem").write_bytes(
        server_cert.public_bytes(serialization.Encoding.PEM)
    )
    (OUTPUT / "fixture.json").write_text(
        json.dumps({"kid": "janus-auth-integration-1"}), encoding="utf-8"
    )
    for path in OUTPUT.iterdir():
        os.chown(path, 1000, 1000)
        if path.name not in {"server-key.pem", "signing-key.pem"}:
            path.chmod(0o644)
    os.chown(OUTPUT, 1000, 1000)


if __name__ == "__main__":
    main()
