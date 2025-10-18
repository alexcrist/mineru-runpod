import os
import runpod
from google.cloud import storage
from dotenv import load_dotenv
import tempfile

# Load .env file
print("Loading dotenv...")
load_dotenv()

INPUT_FILE = "2021_International_Residential_Code_Chapter_3_Page_8_Images.pdf"
BUCKET = "runpod-temp-data"
ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID")
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")

# Setup GCS credentials from env var
print("Setting up google creds...")
creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
if creds_json:
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        f.write(creds_json)
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = f.name

# Upload test PDF to GCS
print("Uploading PDF to GCS...")
client = storage.Client()
bucket = client.bucket(BUCKET)
blob = bucket.blob(INPUT_FILE)
blob.upload_from_filename(INPUT_FILE)

# Run job
print("Hitting runpod endpoint...")
runpod.api_key = RUNPOD_API_KEY
endpoint = runpod.Endpoint(ENDPOINT_ID)
job = endpoint.run({
    "input": {
        "object_path": INPUT_FILE
    }
})
print(f"Job ID: {job.job_id}")
print("Waiting for result...")

# Handle result (download zip)
result = job.output()
print(f"Result: {result}")
output_path = result['output_path']
zip_blob = bucket.blob(output_path)
zip_blob.download_to_filename(f"output_{output_path}")
print(f"Downloaded: output_{output_path}")