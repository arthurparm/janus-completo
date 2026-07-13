#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _subject(common_name: str) -> x509.Name:
    return x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Janus Local"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )


def _san_entry(value: str) -> x509.GeneralName:
    try:
        return x509.IPAddress(ipaddress.ip_address(value))
    except ValueError:
        return x509.DNSName(value)


def _write_private_key(path: Path, key: rsa.RSAPrivateKey) -> None:
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )


def _write_cert(path: Path, cert: x509.Certificate) -> None:
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def generate_qdrant_tls_cert(output_dir: Path, names: list[str], valid_days: int) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)

    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(_subject("Janus Local Qdrant CA"))
        .issuer_name(_subject("Janus Local Qdrant CA"))
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=valid_days))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=False,
                key_cert_sign=True,
                key_agreement=False,
                content_commitment=False,
                data_encipherment=False,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )

    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    san_values = sorted(set(name.strip() for name in names if name.strip()))
    if not san_values:
        raise ValueError("At least one DNS name or IP address is required.")
    server_cert = (
        x509.CertificateBuilder()
        .subject_name(_subject("Janus Local Qdrant"))
        .issuer_name(ca_cert.subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=valid_days))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName([_san_entry(value) for value in san_values]),
            critical=False,
        )
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )

    _write_private_key(output_dir / "ca.key", ca_key)
    _write_cert(output_dir / "ca.pem", ca_cert)
    _write_private_key(output_dir / "key.pem", server_key)
    _write_cert(output_dir / "cert.pem", server_cert)
    (output_dir / "SAN.txt").write_text("\n".join(san_values) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate local TLS certs for Janus Qdrant.")
    parser.add_argument("--out-dir", default=".secrets/qdrant")
    parser.add_argument("--valid-days", type=int, default=397)
    parser.add_argument(
        "--name",
        action="append",
        default=[],
        help="DNS name or IP address to include as a certificate SAN. Can be repeated.",
    )
    parser.add_argument(
        "--include-env-hosts",
        action="store_true",
        help="Include QDRANT_HOST values from .env.pc1 and .env.pc2 when present.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = (repo_root / args.out_dir).resolve()
    names = [
        "localhost",
        "host.docker.internal",
        "qdrant",
        "janus_qdrant_pc2",
        "127.0.0.1",
        "::1",
        *args.name,
    ]
    if args.include_env_hosts:
        for env_name in (".env.pc1", ".env.pc2"):
            qdrant_host = _parse_env_file(repo_root / env_name).get("QDRANT_HOST", "")
            if qdrant_host:
                names.append(qdrant_host)

    generate_qdrant_tls_cert(output_dir=output_dir, names=names, valid_days=args.valid_days)
    print(f"Generated Qdrant TLS material in {output_dir}")
    print("Files: ca.pem, cert.pem, key.pem, SAN.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
