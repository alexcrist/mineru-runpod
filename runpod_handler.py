import tempfile
import uuid
import subprocess
import runpod
import zipfile
import os
import shutil
from google.cloud import storage
from pathlib import Path
from datetime import datetime

BUCKET_NAME = "runpod-temp-data"

# Write credentials to temp file from env var
print("Loading credentials...")
creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
if creds_json:
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        f.write(creds_json)
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = f.name

# Init google cloud storage
print("Initializing google cloud storage...")
client = storage.Client()
bucket = client.bucket(BUCKET_NAME)
print("Initialized google cloud storage.")

def handler(event):
    print("Starting handler...")

    # Generate unique ID
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    id = f"{timestamp}_{str(uuid.uuid4())[:5]}"
    print(f"Starting mineru-runpod (ID={id})...")

    # Setup working directory
    print("Setting up workdir...")
    work_dir = f'/tmp/{id}'
    Path(work_dir).mkdir(parents=True, exist_ok=True)

    # Define input / output files and directories
    pdf_local = f'{work_dir}/input.pdf'
    output_dir = f'{work_dir}/output'
    zip_local = f'{work_dir}/output.zip'

    try:
        # Download input PDF
        print("Downloading PDF...")
        input_path = event['input']['object_path']
        pdf_blob = bucket.blob(input_path)
        pdf_blob.download_to_filename(pdf_local)

        # Parse with MinerU
        print("Processing PDF with MinerU...")
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        subprocess.run(['mineru', '--source', 'local', '--backend', 'pipeline', '-p', pdf_local, '-o', output_dir], check=True)

        # Create zip with all parsed files
        print("Creating zip file...")
        with zipfile.ZipFile(zip_local, 'w') as zf:
            for file in Path(output_dir).rglob('*'):
                if file.is_file():
                    zf.write(file, file.relative_to(output_dir))

        # Upload zip
        print("Uploading zipfile...")
        zip_path = f"{id}.zip"
        zip_blob = bucket.blob(zip_path)
        zip_blob.upload_from_filename(zip_local)
        print("Uploaded zipfile.")

        return {"output_path": zip_path}

    finally:
        # Cleanup
        print("Cleaning up...")
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        print("Cleaned up.")

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})