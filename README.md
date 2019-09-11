# cogeo-watchbot

Convert file to COGs and create mosaic

# What is this


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


2. Create S3 Bucket, VPC and Redis Database

```bash
$ cd services/redis
$ sls deploy
```

3. Create Lambda package

```bash
$ make build
```

4. Deploy

```bash
$ sls deploy --stage production
```
