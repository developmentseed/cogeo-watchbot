"""create_job: Create cogeo-watchbot json."""

import re
import json
from collections import Counter
from urllib.parse import urlparse

import click
from rasterio.rio import options
from rio_cogeo.profiles import cog_profiles


def sources_callback(ctx, param, value):
    """
    Validate scheme and uniqueness of sources.

    From: https://github.com/mapbox/pxm-manifest-specification/blob/master/manifest.py#L157-L179

    Notes
    -----
    The callback takes a fileobj, but then converts it to a sequence
    of strings.

    Returns
    -------
    list

    """
    sources = list([name.strip() for name in value])

    # Validate scheme.
    schemes = [urlparse(name.strip()).scheme for name in sources]
    invalid_schemes = [
        scheme for scheme in schemes if scheme not in ["s3", "http", "https"]
    ]
    if len(invalid_schemes):
        raise click.BadParameter(
            "Schemes {!r} are not valid and should be on of 's3/http/https'.".format(
                invalid_schemes
            )
        )

    # Identify duplicate sources.
    dupes = [name for (name, count) in Counter(sources).items() if count > 1]
    if len(dupes) > 0:
        raise click.BadParameter(
            "Duplicated sources {!r} cannot be processed.".format(dupes)
        )

    return sources


class MosaicIdParamType(click.ParamType):
    """Mosaic Id type."""

    name = "mosaicid"

    def convert(self, value, param, ctx):
        """Validate mosaic id."""
        try:
            assert re.match(r"^[0-9A-Fa-f]{56}$", value)
            return value

        except (ValueError, AttributeError, AssertionError):
            raise click.ClickException(
                "mosaicid must be a string, and match '^[0-9A-Fa-f]{56}$'."
            )


@click.command()
@click.argument("sources", default="-", type=click.File("r"), callback=sources_callback)
@click.option(
    "--cog-profile",
    "-p",
    "cogeo_profile",
    type=click.Choice(cog_profiles.keys()),
    default="deflate",
    help="CloudOptimized GeoTIFF profile (default: deflate).",
)
@options.creation_options
@click.option(
    "--options",
    "--op",
    "options",
    metavar="NAME=VALUE",
    multiple=True,
    callback=options._cb_key_val,
    help="rio_cogeo.cogeo.cog_translate input options.",
)
@click.option(
    "--mosaicid",
    type=MosaicIdParamType(),
    help="A mosaic id where to happend new data."
)
def cli(sources, cogeo_profile, creation_options, options, mosaicid):
    """
    Create cogeo-watchbot job file.

    Example:
    aws s3 ls s3://spacenet-dataset/spacenet/SN5_roads/test_public/AOI_7_Moscow/PS-RGB/ --recursive | awk '{print " https://spacenet-dataset.s3.amazonaws.com/"$NF}' > list.txt
    cat list.txt | python -m create_job - -p webp --co blockxsize=256 --co blockysize=256 --op overview_level=6 --op overview_resampling=bilinear > test.json

    """
    meta = dict(
        sources=sources,
        profile_name=cogeo_profile,
        profile_options=creation_options,
        options=options,
    )

    if mosaicid:
        meta["mosaicid"] = mosaicid

    click.echo(json.dumps(meta))


if __name__ == "__main__":
    cli()
