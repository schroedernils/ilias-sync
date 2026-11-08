"""Generate GitHub Release appcasts and signatures without exposing the signing seed."""
from __future__ import annotations

import argparse
import base64
import binascii
from dataclasses import dataclass
import hashlib
import html
import json
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


REPOSITORY_URL = 'https://github.com/schroedernils/ilias-sync'
FEED_BASE_URL = f'{REPOSITORY_URL}/releases/latest/download'
SPARKLE_NAMESPACE = 'http://www.andymatuschak.org/xml-namespaces/sparkle'
PACKAGE_SUFFIXES = (
    'macOS-arm64.dmg', 'macOS-x64.dmg', 'Windows-x64-Setup.exe',
    'Windows-x64.zip', 'Linux-x64.deb', 'Linux-x64.tar.gz',
)
FEED_NAMES = ('macOS-arm64.xml', 'macOS-x64.xml', 'windows-x64.xml', 'linux-x64.json', 'linux-x64.json.sig')

ET.register_namespace('sparkle', SPARKLE_NAMESPACE)


class FeedError(ValueError):
    """A release input failed validation; messages must never contain private key data."""


@dataclass(frozen=True)
class SignedPackage:
    name: str
    url: str
    size: int
    sha256: str
    signature: str


def package_names(version: str) -> tuple[str, ...]:
    component = r'(?:0|[1-9][0-9]*)'
    if not re.fullmatch(rf'{component}\.{component}\.{component}', version):
        raise FeedError('Stable semantic version required')
    return tuple(f'IliasSync-{version}-{suffix}' for suffix in PACKAGE_SUFFIXES)


def release_asset_names(version: str) -> set[str]:
    names = package_names(version)
    return set(names) | {name + suffix for name in names for suffix in ('.sha256', '.sig')} | set(FEED_NAMES) | {
        'SHA256SUMS',
    }


def _decode_key(value: str, label: str) -> bytes:
    try:
        encoded = value.strip().encode('ascii')
        raw = base64.b64decode(encoded, validate=True)
    except (UnicodeError, ValueError, binascii.Error):
        raise FeedError(f'{label} must be base64 encoding of exactly 32 raw bytes') from None
    if len(raw) != 32 or base64.b64encode(raw) != encoded:
        raise FeedError(f'{label} must be base64 encoding of exactly 32 raw bytes')
    return raw


def _signing_key(public_key_file: Path) -> Ed25519PrivateKey:
    secret = os.environ.get('UPDATE_SIGNING_KEY', '')
    if not secret.strip():
        raise FeedError('UPDATE_SIGNING_KEY is required; unsigned releases are forbidden')
    private_key = Ed25519PrivateKey.from_private_bytes(_decode_key(secret, 'UPDATE_SIGNING_KEY'))
    try:
        encoded_public = public_key_file.read_text(encoding='ascii')
    except (OSError, UnicodeError):
        raise FeedError('A readable updates/public-key.txt is required') from None
    public = _decode_key(encoded_public, 'Update public key')
    if private_key.public_key().public_bytes_raw() != public:
        raise FeedError('UPDATE_SIGNING_KEY does not match the update public key')
    return private_key


def _signature(private_key: Ed25519PrivateKey, data: bytes) -> str:
    # Pure Ed25519 over the original bytes, not Ed25519ph or a SHA-256 digest.
    return base64.b64encode(private_key.sign(data)).decode('ascii')


def _signed_packages(assets: Path, version: str, private_key: Ed25519PrivateKey) -> dict[str, SignedPackage]:
    packages = {}
    for name in package_names(version):
        path = assets / name
        checksum = assets / (name + '.sha256')
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise FeedError(f'Missing or empty package: {name}')
        if checksum.is_symlink() or not checksum.is_file():
            raise FeedError(f'Missing checksum: {name}.sha256')
        try:
            recorded = checksum.read_text(encoding='ascii').strip()
        except UnicodeError:
            raise FeedError(f'Invalid checksum: {name}.sha256') from None
        match = re.fullmatch(r'([0-9a-f]{64})  ' + re.escape(name), recorded)
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if not match or match[1] != digest:
            raise FeedError(f'Checksum mismatch: {name}')
        packages[name] = SignedPackage(
            name, f'{REPOSITORY_URL}/releases/download/v{version}/{name}', len(data), digest,
            _signature(private_key, data),
        )
    return packages


def _appcast(version: str, platform: str, package: SignedPackage, release_notes: str) -> bytes:
    rss = ET.Element('rss', {'version': '2.0'})
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, 'title').text = f'IliasSync {platform} updates'
    ET.SubElement(channel, 'link').text = f'{REPOSITORY_URL}/releases'
    ET.SubElement(channel, 'description').text = f'Stable IliasSync updates for {platform}'
    ET.SubElement(channel, 'language').text = 'en'
    item = ET.SubElement(channel, 'item')
    ET.SubElement(item, 'title').text = f'IliasSync {version}'
    ET.SubElement(item, 'link').text = f'{REPOSITORY_URL}/releases/tag/v{version}'
    ET.SubElement(item, f'{{{SPARKLE_NAMESPACE}}}version').text = version
    ET.SubElement(item, f'{{{SPARKLE_NAMESPACE}}}shortVersionString').text = version
    ET.SubElement(item, f'{{{SPARKLE_NAMESPACE}}}minimumSystemVersion').text = (
        '10.0' if platform == 'Windows-x64' else '13.0.0'
    )
    # Escape notes as HTML as well as XML, since native updaters render description HTML.
    ET.SubElement(item, 'description').text = '<pre>' + html.escape(release_notes or f'IliasSync {version}') + '</pre>'
    ET.SubElement(item, 'enclosure', {
        'url': package.url, 'length': str(package.size), 'type': 'application/octet-stream',
        f'{{{SPARKLE_NAMESPACE}}}edSignature': package.signature,
        f'{{{SPARKLE_NAMESPACE}}}os': 'windows-x64' if platform == 'Windows-x64' else 'macos',
    })
    ET.indent(rss, space='  ')
    return ET.tostring(rss, encoding='utf-8', xml_declaration=True) + b'\n'


