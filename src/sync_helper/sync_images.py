"""
sync-images: CLI tool for managing b2 image gallery for unicorn.github.io

.. moduleauthor:: John Purcell

"""

import os
import pathlib

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
)

## Common args
common_verbose = click.option(
    "--verbose", "-v", is_flag=True, default=False, help="enable verbose logging"
)
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
    "--application-key", envvar="B2_APPLICATION_KEY", help="b2 application key"
)
common_application_key_id = click.option(
    "--application-key-id", envvar="B2_APPLICATION_KEY_ID", help="b2 application key id"
)

common_bucket_path = click.option(
    "--b2-path", "-p", envvar="B2_LATEST_PATH", default="latest", help="b2 bucket path"
)

common_source_path = click.option(
    "--source-path",
    "-s",
    envvar="LOCAL_SOURCE_PATH",
    default=pathlib.Path.cwd() / "_images",
    help="LOCAL path for sync operations",
    type=click.Path(),
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
@common_verbose
@common_dryrun
@common_bucket
@common_application_key
@common_application_key_id
@common_bucket_path
@common_source_path
@common_force
def pull(
    verbose,
    dry_run,
    bucket,
    application_key,
    application_key_id,
    b2_path,
    source_path,
    force,
):
    """sync-images pull: pulls all images from `latest` in desired bucket"""
    logger.info("B2: Authorize Account")
    b2_api = _toolbox.authorize_b2(application_key_id, application_key)

    logger.info(f"Checking local path: {source_path}")
    source_path.mkdir(parents=True, exist_ok=True)

    sync_settings = _toolbox.sync_enums(force, _toolbox.is_local_empty(source_path))

    # empty = True
    # if any(source_path.iterdir()):
    #     logger.warning("-- Local path is not empty")
    #     empty = False


cli.add_command(pull)


if __name__ == "__main__":
    cli()
