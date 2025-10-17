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
creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
if creds_json:
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        f.write(creds_json)
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = f.name

# Init google cloud storage
client = storage.Client()
bucket = client.bucket(BUCKET_NAME)

def handler(event):
    # Generate unique ID
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    id = f"{timestamp}_{str(uuid.uuid4())[:5]}"
    print(f"Starting mineru-runpod (ID={id})...")

    # Setup working directory
    work_dir = f'/tmp/{id}'
    Path(work_dir).mkdir(parents=True, exist_ok=True)

    # Define input / output files and directories
    pdf_local = f'{work_dir}/input.pdf'
    output_dir = f'{work_dir}/output'
    zip_local = f'{work_dir}/output.zip'

    try:
        # Download input PDF
        input_path = event['input']['object_path']
        pdf_blob = bucket.blob(input_path)
        pdf_blob.download_to_filename(pdf_local)

        # Parse with MinerU
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        subprocess.run(['mineru', '-p', pdf_local, '-o', output_dir], check=True)

        # Create zip with all parsed files
        with zipfile.ZipFile(zip_local, 'w') as zf:
            for file in Path(output_dir).rglob('*'):
                if file.is_file():
                    zf.write(file, file.relative_to(output_dir))

        # Upload zip
        zip_path = f"{id}.zip"
        zip_blob = bucket.blob(zip_path)
        zip_blob.upload_from_filename(zip_local)

        return {"output_path": zip_path}

    finally:
        # Cleanup
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})