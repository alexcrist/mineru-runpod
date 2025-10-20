# MinerU Serverless

Runs MinerU on Modal (serverless) using Docker

## Getting started

### Google Cloud

Go into google cloud storage

Make a bucket called "mineru-temp-data"

Add lifecycle setting to delete objects after one day

### Docker

Build docker image

```bash
sudo docker build . -t alexcrist/mineru-serverless
```

Log in to docker hub

```bash
docker login
```

Push to docker hub

```bash
docker push alexcrist/mineru-serverless
```

### Modal

Create secret called "googlecloud-secret"

Create env var in secret

```env
GOOGLE_APPLICATION_CREDENTIALS_JSON='{ ... }'
```

Deploy app

```bash
modal deploy app.py --name mineru
```

### Testing

#### Go into test dir

```bash
cd test
```

#### Set up venv

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Install deps

```bash
pip install modal
pip install google-cloud-storage
```

#### Add gcs-key.json file to `test/` dir

Create a Google Cloud service account and put the JSON secret file in the `test/` dir

#### Run test file

```bash
python3 test.py
```
