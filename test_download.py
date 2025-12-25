import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.services.hf_client import HuggingFaceClient
from src.services.storage import StorageManager
from src.services.downloader import DownloadManager
from src.config import MODELS_DIR, METADATA_FILE

async def test():
    hf = HuggingFaceClient()
    storage = StorageManager(MODELS_DIR, METADATA_FILE)
    downloader = DownloadManager(hf, storage)
    
    # Use a tiny file for testing
    repo_id = "TheBloke/Llama-2-7B-Chat-GGUF"
    files = ["config.json"]  # Very small file
    
    def progress_cb(data):
        print(f"PROGRESS: {data['current_file']} - {data.get('overall_downloaded', 0)} / {data.get('overall_total', 0)}")
    
    print("Starting download test...")
    success = await downloader.download_model(repo_id, files, progress_callback=progress_cb)
    print(f"Download result: {success}")

asyncio.run(test())
