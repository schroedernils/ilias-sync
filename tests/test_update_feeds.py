import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import plistlib
import re
import subprocess
import sys
from types import SimpleNamespace
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts import update_feeds as feeds


VERSION = '2.3.4'
SOURCE_SHA = 'a' * 40
ROOT = Path(__file__).resolve().parents[1]
BASE_URL = 'https://github.com/schroedernils/ilias-sync'
SPARKLE = '{http://www.andymatuschak.org/xml-namespaces/sparkle}'
SUFFIXES = ('macOS-arm64.dmg', 'macOS-x64.dmg', 'Windows-x64-Setup.exe',
            'Windows-x64.zip', 'Linux-x64.deb', 'Linux-x64.tar.gz')


class SyntheticRelease(SimpleNamespace):
    def __repr__(self):
        return '<synthetic release fixture>'


@pytest.fixture
def release(tmp_path, monkeypatch):
    assets = tmp_path / 'assets'
    assets.mkdir()
    # Deterministic synthetic test key; never provision a repository or account key here.
    private = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    seed = base64.b64encode(bytes(range(32))).decode('ascii')
    public_file = tmp_path / 'public-key.txt'
    public_file.write_text(base64.b64encode(private.public_key().public_bytes_raw()).decode('ascii') + '\n')
    monkeypatch.setenv('UPDATE_SIGNING_KEY', seed)
    for suffix in SUFFIXES:
        name = f'IliasSync-{VERSION}-{suffix}'
        data = b'Synthetic package\x00\xff\r\n' + name.encode()
        (assets / name).write_bytes(data)
        (assets / (name + '.sha256')).write_text(hashlib.sha256(data).hexdigest() + '  ' + name + '\n')
    return SyntheticRelease(assets=assets, public_file=public_file, private=private, seed=seed)


@pytest.fixture
def sparkle_tool():
    tool = ROOT / 'build/updaters/sparkle/bin/sign_update'
    if sys.platform != 'darwin' or not tool.is_file():
        pytest.skip('Optional local Sparkle SDK interoperability check requires macOS and downloaded SDK')
    info = tool.parent.parent / 'Sparkle.framework/Versions/B/Resources/Info.plist'
    assert plistlib.loads(info.read_bytes())['CFBundleShortVersionString'] == '2.10.1'
    return tool


def generate(release, notes=''):
    return feeds.generate_feeds(release.assets, VERSION, release.public_file, notes)


def signature(path):
    return base64.b64decode(path.read_bytes().strip(), validate=True)


@pytest.fixture
def staged_release(release, tmp_path):
    generate(release)
    public = tmp_path / 'public-release'
    feeds.stage_release_assets(release.assets, public, VERSION)
    return public


