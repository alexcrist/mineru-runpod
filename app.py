import modal

BUCKET_NAME = "mineru-temp-data"
PARSING_BACKEND = "vlm-vllm"

app = modal.App("mineru")
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
    creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if creds_json:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            f.write(creds_json)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = f.name

    print("Initializing google cloud storage...")
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    id = f"{timestamp}_{str(uuid.uuid4())[:5]}"
    print(f"ID={id}")

    print("Setting up work dir...")
    work_dir = f"/tmp/{id}"
    Path(work_dir).mkdir(parents=True, exist_ok=True)
    input_zip_local = f"{work_dir}/input.zip"
    extracted_dir = f"{work_dir}/extracted"
    output_dir = f"{work_dir}/output"
    zip_local = f"{work_dir}/output.zip"
    Path(extracted_dir).mkdir(parents=True, exist_ok=True)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    try:
        print("Downloading input zip...")
        zip_blob = bucket.blob(input_path)
        zip_blob.download_to_filename(input_zip_local)

        print("Extracting PDFs from zip...")
        with zipfile.ZipFile(input_zip_local, "r") as zf:
            zf.extractall(extracted_dir)

        # Find all PDF files in the extracted directory
        pdf_files = list(Path(extracted_dir).rglob("*.pdf"))
        print(f"Found {len(pdf_files)} PDF(s) to process")
        if not pdf_files:
            raise ValueError("No PDF files found in the input zip")

        # Process each PDF
        for pdf_file in pdf_files:
            pdf_name = pdf_file.stem  # Get filename without extension
            print(f"Processing {pdf_file.name}...")

            # Create a subdirectory for this PDF's output
            pdf_output_dir = f"{output_dir}/{pdf_name}"
            Path(pdf_output_dir).mkdir(parents=True, exist_ok=True)

            print(f"Running MinerU on {pdf_file.name}...")
            subprocess.run(
                [
                    "mineru",
                    "--source",
                    "local",
                    "--backend",
                    PARSING_BACKEND,
                    "-p",
                    str(pdf_file),
                    "-o",
                    pdf_output_dir,
                ],
                check=True,
            )

        print("Zipping output...")
        with zipfile.ZipFile(zip_local, "w") as zf:
            for file in Path(output_dir).rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(output_dir))

        print("Uploading zip...")
        zip_path = f"{id}.zip"
        zip_blob = bucket.blob(zip_path)
        zip_blob.upload_from_filename(zip_local)
        print("Zip uploaded.")

        return {"output_path": zip_path, "processed_pdfs": len(pdf_files)}

    finally:
        print("Cleaning up...")
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        print("Cleaned up.")
