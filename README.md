# MinerU Serverless

Runs MinerU on serverless using Docker

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

### Other

Set env var

```env
GOOGLE_APPLICATION_CREDENTIALS_JSON='{ ... }'
```

## Testing

Go into test/ dir

```bash
cd test
```

Set up venv

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install deps

```bash
pip install -r requirements.txt
```

Fill out .env (see .env.example)

Run test script

```bash
cd test
python3 test.py
```
