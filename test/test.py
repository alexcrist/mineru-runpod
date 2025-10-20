import os
import tempfile
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

import modal
from google.cloud import storage

# Get the path to the test directory
TEST_DIR = Path(__file__).parent

# List of local PDF files to test
TEST_PDF_FILES = [
    str(TEST_DIR / "2021_International_Residential_Code_Chapter_3_Page_1.pdf"),
    str(TEST_DIR / "2021_International_Residential_Code_Chapter_3_Page_8_Images.pdf"),
]

BUCKET_NAME = "mineru-temp-data"


def setup_gcs_credentials():
    """Setup GCS credentials from environment variable."""
    gcs_key_path = str(TEST_DIR / "gcs-key.json")
    if not os.path.exists(gcs_key_path):
        raise FileNotFoundError(f"GCS credentials file not found: {gcs_key_path}")
    print(f"Using GCS credentials from: {gcs_key_path}")


def create_input_zip(pdf_files: list[str], output_path: str):
    """Create a zip file containing the specified PDF files."""
    print(f"Creating input zip with {len(pdf_files)} PDF(s)...")
    with zipfile.ZipFile(output_path, "w") as zf:
        for pdf_file in pdf_files:
            if not os.path.exists(pdf_file):
                raise FileNotFoundError(f"PDF file not found: {pdf_file}")
            # Add file to zip with just the filename (no directory structure)
            zf.write(pdf_file, arcname=os.path.basename(pdf_file))
    print(f"Created zip file: {output_path}")


def upload_to_gcs(local_path: str, gcs_path: str, bucket_name: str):
    """Upload a file to Google Cloud Storage."""
    print(f"Uploading {local_path} to gs://{bucket_name}/{gcs_path}...")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(gcs_path)
    blob.upload_from_filename(local_path)
    print(f"Uploaded to GCS: {gcs_path}")
    return gcs_path


def download_from_gcs(gcs_path: str, local_path: str, bucket_name: str):
    """Download a file from Google Cloud Storage."""
    print(f"Downloading gs://{bucket_name}/{gcs_path} to {local_path}...")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(gcs_path)
    blob.download_to_filename(local_path)
    print(f"Downloaded to: {local_path}")


def main():
    """Main test function."""
    # Setup GCS credentials
    setup_gcs_credentials()

    # Generate unique ID for this test run
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    test_id = f"test_{timestamp}_{str(uuid.uuid4())[:5]}"
    print(f"Test ID: {test_id}")

    # Create temporary directory for test files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Step 1: Create input zip
        input_zip_path = os.path.join(temp_dir, "input.zip")
        create_input_zip(TEST_PDF_FILES, input_zip_path)

        # Step 2: Upload to GCS
        gcs_input_path = f"{test_id}_input.zip"
        upload_to_gcs(input_zip_path, gcs_input_path, BUCKET_NAME)

        # Step 3: Call Modal endpoint
        print("Calling Modal endpoint...")
        func = modal.Function.from_name("mineru", "process_pdf")
        result = func.remote(gcs_input_path)
        print(f"Modal result: {result}")

        if "output_path" not in result:
            raise ValueError(f"No output_path in result: {result}")

        output_gcs_path = result["output_path"]
        processed_count = result.get("processed_pdfs", 0)
        print(f"Successfully processed {processed_count} PDF(s)")

        # Step 4: Download result from GCS
        output_zip_path = str(TEST_DIR / f"output_{timestamp}.zip")
        download_from_gcs(output_gcs_path, output_zip_path, BUCKET_NAME)

        # Step 5: Extract and inspect the output
        output_extract_dir = os.path.join(temp_dir, "output_extracted")
        os.makedirs(output_extract_dir, exist_ok=True)

        print("Extracting output zip...")
        with zipfile.ZipFile(output_zip_path, "r") as zf:
            zf.extractall(output_extract_dir)
            file_list = zf.namelist()
            print(f"Output contains {len(file_list)} file(s):")
            for file_name in file_list[:10]:  # Show first 10 files
                print(f"  - {file_name}")
            if len(file_list) > 10:
                print(f"  ... and {len(file_list) - 10} more")

        print("\nTest completed successfully!")
        print(f"Output extracted to: {output_extract_dir}")
        print("Note: Temporary files will be cleaned up automatically")


if __name__ == "__main__":
    main()
