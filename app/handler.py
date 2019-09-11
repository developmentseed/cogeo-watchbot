"""public facing api."""

from typing import Dict, Tuple

import os
import json
import base64

from . import version as app_version
from cogeo_mosaic.utils import get_hash, _aws_put_data

from lambda_proxy.proxy import API

app = API(name="cogeo-watchbot-api", debug=True)


@app.route("/upload", methods=["POST"], cors=True)
@app.pass_event
def upload_job_spec(event: Dict, body: str) -> Tuple[str, str, str]:
    """Send Job definition to process."""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode()

    jobid = get_hash(body=body, version=app_version)
    body = json.loads(body)

    # Check if we are not overwriding a mosaic
    mosaicid = body.get("mosaicid", jobid)

    # TODO
    # Validate schema
    key = f"jobs/{jobid}.json"
    bucket = os.environ["MOSAIC_BUCKET"]
    _aws_put_data(key, bucket, json.dumps(body).encode("utf-8"))
    return ("OK", "text/plain", mosaicid)
