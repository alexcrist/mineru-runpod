import runpod
from google.cloud import storage

# Upload test PDF to GCS
client = storage.Client()
bucket = client.bucket("runpod-temp-data")
blob = bucket.blob("2021_International_Residential_Code_Chapter_3_Page_8_Images.pdf")
blob.upload_from_filename("2021_International_Residential_Code_Chapter_3_Page_8_Images.pdf")
print("Uploaded test PDF to GCS")

# Run job
runpod.api_key = "your-runpod-api-key"
endpoint = runpod.Endpoint("your-endpoint-id")

job = endpoint.run({
    "input": {
        "object_path": "2021_International_Residential_Code_Chapter_3_Page_8_Images.pdf"
    }
})

print(f"Job ID: {job.job_id}")
print("Waiting for result...")

result = job.output()
print(f"Result: {result}")