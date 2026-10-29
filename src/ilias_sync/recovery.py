"""Actionable recovery from recorded facts; unknown failures stay unknown."""
from dataclasses import dataclass

from .i18n import t


# Older builds sometimes recorded an authentication message under a generic
# state. Recognize only these exact, application-owned messages, never fuzzy
# matches against server text or arbitrary filenames.
SIGN_IN_MESSAGES = {
    'Sign-in expired or was rejected by ILIAS.',
    'Your browser session has expired. Import a new session to continue.',
    'ILIAS rejected the sign-in. Update the saved credentials or import a browser session.',
    'A download returned a login page. Sign in again.',
    'Sign in again. No password is stored for this source.',
}


def needs_signin(status):
    return bool(status.get('login_required') or status.get('state') == 'Sign in again' or status.get('message') in SIGN_IN_MESSAGES)


def failure_kind(error):
    import errno
    import aiohttp
    if isinstance(error, PermissionError):
        return 'permission'
    if isinstance(error, OSError) and error.errno == errno.ENOSPC:
        return 'storage_full'
    if isinstance(error, (aiohttp.ClientConnectionError, aiohttp.ServerTimeoutError, TimeoutError)):
        return 'network'
    return ''


@dataclass(frozen=True)
class RecoveryPlan:
    kind: str
    action: str
    button: str
    explanation: str
    steps: tuple[str, ...]


def recovery_plan(status):
    kind = status.get('failure_kind', '')
    if kind == 'missing':
        return RecoveryPlan('missing', 'retry', t('Restore file'),
            t('This file is missing from its recorded location. Other materials remain available.'),
            (t('1. Check this university to download missing materials again.'),
             t('2. If the file stays missing, check whether it is still available to you in ILIAS. Existing files are never deleted by this repair.')))
    if needs_signin(status):
        return RecoveryPlan('signin', 'signin', t('Renew sign-in'),
            t('ILIAS needs a new sign-in. Existing materials remain in your library; new downloads are waiting.'),
            (t('1. Update the password or import a fresh browser session.'),
             t('2. Save and check. IliasSync tests the sign-in by checking this university.'),
             t('3. The new result confirms whether syncing works again.')))
    if status.get('recovery') == 'folders':
        return RecoveryPlan('folders', 'folders', t('Check folder names'),
            t('Two folders would use the same name. Your existing files have been kept.'),
            (t('1. Choose another folder name or reset its custom name.'),
             t('2. Save the mapping, then IliasSync checks the university again.')))
    if status.get('server_deferred'):
        return RecoveryPlan('server', 'browser', t('Open ILIAS'),
            t('ILIAS asked for a pause. Retrying immediately would not fix it. Your materials remain accessible.'),
            (t('1. Wait until the server pause ends; the planned time is shown above.'),
             t('2. Automatic checks resume at the next eligible scheduled time. With automation off, start a check yourself afterwards.')))
    if kind in {'permission', 'storage_full'}:
        return RecoveryPlan(kind, 'storage', t('Check storage location'),
            t('The device reported insufficient storage space.') if kind == 'storage_full' else t('The device denied file access.'),
            (t('1. Free some storage space; IliasSync will not delete your files.') if kind == 'storage_full' else
             t('1. Check access to the download folder and IliasSync application data.'),
             t('2. Review the download location if needed, then save and check again.')))
    if status.get('state') in {'Needs attention', 'Checking courses'} or (status.get('result') or {}).get('errors'):
        network = kind == 'network'
        return RecoveryPlan('network' if network else 'unknown', 'retry', t('Check again'),
            t('The connection could not be completed. Previously downloaded materials remain accessible.') if network else
            t('The check could not finish. The exact cause is not confirmed; existing materials have been kept.'),
            (t('1. Check your internet or VPN connection and whether ILIAS opens in the browser.') if network else
             t('1. Check the recorded message and whether ILIAS opens in the browser.'),
             t('2. Check again. If it still fails, keep using your files and review the new result below.')))
    if (status.get('result') or {}).get('unavailable'):
        return RecoveryPlan('partial', 'browser', t('Open ILIAS'),
            t('Some downloads were unavailable. The rest of your materials can still be used.'),
            (t('1. Select an affected file below to see its path and the known reason.'),
             t('2. Check its availability in ILIAS. A removed file or missing permission cannot be repaired by repeated syncing.'),
             t('3. When access is restored, check the university again.')))
    return None