def _signed_appcast(private_key: Ed25519PrivateKey, data: bytes) -> bytes:
    # Sparkle 2.10.1's --disable-signing-warning format: sign the unchanged XML prefix,
    # record its byte length, then append the signature comment outside the signed range.
    trailer = f'<!-- sparkle-signatures:\nedSignature: {_signature(private_key, data)}\nlength: {len(data)}\n-->\n'
    return data + trailer.encode('ascii')


def generate_feeds(assets: Path, version: str, public_key_file: Path, release_notes: str = '') -> list[Path]:
    """Validate all six packages first, then write appcasts, package signatures and signed Linux metadata."""
    package_names(version)
    private_key = _signing_key(public_key_file)
    packages = _signed_packages(assets, version, private_key)
    outputs = {name + '.sig': (package.signature + '\n').encode('ascii') for name, package in packages.items()}
    for feed, platform, suffix in (
        ('macOS-arm64.xml', 'macOS-arm64', 'macOS-arm64.dmg'),
        ('macOS-x64.xml', 'macOS-x64', 'macOS-x64.dmg'),
        ('windows-x64.xml', 'Windows-x64', 'Windows-x64-Setup.exe'),
    ):
        appcast = _appcast(version, platform, packages[f'IliasSync-{version}-{suffix}'], release_notes)
        outputs[feed] = _signed_appcast(private_key, appcast) if platform.startswith('macOS') else appcast
    deb = packages[f'IliasSync-{version}-Linux-x64.deb']
    metadata = {
        'schema': 1, 'version': version, 'platform': 'Linux-x64', 'url': deb.url, 'name': deb.name,
        'size': deb.size, 'sha256': deb.sha256, 'signature': deb.signature,
        'release_url': f'{REPOSITORY_URL}/releases/tag/v{version}',
    }
    linux_json = (json.dumps(metadata, sort_keys=True, indent=2) + '\n').encode('utf-8')
    outputs['linux-x64.json'] = linux_json
    outputs['linux-x64.json.sig'] = (_signature(private_key, linux_json) + '\n').encode('ascii')
    outputs['SHA256SUMS'] = ''.join(f'{package.sha256}  {name}\n' for name, package in sorted(packages.items())).encode()
    if any((assets / name).is_symlink() for name in outputs):
        raise FeedError('Refusing to overwrite a symlink in release outputs')
    # No output is written until every package, checksum and key has passed validation.
    for name, data in outputs.items():
        (assets / name).write_bytes(data)
    return [assets / name for name in sorted(outputs)]


def verify_uploaded_assets(assets: Path, version: str, source_sha: str, release: dict) -> None:
    """Require a complete draft with GitHub-reported SHA-256 digests matching local release bytes."""
    if (release.get('draft') is not True or release.get('prerelease') is not False
            or release.get('tag_name') != f'v{version}' or release.get('target_commitish') != source_sha):
        raise FeedError('Expected a stable draft release at the verified source commit')
    expected = release_asset_names(version)
    if {path.name for path in assets.iterdir()} != expected:
        raise FeedError('Local release asset set is incomplete or unexpected')
    remote = release.get('assets', [])
    if len(remote) != len(expected) or {asset.get('name') for asset in remote} != expected:
        raise FeedError('Uploaded release asset set is incomplete or unexpected')
    for asset in remote:
        path = assets / asset['name']
        if path.is_symlink() or not path.is_file():
            raise FeedError('Local release asset is not a regular file')
        with path.open('rb') as stream:
            digest = 'sha256:' + hashlib.file_digest(stream, 'sha256').hexdigest()
        if (asset.get('state') != 'uploaded' or asset.get('size') != path.stat().st_size
                or asset.get('digest') != digest):
            raise FeedError('Uploaded release asset bytes do not match the validated local files')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, default=Path('release-assets'))
    parser.add_argument('--version', required=True)
    parser.add_argument('--public-key', type=Path, default=Path('updates/public-key.txt'))
    parser.add_argument('--release-notes', type=Path)
    args = parser.parse_args(argv)
    try:
        notes = args.release_notes.read_text(encoding='utf-8') if args.release_notes else ''
        generate_feeds(args.assets, args.version, args.public_key, notes)
    except FeedError as exc:
        parser.exit(1, f'Update-feed generation failed: {exc}\n')
    except (OSError, UnicodeError):
        parser.exit(1, 'Update-feed generation failed: could not read or write release files\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