def remote_release(public):
    return {
        'draft': True, 'prerelease': False, 'tag_name': f'v{VERSION}', 'target_commitish': SOURCE_SHA,
        'assets': [
            {'name': path.name, 'state': 'uploaded', 'size': path.stat().st_size,
             'digest': 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in public.iterdir()
        ],
    }


def test_all_archives_are_signed_and_checksum_manifest_is_complete(release):
    generate(release)
    expected_packages = {f'IliasSync-{VERSION}-{suffix}' for suffix in SUFFIXES}
    expected = expected_packages | {name + ext for name in expected_packages for ext in ('.sha256', '.sig')} | {
        'macOS-arm64.xml', 'macOS-x64.xml', 'windows-x64.xml', 'linux-x64.json', 'linux-x64.json.sig', 'SHA256SUMS',
    }
    assert {path.name for path in release.assets.iterdir()} == expected
    checksums = (release.assets / 'SHA256SUMS').read_text().splitlines()
    assert len(checksums) == 6
    for name in expected_packages:
        data = (release.assets / name).read_bytes()
        release.private.public_key().verify(signature(release.assets / (name + '.sig')), data)
        assert hashlib.sha256(data).hexdigest() + '  ' + name in checksums


@pytest.mark.parametrize('feed,suffix,os_name', [
    ('macOS-arm64.xml', 'macOS-arm64.dmg', 'macos'),
    ('macOS-x64.xml', 'macOS-x64.dmg', 'macos'),
    ('windows-x64.xml', 'Windows-x64-Setup.exe', 'windows-x64'),
])
def test_native_appcasts_have_compatible_signed_enclosures(release, feed, suffix, os_name):
    generate(release)
    root = ET.parse(release.assets / feed).getroot()
    assert root.tag == 'rss' and root.attrib == {'version': '2.0'}
    items = root.findall('./channel/item')
    assert len(items) == 1
    item = items[0]
    assert item.findtext(SPARKLE + 'version') == VERSION
    assert item.findtext(SPARKLE + 'shortVersionString') == VERSION
    assert item.findtext(SPARKLE + 'minimumSystemVersion') == ('10.0' if os_name == 'windows-x64' else '13.0.0')
    assert item.findtext('link') == f'{BASE_URL}/releases/tag/v{VERSION}'
    enclosure = item.find('enclosure')
    name = f'IliasSync-{VERSION}-{suffix}'
    data = (release.assets / name).read_bytes()
    assert enclosure.get('url') == f'{BASE_URL}/releases/download/v{VERSION}/{name}'
    assert enclosure.get('length') == str(len(data))
    assert enclosure.get('type') == 'application/octet-stream'
    assert enclosure.get(SPARKLE + 'os') == os_name
    sig = base64.b64decode(enclosure.get(SPARKLE + 'edSignature'), validate=True)
    assert sig == signature(release.assets / (name + '.sig'))
    release.private.public_key().verify(sig, data)


def test_linux_schema_and_detached_signature_cover_exact_feed_and_deb_bytes(release):
    generate(release)
    data = (release.assets / 'linux-x64.json').read_bytes()
    metadata = json.loads(data)
    assert set(metadata) == {'schema', 'version', 'platform', 'url', 'name', 'size', 'sha256', 'signature', 'release_url'}
    assert metadata['schema'] == 1
    assert metadata['version'] == VERSION
    assert metadata['platform'] == 'Linux-x64'
    assert metadata['name'] == f'IliasSync-{VERSION}-Linux-x64.deb'
    assert metadata['url'] == f'{BASE_URL}/releases/download/v{VERSION}/' + metadata['name']
    assert metadata['release_url'] == f'{BASE_URL}/releases/tag/v{VERSION}'
    deb = (release.assets / metadata['name']).read_bytes()
    assert metadata['size'] == len(deb)
    assert metadata['sha256'] == hashlib.sha256(deb).hexdigest()
    release.private.public_key().verify(base64.b64decode(metadata['signature'], validate=True), deb)
    release.private.public_key().verify(signature(release.assets / 'linux-x64.json.sig'), data)


@pytest.mark.parametrize('mutation', ['metadata', 'whitespace', 'wrong-key', 'signature', 'deb'])
def test_tampered_linux_feed_and_archive_or_wrong_key_are_rejected(release, mutation):
    generate(release)
    data = (release.assets / 'linux-x64.json').read_bytes()
    sig = signature(release.assets / 'linux-x64.json.sig')
    public = release.private.public_key()
    if mutation == 'metadata':
        data = data.replace(b'2.3.4', b'9.9.9')
    elif mutation == 'whitespace':
        data = data.rstrip(b'\n')
    elif mutation == 'wrong-key':
        public = Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33))).public_key()
    elif mutation == 'signature':
        sig = bytes([sig[0] ^ 1]) + sig[1:]
    else:
        metadata = json.loads(data)
        data = (release.assets / metadata['name']).read_bytes() + b'tampered'
        sig = base64.b64decode(metadata['signature'])
    with pytest.raises(InvalidSignature):
        public.verify(sig, data)


@pytest.mark.parametrize('suffix', SUFFIXES)
@pytest.mark.parametrize('problem', ['missing', 'empty', 'tampered', 'missing-checksum', 'wrong-checksum-name'])
def test_invalid_or_missing_package_aborts_before_writing_any_outputs(release, suffix, problem):
    name = f'IliasSync-{VERSION}-{suffix}'
    path = release.assets / name
    if problem == 'missing':
        path.unlink()
    elif problem == 'empty':
        path.write_bytes(b'')
    elif problem == 'tampered':
        path.write_bytes(path.read_bytes() + b'tampered')
    elif problem == 'missing-checksum':
        (release.assets / (name + '.sha256')).unlink()
    else:
        (release.assets / (name + '.sha256')).write_text(hashlib.sha256(path.read_bytes()).hexdigest() + '  other.deb\n')
    before = {path.name: path.read_bytes() for path in release.assets.iterdir()}
    with pytest.raises(feeds.FeedError):
        generate(release)
    assert {path.name: path.read_bytes() for path in release.assets.iterdir()} == before


