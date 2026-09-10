"""
sync-images toolbox: utilities for sync-images

.. moduleauthor: John Purcell

"""

from collections import namedtuple
from dataclasses import dataclass, field
import pathlib
import re

import b2sdk.v3 as b2sdk
from loguru import logger
from PIL import Image

b2sdk_enums = namedtuple(
    "b2sdk_enums",
    [
        "MetadataDirectiveMode",
        "NewerFileSyncMode",
        "CompareVersionMode",
        "KeepOrDeleteMode",
    ],
)

syncFile = namedtuple("syncFile", ["full_pathlib", "b2_filepath"])


@dataclass
class B2Bucket:
    b2_fullpath: str
    bucket_name: str = field(init=False)
    folder_path: str = field(init=False)

    def __post_init__(self):
        self.bucket_name = (
            re.search(r"\/([a-zA-Z\-]+)", self.b2_fullpath).group(0).strip("/")
        )
        self.folder_path = self.b2_fullpath.split(self.bucket_name)[1].strip("/")


@dataclass
class B2Filepath:
    b2_bucket: B2Bucket
    full_filepath: pathlib.Path
    common_rootpath: pathlib.Path
    simple_filepath: str = field(init=False)
    bucket_path: str = field(
        init=False
    )  # b2_bucket.bucket_path/(full_filepath - common_rootpath)
    full_b2path: str = field(
        init=False
    )  # b2://bucket.bucket_name/bucket.bucket_path/pat
    local_path: str = field(init=False)

    def __post_init__(self):
        self.simple_filepath = str(self.full_filepath.relative_to(self.common_rootpath))

        path_elements = []
        if self.b2_bucket.folder_path:
            path_elements.append(self.b2_bucket.folder_path)
        path_elements.append(self.simple_filepath)

        self.bucket_path = "/".join(path_elements)
        self.full_b2path = f"b2://{self.b2_bucket.bucket_name}/{self.bucket_path}"

        self.local_path = str(self.full_filepath.resolve())

    def __str__(self):
        return self.full_b2path


def generate_thumbnail(
    original_image: pathlib.Path,
    file_suffix: str = "-thumb",
    thumbnail_size: tuple[int, int] = (400, 400),
    quality: int = 82,
):
    """generates thumbail and saves it at '{original_image.name}{file_suffix}.{original_image.suffix}'"""
    thumb_path = (
        original_image.parent
        / f"{original_image.stem}{file_suffix}{original_image.suffix}"
    )
    with Image.open(original_image) as pil_image:
        pil_image.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
        pil_image.save(thumb_path, "jpeg", quality=quality)


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


def list_files(
    head_path: pathlib.Path,
    skip_string: str | None = "",
    required_ext: set | None = None,
    ignored_files: set | None = None,
) -> list[pathlib.Path]:
    """returns a list of files in `head_path`, skips `ignore_files` or files without `required_ext`.  returns list of files

    NOTE:
        directory paths are skipped, only returns paths to files
    Args:
        head_path (pathlib.Path): top-of-directory to search
        skip_string (str, optional): filename substring to skip
        required_ext (set, Optional): file extensions to include
        ignored_files (set, Optional): ignored files to skip

    Returns:
        list[pathlib.Path]: list of valid files in `head_path`
    """
    if ignored_files is None:
        ignored_files = {".DS_Store", ".bzEmpty", ".hedge-enabled"}

    return_list = []
    for x in head_path.rglob("*"):
        # NOTE: return needs a len() for click.progressbar()
        # generators do not support len()
        if x.name in ignored_files:
            continue
        if x.is_dir():
            continue
        if skip_string and skip_string in x.name:
            continue
        if required_ext and x.suffix not in required_ext:
            continue

        return_list.append(x)

    return return_list


def authorize_b2(
    application_key_id: str,
    application_key: str,
    realm: str = "production",
    account_info: b2sdk.AbstractAccountInfo = b2sdk.InMemoryAccountInfo(),
) -> b2sdk.B2Api:
    """Returns authorized b2 SDK object

    NOTE:
        `authorize_account` does not throw errors if keypair is invalid

    Args:
        application_key_id (str): b2 application key id (SECRET)
        application_key (str): b2 application key
        realm (str, optional): b2sdk.B2Api.authorize_account optional arg
        account_info (b2sdk.AbstractAccountInfo, optional): https://b2-sdk-python.readthedocs.io/en/master/api/account_info.html#accountinfo

    Returns:
        b2sdk.B2Api: authorized b2 SDK object

    """
    b2_api = b2sdk.B2Api(account_info)
    b2_api.authorize_account(application_key_id, application_key, realm=realm)
    return b2_api
