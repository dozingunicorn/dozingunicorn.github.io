"""
sync-images: CLI tool for managing b2 image gallery for unicorn.github.io

.. moduleauthor:: John Purcell

"""

from datetime import datetime
import os
import pathlib
import sys
import time
import re

import b2sdk.v3 as b2sdk

# from b2sdk.v3 import B2Api, InMemoryAccountInfo
import click
from dotenv import load_dotenv
from loguru import logger
from click_loguru import ClickLoguru

from . import __version__, __pkg_name__
from . import _toolbox

load_dotenv(".b2env")


__logging_path__ = os.environ.get("LOGGING_PATH", f"/tmp/unicorn/{__pkg_name__}/")

click_loguru = ClickLoguru(
    __pkg_name__,
    __version__,
    retention=0,
    log_dir_parent=__logging_path__,
    stderr_log_level="INFO",
    file_log_level="DEBUG",
)

## Common args
common_dryrun = click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    default=False,
    help="dry run mode - do not overwrite b2 data",
)
common_force = click.option(
    "--force", "-f", is_flag=True, default=False, help="force overwrite data"
)
common_bucket = click.option(
    "--bucket", "-b", envvar="B2_BUCKET", help="b2://my-bucket path"
)
common_application_key = click.option(
    "--application-key", envvar="_B2_APPLICATION_KEY", help="b2 application key"
)
common_application_key_id = click.option(
    "--application-key-id",
    envvar="_B2_APPLICATION_KEY_ID",
    help="b2 application key id",
)

common_bucket_path = click.option(
    "--b2-path", "-p", envvar="B2_LATEST_PATH", default="latest", help="b2 bucket path"
)

common_local_path = click.option(
    "--local-path",
    "-s",
    envvar="LOCAL_PATH",
    default=pathlib.Path.cwd() / "_images",
    help="LOCAL path for sync operations",
    type=click.Path(),
)

common_backup_path = click.option(
    "--backup-path",
    envvar="B2_BACKUP_PATH",
    default=f"backup/{datetime.now().isoformat(timespec="minutes")}",
    help="b2 backup path",
)


@click_loguru.logging_options
@click.group()
@click_loguru.stash_subcommand()
@click.version_option(__version__, prog_name=__pkg_name__)
def cli(verbose, quiet, logfile, profile_mem):
    """cli/main wrapper"""
    pass


@click.command(context_settings=dict(show_default=True))
@click_loguru.init_logger()
@common_dryrun
@common_bucket
@common_application_key
@common_application_key_id
@common_bucket_path
@common_local_path
@common_force
def pull(
    dry_run,
    bucket,
    application_key,
    application_key_id,
    b2_path,
    local_path,
    force,
):
    """sync-images pull: pulls all images from `latest` in desired bucket"""
    logger.info("B2: Authorize Account")
    b2_api = _toolbox.authorize_b2(application_key_id, application_key)

    logger.info(f"Checking local path: {local_path}")
    local_path.mkdir(parents=True, exist_ok=True)

    sync_settings = _toolbox.sync_enums(force, _toolbox.is_local_empty(local_path))

    b2_full_path = "/".join(x.rstrip("/") for x in [bucket, b2_path])
    local_path_str = str(local_path.resolve())
    logger.info(f"b2 sync {b2_full_path} {local_path_str}")

    policies_manager = b2sdk.ScanPoliciesManager(exclude_all_symlinks=True)
    sync = b2sdk.Synchronizer(
        max_workers=10,
        policies_manager=policies_manager,
        dry_run=dry_run,
        allow_empty_source=False,
        compare_version_mode=sync_settings.CompareVersionMode,
        newer_file_mode=sync_settings.NewerFileSyncMode,
        keep_days_or_delete=sync_settings.KeepOrDeleteMode,
    )

    with b2sdk.SyncReport(sys.stdout, True) as reporter:
        sync.sync_folders(
            source_folder=b2sdk.parse_folder(b2_full_path, b2_api),
            dest_folder=b2sdk.parse_folder(local_path_str, b2_api),
            reporter=reporter,
            now_millis=int(round(time.time() * 1000)),
        )


@click.command(context_settings=dict(show_default=True))
@click_loguru.init_logger()
@common_dryrun
@common_bucket
@common_application_key
@common_application_key_id
@common_bucket_path
@common_local_path
@common_backup_path
@common_force
def push(
    dry_run,
    bucket,
    application_key,
    application_key_id,
    b2_path,
    local_path,
    backup_path,
    force,
):
    """sync-images push: `b2 copy` images to /latest and /backup/YYYY-MM-DD_HH:MM:SS"""
    logger.info("B2: Authorize Account")
    b2_api = _toolbox.authorize_b2(application_key_id, application_key)

    logger.info("Generating file list for `b2 copy`")
    files_to_push = _toolbox.list_files(local_path)

    b2_bucketInfo = _toolbox.B2Bucket(
        "/".join([bucket, b2_path])
    )  # TODO: b2://{bucket}/{b2_path} needs helper or fix
    b2_bucketInfo_backup = _toolbox.B2Bucket(
        "/".join([bucket.rstrip("/"), backup_path])
    )  # TODO: make backup bucket a full b2:// path
    with click.progressbar(files_to_push, label=f"Pushing files to {bucket}") as bar:
        logger.debug("")
        if dry_run:
            logger.warning("DRY RUN: Skipping b2 copy operations")
        b2_bucket = b2_api.get_bucket_by_name(b2_bucketInfo.bucket_name)
        b2_bucket_backup = b2_api.get_bucket_by_name(b2_bucketInfo_backup.bucket_name)
        for x in bar:
            # TODO: this should be a function
            b2_fileInfo = _toolbox.B2Filepath(
                b2_bucketInfo,
                x,
                local_path,
            )
            logger.debug(f"b2 copy {x.resolve()} {b2_fileInfo}")
            if not dry_run:
                b2_bucket.upload_local_file(
                    b2_fileInfo.local_path, b2_fileInfo.bucket_path
                )

            b2_fileInfo_backup = _toolbox.B2Filepath(
                b2_bucketInfo_backup,
                x,
                local_path,
            )
            logger.debug(f"b2 copy {x.resolve()} {b2_fileInfo_backup}")
            if not dry_run:
                b2_bucket_backup.upload_local_file(
                    b2_fileInfo_backup.local_path, b2_fileInfo_backup.bucket_path
                )


@click.command(context_settings=dict(show_default=True))
@click_loguru.init_logger()
@common_dryrun
@common_force
@common_local_path
@click.option(
    "--thumbsize",
    envvar="THUMBSIZE",
    help="Thumbnail size '\dX\d' pattern",
    # TODO: click callback to validate regex
    default="600x600",
)
@click.option(
    "--thumbquality",
    envvar="THUMBQUALITY",
    help="Thumbnail quality percent",
    default=95,
    type=int,
)
def thumbnail(
    verbose,
    dry_run,
    bucket,
    force,
    local_path,
    thumbsize,
    thumbquality,
):
    """sync-images thumbnail: generate automatic thumbnails of images in local_path"""
    pass


cli.add_command(push)
cli.add_command(pull)
cli.add_command(thumbnail)

if __name__ == "__main__":
    cli()
