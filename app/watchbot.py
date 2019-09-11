"""Watchbot Worker."""

from typing import Dict

import os
import json
import logging

from boto3.session import Session as boto3_session

# import numpy
# import rasterio

from watchbot_progress import Part
from watchbot_progress.backends.redis import RedisProgress
from watchbot_progress.main import create_job

from . import translator
from . import version as app_version

from cogeo_mosaic.utils import (
    _aws_get_data,
    _aws_put_data,
    _compress_gz_json,
    create_mosaic,
    get_hash,
)


logger = logging.getLogger("watchbot")
logger.setLevel(logging.INFO)

progress = RedisProgress(
    host=os.environ["REDIS_DB_HOST"],
    port=os.environ["REDIS_DB_PORT"],
    topic_arn=os.environ["SNS_TOPIC"],
)


class LambdaFileIsTooBig(Exception):
    """File is too big for AWS Lambda."""


def _aws_list_objects(bucket, prefix):
    """List object in a bucket."""
    session = boto3_session()
    client = session.client("s3")
    pag = client.get_paginator("list_objects_v2")

    files = []
    for res in pag.paginate(Bucket=bucket, Prefix=prefix):
        if "Contents" in res.keys():
            files.extend(res.get("Contents"))

    return ["s3://{}/{}".format(bucket, r["Key"]) for r in files]


def create_map_message(
    src_path: str, profile_name: Dict, profile_options: Dict = {}, **kwargs: Dict
):
    """Create MAP Message."""
    return {
        "src_path": src_path,
        "profile_name": profile_name,
        "profile_options": profile_options,
        "options": kwargs,
    }


def start(message):
    """Start JOB.

    - Read Job definition
    - Create SQS messages to be sent
        - src_path
        - profile_name
        - profile_options
        - kwargs for rio-cogeo
    - Create Job in Redis db
        - Send Map messages

    """
    if isinstance(message, str):
        message = json.loads(message)

    mosaicid = message.get(
        "mosaicid", get_hash(body=json.dumps(message), version=app_version)
    )
    logger.info(f"Starting work for mosaic: {mosaicid}")

    src_list = message["sources"]
    profile_name = message.get("profile_name", "deflate")
    profile_options = message.get("profile_options", {})
    options = message.get("options", {})
    sqs_messages = [
        create_map_message(src_path, profile_name, profile_options, **options)
        for src_path in src_list
    ]

    number_of_sources = len(sqs_messages)
    logger.info(f"{number_of_sources} parts to proccess")

    jobid = create_job(sqs_messages, progress=progress, metadata={"mosaicid": mosaicid})
    logger.info(f"[START] Jobid: {jobid}")
    return True


def map(message):
    """Map Step: Create COGs."""
    if isinstance(message, str):
        message = json.loads(message)

    jobid = message["jobid"]
    partid = message["partid"]
    mosaicid = message["metadata"]["mosaicid"]

    logger.info(f"[MAP] Processing {jobid} - {partid}")

    with Part(jobid, partid, progress=progress):
        src_path = message["src_path"]
        # with rasterio.open(src_path) as src_dst:
        #     witdh, height, dtype = src_dst.width, src_dst.height, src_dst.dtypes[0]
        #     size = numpy.array([0], dtype=dtype).nbytes * witdh * height
        # logger.info(f"Size of image {size}")

        bname = os.path.splitext(os.path.basename(src_path))[0]
        out_key = os.path.join("cogs", mosaicid, f"{bname}_cog.tif")
        translator.process(
            src_path,
            os.environ["MOSAIC_BUCKET"],
            out_key,
            message["profile_name"],
            message["profile_options"],
            **message["options"],
        )

    return True


def reduce(message):
    """Reduce Step: Create Mosaic."""
    if isinstance(message, str):
        message = json.loads(message)

    mosaicid = message["metadata"]["mosaicid"]
    jobid = message["jobid"]
    logger.info(f"[REDUCE] Starting reduce step for job {jobid}")

    bucket = os.environ["MOSAIC_BUCKET"]
    list_cog = _aws_list_objects(bucket, f"cogs/{mosaicid}")
    mosaic_definition = create_mosaic(list_cog)

    key = f"mosaics/{mosaicid}.json.gz"
    _aws_put_data(key, bucket, _compress_gz_json(mosaic_definition))
    return True


def _parse_message(message):
    record = message["Records"][0]
    if record.get("eventSource", "") == "aws:s3":
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        return "start", json.loads(_aws_get_data(key, bucket))
    else:
        body = json.loads(record["body"])
        return body.get("Subject", "start"), body["Message"]


def main(event, context):
    """
    Handle events.

    Events:
        - S3 (Start or requeue)
        - SQS queue (Start or MAP)
        - SQS queue (REDUCE)

    """
    subject, message = _parse_message(event)

    if subject == "start":
        return start(message)

    elif subject == "map":
        return map(message)

    elif subject == "reduce":
        return reduce(message)

    else:
        raise Exception(f"Invalid subject {subject}")
