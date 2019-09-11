# Example

1. List files
```$
$ aws s3 ls s3://spacenet-dataset/spacenet/SN5_roads/test_public/AOI_7_Moscow/PS-RGB/ --recursive | awk '{print "https://spacenet-dataset.s3.amazonaws.com/"$NF}' > list_moscow.txt
```
Note: we use `https://spacenet-dataset.s3.amazonaws.com` prefix because we don't want to add IAM role for this bucket


2. Create YML definition (Optional)

```yaml
sources:
  - https://spacenet-dataset.s3.amazonaws.com/spacenet/SN5_roads/test_public/AOI_7_Moscow/PS-RGB/SN5_roads_test_public_AOI_7_Moscow_PS-RGB_chip0.tif
  - https://spacenet-dataset.s3.amazonaws.com/spacenet/SN5_roads/test_public/AOI_7_Moscow/PS-RGB/SN5_roads_test_public_AOI_7_Moscow_PS-RGB_chip1.tif
  ...
profile_name: "jpeg"
profile_options:
  blockxsize: 256
  blockysize: 256
options:
  add_mask: "true"
```

3. Convert to JSON

```bash
$ yaml2json spacenet_moscow.yml > spacenet_moscow.json
```

4. upload to S3 and start processing

```
$ aws s3 cp spacenet_moscow.json s3://cogeo-watchbot-us-east-1/jobs/spacenet_moscow.json
```