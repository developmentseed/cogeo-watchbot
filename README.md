# cogeo-watchbot

Convert file to COGs and create mosaic at scale using AWS Lambda

# What is this

This repo host the code for a serverless architecture enabling creation of Cloud Optimized GeoTIFF and [Mosaic-JSON](https://github.com/developmentseed/mosaicjson-spec) at scale using a [`map-reduce`](https://en.wikipedia.org/wiki/MapReduce) like model.

#### Map-Reduce events

1. Start job (distribute tasks)
2. Run processing task in parallel (e.g COG creation)
3. Run a summary task (e.g. Create mosaic-json)


Note: This work was inspired by the awesome [ecs-watchbot](https://github.com/mapbox/ecs-watchbot).


## Architecture

![](https://user-images.githubusercontent.com/10407788/64704939-18961400-d47d-11e9-9a67-ae6bbbdfa7cd.png)

### Serverless ? 

Not really. To be able to run a `map-reduce` like model we need a fast and reliable database to store the `job` status.
We use AWS ElastiCache Redis this part thus the stack is not fully serverless.


# Deploy

### Requirements
- serverless
- docker
- aws account


1. Install and configure serverless
```bash
# Install and Configure serverless (https://serverless.com/framework/docs/providers/aws/guide/credentials/)
$ npm install serverless -g 
```

2. Create VPC and Redis Database

```bash
$ cd services/redis
$ sls deploy --region us-east-1
```

3. Create Lambda package

```bash
$ make build
```

4. Create Bucket (optional)

We need to create a bucket to store the COGs and mosaic-json. The bucket must be created before the lambda deploy.

```bash
$ aws s3api create-bucket --bucket my-bucket --region us-east-1
```

5. Deploy the Watchbot Serverless stack

```bash
$ sls deploy --stage production --bucket my-bucket --region us-east-1
```


# How To

### Example

1. Get a list of files you want to convert
```$
$ aws s3 ls s3://spacenet-dataset/spacenet/SN5_roads/test_public/AOI_7_Moscow/PS-RGB/ --recursive | awk '{print "https://spacenet-dataset.s3.amazonaws.com/"$NF}' > list_moscow.txt
```
Note: we use `https://spacenet-dataset.s3.amazonaws.com` prefix because we don't want to add IAM role for this bucket

2. Use scripts/create_job.py

```bash
$ pip install rio-cogeo
$ cd scripts/
$ cat ../list_moscow.txt | python -m create_job - \
   -p webp \
   --co blockxsize=256 \
   --co blockysize=256 \
   --op overview_level=6 \
   --op overview_resampling=bilinear > test.json
```

3. Validate JSON (Optional)

```bash
$ jsonschema -i test.json schema.json
```

4. upload to S3 and start processing

```
$ aws s3 cp spacenet_moscow.json s3://my-bucket/jobs/spacenet_moscow.json
```