@pytest.mark.parametrize('secret', [None, '', ' ', 'sensitive-invalid-value', 'é' * 44,
                                  base64.b64encode(b'x' * 31).decode(), base64.b64encode(b'x' * 64).decode()])
def test_missing_or_malformed_private_key_fails_closed_without_key_disclosure(release, monkeypatch, capsys, secret):
    if secret is None:
        monkeypatch.delenv('UPDATE_SIGNING_KEY')
    else:
        monkeypatch.setenv('UPDATE_SIGNING_KEY', secret)
    with pytest.raises(SystemExit) as exit_info:
        feeds.main(['--assets', str(release.assets), '--version', VERSION, '--public-key', str(release.public_file)])
    assert exit_info.value.code == 1
    output = capsys.readouterr()
    assert output.out == ''
    assert 'Update-feed generation failed:' in output.err
    if secret and secret.strip():
        assert secret not in output.err
    assert not list(release.assets.glob('*.sig'))
    assert not list(release.assets.glob('*.xml'))


@pytest.mark.parametrize('problem', ['missing', 'invalid', 'wrong-length', 'wrong-key'])
def test_missing_invalid_or_mismatched_public_key_fails_closed(release, problem):
    if problem == 'missing':
        release.public_file.unlink()
    elif problem == 'invalid':
        release.public_file.write_text('not base64')
    elif problem == 'wrong-length':
        release.public_file.write_text(base64.b64encode(b'x' * 64).decode())
    else:
        public = Ed25519PrivateKey.from_private_bytes(b'x' * 32).public_key().public_bytes_raw()
        release.public_file.write_text(base64.b64encode(public).decode())
    with pytest.raises(feeds.FeedError):
        generate(release)
    assert not list(release.assets.glob('*.sig'))


@pytest.mark.parametrize('version', ['1.2.3-beta', '../2.3.4', '1.2.3?url=evil', '1.2', '01.2.3', '１.2.3'])
def test_unsafe_or_nonstable_versions_are_rejected(release, version):
    with pytest.raises(feeds.FeedError, match='Stable semantic version'):
        feeds.generate_feeds(release.assets, version, release.public_file)


def test_release_notes_are_escaped_in_xml_and_rendered_html(release):
    notes = ('Fix "quotes" & <script>alert("unsafe")</script>\nSchröder </description><enclosure url="evil" />\n\n'
             '- **Safer updates**\n- [Read more](https://example.test)\n\n'
             '![tracking](https://example.test/pixel.png) [unsafe](javascript:alert(1))')
    generate(release, notes)
    for name in ('macOS-arm64.xml', 'macOS-x64.xml', 'windows-x64.xml'):
        root = ET.parse(release.assets / name).getroot()
        assert len(root.findall('./channel/item/enclosure')) == 1
        rendered = root.findtext('./channel/item/description')
        assert '<ul>' in rendered and '<strong>Safer updates</strong>' in rendered
        assert '<a href="https://example.test">Read more</a>' in rendered
        assert '&lt;script&gt;' in rendered and '<script>' not in rendered
        assert 'Schröder' in rendered and '<pre>' not in rendered
        assert '<img' not in rendered and 'href="javascript:' not in rendered


