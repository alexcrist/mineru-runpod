import modal

BUCKET_NAME = "mineru-temp-data"
PARSING_BACKEND = "vlm-transformers"

app = modal.App("mineru")
image = modal.Image.from_dockerfile("./Dockerfile")

DEVICE_MODE = "cuda"
MODEL_SOURCE = "local"


@app.function(
    image=image,
    gpu="T4",
    timeout=600,
    secrets=[modal.Secret.from_name("googlecloud-secret")],
)
def process_pdf(input_path: str):
    import os
    import shutil
    import tempfile
    import uuid
    import zipfile
    from datetime import datetime
    from pathlib import Path

    from google.cloud import storage
    from mineru.cli.common import do_parse, read_fn
    from mineru.utils.model_utils import get_vram

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

    print("Initializing MinerU...")
    os.environ["MINERU_MODEL_SOURCE"] = MODEL_SOURCE
    os.environ["MINERU_DEVICE_MODE"] = DEVICE_MODE
    os.environ["MINERU_VIRTUAL_VRAM_SIZE"] = round(get_vram(DEVICE_MODE))

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

        # Prepare file names and bytes for batch processing
        file_name_list = []
        pdf_bytes_list = []
        lang_list = []

        for pdf_file in pdf_files:
            file_name = pdf_file.stem
            pdf_bytes = read_fn(pdf_file)
            file_name_list.append(file_name)
            pdf_bytes_list.append(pdf_bytes)
            lang_list.append("en")  # Default language

        print(f"Running MinerU on {len(pdf_files)} PDF(s)...")

        # Use do_parse to handle all PDFs at once
        do_parse(
            output_dir=output_dir,
            pdf_file_names=file_name_list,
            pdf_bytes_list=pdf_bytes_list,
            p_lang_list=lang_list,
            backend=PARSING_BACKEND,
            parse_method="auto",
            server_url=None,
            start_page_id=0,
            end_page_id=None,
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
