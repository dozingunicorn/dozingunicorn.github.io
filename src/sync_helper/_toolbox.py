"""
sync-images toolbox: utilities for sync-images

.. moduleauthor: John Purcell

"""

from collections import namedtuple
import pathlib

import b2sdk.v3 as b2sdk
from click import pass_context
from loguru import logger

b2sdk_enums = namedtuple(
    "b2sdk_enums",
    [
        "MetadataDirectiveMode",
        "NewerFileSyncMode",
        "CompareVersionMode",
        "KeepOrDeleteMode",
    ],
)


def is_local_empty(folder: pathlib.Path, ignored_files: dict | None = None) -> bool:
    if ignored_files is None:
        ignored_files = {".DS_Store"}

    return not any(item.name not in ignored_files for item in folder.iterdir())


def sync_enums(is_force: bool, is_empty: bool) -> b2sdk_enums:
    """standardizes which copy/sync modes to use
    https://b2-sdk-python.readthedocs.io/en/master/api/enums.html#enums

    Args:
        is_force (bool): if --force is set, do not be graceful
        is_empty (bool): if destination is not empty, use different profile than default

    Returns:
        b2sdk_enums: namedTuple with b2sdk enum values set

    """
    if is_force:
        logger.warning("`--force` is set, sync will delete DEST files")
        return b2sdk_enums(
            b2sdk.MetadataDirectiveMode.REPLACE,
            b2sdk.NewerFileSyncMode.REPLACE,
            b2sdk.CompareVersionMode.NONE,
            b2sdk.KeepOrDeleteMode.DELETE,
        )
    if not is_empty:
        logger.warning("DEST is not empty, sync will skip DEST files")
        return b2sdk_enums(
            b2sdk.MetadataDirectiveMode.COPY,
            b2sdk.NewerFileSyncMode.SKIP,
            b2sdk.CompareVersionMode.MODTIME,
            b2sdk.KeepOrDeleteMode.DELETE,
        )
    return b2sdk_enums(
        b2sdk.MetadataDirectiveMode.REPLACE,
        b2sdk.NewerFileSyncMode.RAISE_ERROR,
        b2sdk.CompareVersionMode.MODTIME,
        b2sdk.KeepOrDeleteMode.NO_DELETE,
    )


def authorize_b2(
    application_key_id: str,
    application_key: str,
    realm: str = "production",
    accountInfo: b2sdk.AbstractAccountInfo = b2sdk.InMemoryAccountInfo(),
) -> b2sdk.B2Api:
    """Returns authorized b2 SDK object

    NOTE:
        `authorize_account` does not throw errors if keypair is invalid

    Args:
        application_key_id (str): b2 application key id (SECRET)
        application_key (str): b2 application key
        realm (str, optional): b2sdk.B2Api.authorize_account optional arg
        accountInfo (b2sdk.AbstractAccountInfo, optional): https://b2-sdk-python.readthedocs.io/en/master/api/account_info.html#accountinfo

    Returns:
        b2sdk.B2Api: authorized b2 SDK object

    """
    b2_api = b2sdk.B2Api(accountInfo)
    b2_api.authorize_account(application_key_id, application_key, realm=realm)
    return b2_api