def test_urls_are_pinned_to_official_github_release_source(release, monkeypatch):
    monkeypatch.setenv('GITHUB_REPOSITORY', 'attacker/fork')
    monkeypatch.setenv('GITHUB_SERVER_URL', 'https://attacker.invalid')
    generate(release)
    assert feeds.FEED_BASE_URL == f'{BASE_URL}/releases/latest/download'
    metadata = json.loads((release.assets / 'linux-x64.json').read_bytes())
    for name in ('macOS-arm64.xml', 'macOS-x64.xml', 'windows-x64.xml'):
        root = ET.parse(release.assets / name).getroot()
        assert root.find('./channel/item/enclosure').get('url').startswith(f'{BASE_URL}/releases/download/v{VERSION}/')
        assert root.findtext('./channel/link') == f'{BASE_URL}/releases'
    assert metadata['url'].startswith(f'{BASE_URL}/releases/download/v{VERSION}/')
    assert 'latest' not in metadata['url']
    assert metadata['release_url'] == f'{BASE_URL}/releases/tag/v{VERSION}'


def test_rerunning_with_same_inputs_is_byte_for_byte_reproducible(release):
    outputs = generate(release)
    before = {path.name: path.read_bytes() for path in outputs}
    assert {path.name: path.read_bytes() for path in generate(release)} == before


@pytest.mark.parametrize('feed', ['macOS-arm64.xml', 'macOS-x64.xml'])
def test_sparkle_signed_feed_covers_exact_original_xml_bytes(release, feed):
    generate(release, 'UTF-8 byte length: Schröder & <notes>')
    data = (release.assets / feed).read_bytes()
    match = re.fullmatch(rb'(.*)<!-- sparkle-signatures:\nedSignature: ([A-Za-z0-9+/=]+)\nlength: ([0-9]+)\n-->\n',
                         data, re.DOTALL)
    assert match is not None
    original, encoded_sig, length = match.groups()
    assert int(length) == len(original)
    assert original.endswith(b'</rss>\n')
    assert b'sparkle-signatures' not in original
    release.private.public_key().verify(base64.b64decode(encoded_sig, validate=True), original)
    with pytest.raises(InvalidSignature):
        release.private.public_key().verify(base64.b64decode(encoded_sig), original.replace(b'2.3.4', b'9.9.9'))
    with pytest.raises(InvalidSignature):
        Ed25519PrivateKey.from_private_bytes(b'x' * 32).public_key().verify(base64.b64decode(encoded_sig), original)


def test_public_downloads_keep_updater_urls_and_bundle_only_optional_sidecars(release, staged_release):
    required = {f'IliasSync-{VERSION}-{suffix}' for suffix in SUFFIXES} | {
        'macOS-arm64.xml', 'macOS-x64.xml', 'windows-x64.xml', 'linux-x64.json', 'linux-x64.json.sig', 'SHA256SUMS',
    }
    assert {path.name for path in staged_release.iterdir()} == required | {'IliasSync-package-verification.zip'}
    for name in required:
        assert (staged_release / name).read_bytes() == (release.assets / name).read_bytes()
    with ZipFile(staged_release / 'IliasSync-package-verification.zip') as archive:
        assert len(archive.namelist()) == 12
        for suffix in SUFFIXES:
            for extension in ('.sha256', '.sig'):
                name = f'IliasSync-{VERSION}-{suffix}{extension}'
                assert archive.read(name) == (release.assets / name).read_bytes()
    notes = feeds.release_download_links(VERSION)
    assert all(f'/releases/download/v{VERSION}/IliasSync-{VERSION}-{suffix})' in notes for suffix in SUFFIXES)


def test_staging_rejects_incomplete_signature_set(release, tmp_path):
    generate(release)
    next(release.assets.glob('*.dmg.sig')).unlink()
    target = tmp_path / 'public-release'
    with pytest.raises(feeds.FeedError, match='incomplete'):
        feeds.stage_release_assets(release.assets, target, VERSION)
    assert not target.exists()


def test_complete_draft_passes_uploaded_byte_verification(staged_release):
    feeds.verify_uploaded_assets(staged_release, VERSION, SOURCE_SHA, remote_release(staged_release))


@pytest.mark.parametrize('problem', ['missing', 'duplicate', 'extra', 'starter', 'size', 'digest', 'no-digest',
                                   'published', 'prerelease', 'tag', 'source'])
