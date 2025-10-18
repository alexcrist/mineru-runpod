import modal

BUCKET_NAME = "mineru-temp-data"

app = modal.App("mineru-parser")
image = modal.Image.from_dockerfile("./Dockerfile")

@app.function(
    image=image,
    gpu="T4",
    timeout=600,
    secrets=[modal.Secret.from_name("googlecloud-secret")],
)
def process_pdf(input_path: str):
    import uuid
    import subprocess
    import zipfile
    import os
    import shutil
    from google.cloud import storage
    from pathlib import Path
    from datetime import datetime
    import tempfile

    print("Loading credentials...")
    creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if creds_json:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write(creds_json)
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = f.name

    print("Initializing google cloud storage...")
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    id = f"{timestamp}_{str(uuid.uuid4())[:5]}"
    print(f"ID={id}")

    print("Setting up work dir...")
    work_dir = f'/tmp/{id}'
    Path(work_dir).mkdir(parents=True, exist_ok=True)
    pdf_local = f'{work_dir}/input.pdf'
    output_dir = f'{work_dir}/output'
    zip_local = f'{work_dir}/output.zip'
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    try:
        print("Downloading PDF...")
        pdf_blob = bucket.blob(input_path)
        pdf_blob.download_to_filename(pdf_local)

        print("Runing MinerU...")
        subprocess.run(['mineru', '--source', 'local', '--backend', 'pipeline', '-p', pdf_local, '-o', output_dir], check=True)

        print("Zipping output...")
        with zipfile.ZipFile(zip_local, 'w') as zf:
            for file in Path(output_dir).rglob('*'):
                if file.is_file():
                    zf.write(file, file.relative_to(output_dir))

        print("Uploading zip...")
        zip_path = f"{id}.zip"
        zip_blob = bucket.blob(zip_path)
        zip_blob.upload_from_filename(zip_local)
        print("Zip upploaded.")

        return {"output_path": zip_path}

    finally:
        print("Cleaning up...")
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        print("Cleaned up.")

@app.local_entrypoint()
def main():
    input_path = "2021_International_Residential_Code_Chapter_3_Page_8_Images.pdf"
    result = process_pdf.remote(input_path)
    print(result)