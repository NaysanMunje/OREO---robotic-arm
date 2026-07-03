"""Generate a local dev TLS cert (self-signed) for iPhone camera / getUserMedia."""

from __future__ import annotations

import datetime
import ipaddress
import socket
from pathlib import Path

UTC = datetime.timezone.utc


def local_lan_ip() -> str | None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return None


def ensure_dev_cert(cert_dir: Path) -> tuple[Path, Path]:
    """Create or reuse dev-cert.pem + dev-key.pem with LAN IP in SAN."""
    cert_dir.mkdir(parents=True, exist_ok=True)
    cert_file = cert_dir / "dev-cert.pem"
    key_file = cert_dir / "dev-key.pem"
    lan_ip = local_lan_ip()

    if cert_file.is_file() and key_file.is_file():
        return cert_file, key_file

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "arm-twin-local")])

    alt_names: list[x509.GeneralName] = [
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
    ]
    if lan_ip:
        alt_names.append(x509.IPAddress(ipaddress.IPv4Address(lan_ip)))

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(UTC))
        .not_valid_after(datetime.datetime.now(UTC) + datetime.timedelta(days=825))
        .add_extension(x509.SubjectAlternativeName(alt_names), critical=False)
        .sign(key, hashes.SHA256())
    )

    key_file.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return cert_file, key_file