def test_incomplete_or_tampered_uploaded_release_cannot_pass_publish_gate(staged_release, problem):
    remote = deepcopy(remote_release(staged_release))
    if problem == 'missing':
        remote['assets'].pop()
    elif problem == 'duplicate':
        remote['assets'][-1] = remote['assets'][0]
    elif problem == 'extra':
        remote['assets'].append({'name': 'unexpected'})
    elif problem == 'starter':
        remote['assets'][0]['state'] = 'starter'
    elif problem == 'size':
        remote['assets'][0]['size'] += 1
    elif problem == 'digest':
        remote['assets'][0]['digest'] = 'sha256:' + '0' * 64
    elif problem == 'no-digest':
        remote['assets'][0].pop('digest')
    elif problem == 'published':
        remote['draft'] = False
    elif problem == 'prerelease':
        remote['prerelease'] = True
    elif problem == 'tag':
        remote['tag_name'] = 'v9.9.9'
    else:
        remote['target_commitish'] = 'b' * 40
    with pytest.raises(feeds.FeedError):
        feeds.verify_uploaded_assets(staged_release, VERSION, SOURCE_SHA, remote)


def test_local_tampering_after_upload_fails_publish_gate(staged_release):
    remote = remote_release(staged_release)
    path = staged_release / 'linux-x64.json'
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(feeds.FeedError):
        feeds.verify_uploaded_assets(staged_release, VERSION, SOURCE_SHA, remote)


def test_output_symlink_is_rejected_before_any_generated_file_is_written(release, tmp_path):
    target = tmp_path / 'preserved'
    target.write_bytes(b'preserve this file')
    try:
        (release.assets / 'macOS-arm64.xml').symlink_to(target)
    except OSError:
        pytest.skip('Creating symlinks requires privileges on this host')
    with pytest.raises(feeds.FeedError, match='symlink'):
        generate(release)
    assert target.read_bytes() == b'preserve this file'
    assert not list(release.assets.glob('*.sig'))


def test_pure_ed25519_signature_matches_rfc8032_test_vector():
    # RFC 8032 section 7.1, TEST 1 (empty message), independent of generated feed fixtures.
    private = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(
        '9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60'))
    expected = bytes.fromhex(
        'e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155'
        '5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b')
    assert base64.b64decode(feeds._signature(private, b'')) == expected


def test_archive_signature_matches_sparkle_sdk_when_available(release, sparkle_tool):
    generate(release)
    package = release.assets / f'IliasSync-{VERSION}-macOS-arm64.dmg'
    result = subprocess.run([str(sparkle_tool), '--ed-key-file', '-', '-p', str(package)],
                            input=release.seed + '\n', text=True, capture_output=True, check=True)
    assert base64.b64decode(result.stdout.strip(), validate=True) == signature(Path(str(package) + '.sig'))


@pytest.mark.parametrize('feed', ['macOS-arm64.xml', 'macOS-x64.xml'])
def test_signed_feed_matches_and_verifies_with_sparkle_sdk_when_available(release, sparkle_tool, feed):
    generate(release, 'Schröder & <notes>')
    path = release.assets / feed
    signed_xml = path.read_bytes()
    result = subprocess.run([str(sparkle_tool), '--verify', '--ed-key-file', '-', str(path)],
                            input=release.seed + '\n', text=True, capture_output=True)
    assert result.returncode == 0, 'Official Sparkle SDK rejected the generated feed signature'
    # Have the official tool sign the identical unsigned XML and require identical final bytes.
    original = signed_xml.split(b'<!-- sparkle-signatures:\n')[0]
    path.write_bytes(original)
    subprocess.run([str(sparkle_tool), '--ed-key-file', '-', '--disable-signing-warning', str(path)],
                   input=release.seed + '\n', text=True, capture_output=True, check=True)
    assert path.read_bytes() == signed_xml
    wrong_key = subprocess.run([str(sparkle_tool), '--verify', '--ed-key-file', '-', str(path)],
                               input=base64.b64encode(b'x' * 32).decode() + '\n', text=True, capture_output=True)
    assert wrong_key.returncode != 0
    path.write_bytes(signed_xml.replace(b'2.3.4', b'9.9.9'))
    tampered = subprocess.run([str(sparkle_tool), '--verify', '--ed-key-file', '-', str(path)],
                              input=release.seed + '\n', text=True, capture_output=True)
    assert tampered.returncode != 0
