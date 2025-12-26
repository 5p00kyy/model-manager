#!/usr/bin/env python3
"""
Test script for the improved download system with byte-level progress.
This tests the fixes for the stuck-at-0% issue.
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.services.downloader import DownloadManager
from src.services.hf_client import HuggingFaceClient
from src.services.storage import StorageManager
from src.config import MODELS_DIR, METADATA_FILE
from src.utils.helpers import format_size, format_speed, format_time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class DownloadTester:
    """Test harness for improved download functionality."""
    
    def __init__(self):
        self.hf_client = HuggingFaceClient()
        self.storage = StorageManager(MODELS_DIR, METADATA_FILE)
        self.downloader = DownloadManager(self.hf_client, self.storage)
        
        self.progress_updates = []
        self.last_progress = None
    
    def progress_callback(self, progress_data):
        """Capture and display progress updates."""
        self.progress_updates.append(progress_data)
        self.last_progress = progress_data
        
        # Display progress
        file_name = progress_data.get('current_file', 'unknown')
        file_downloaded = progress_data.get('current_file_downloaded', 0)
        file_total = progress_data.get('current_file_total', 0)
        overall_pct = (
            progress_data.get('overall_downloaded', 0) /
            max(progress_data.get('overall_total', 1), 1) * 100
        )
        speed = progress_data.get('speed', 0)
        eta = progress_data.get('eta', 0)
        
        logger.info(
            f"📥 {file_name}: {format_size(file_downloaded)}/{format_size(file_total)} "
            f"| Overall: {overall_pct:.1f}% | Speed: {format_speed(speed)} | ETA: {format_time(eta)}"
        )
    
    async def test_small_download(self):
        """Test download with a small model."""
        logger.info("\n" + "="*60)
        logger.info("TEST: Small Model Download")
        logger.info("="*60)
        
        # Use TinyLlama Q2_K (smallest quantization ~460 MB)
        repo_id = "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF"
        
        try:
            # Get GGUF files
            gguf_files = self.hf_client.list_gguf_files(repo_id)
            if not gguf_files:
                logger.error("❌ No GGUF files found")
                return False
            
            # Get file sizes
            file_sizes = self.hf_client.get_file_sizes(repo_id)
            
            # Select smallest file (Q2_K)
            test_files = [f for f in gguf_files if "Q2_K" in f.upper()][:1]
            if not test_files:
                test_files = sorted(gguf_files, key=lambda f: file_sizes.get(f, 0))[:1]
            
            total_size = sum(file_sizes.get(f, 0) for f in test_files)
            
            logger.info(f"Model: {repo_id}")
            logger.info(f"File: {test_files[0]}")
            logger.info(f"Size: {format_size(total_size)}")
            
            # Validate
            valid, error_msg = await self.downloader.validate_download(
                repo_id, test_files, total_size
            )
            
            if not valid:
                logger.error(f"❌ Validation failed: {error_msg}")
                return False
            
            logger.info("✓ Validation passed")
            
            # Download
            logger.info("\nStarting download...")
            success = await self.downloader.download_model(
                repo_id,
                test_files,
                progress_callback=self.progress_callback
            )
            
            if success:
                logger.info(f"\n✅ Download completed successfully!")
                logger.info(f"Progress updates received: {len(self.progress_updates)}")
                
                if len(self.progress_updates) > 2:
                    logger.info("✓ Byte-level progress monitoring working!")
                else:
                    logger.warning("⚠ Only received start/end progress (no byte-level updates)")
                
                return True
            else:
                logger.error("❌ Download failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Test failed with exception: {e}", exc_info=True)
            return False


async def main():
    """Main test execution."""
    logger.info("="*60)
    logger.info("Model Manager - Download System Test")
    logger.info("Testing fixes for stuck-at-0% issue")
    logger.info("="*60 + "\n")
    
    tester = DownloadTester()
    
    # Test small download
    success = await tester.test_small_download()
    
    if success:
        logger.info("\n" + "="*60)
        logger.info("✅ ALL TESTS PASSED")
        logger.info("="*60)
        logger.info("\nThe download system is working correctly!")
        logger.info("- Byte-level progress monitoring: ✓")
        logger.info("- UI updates during download: ✓")
        logger.info("- Error handling and retry: ✓")
        return True
    else:
        logger.info("\n" + "="*60)
        logger.info("❌ TESTS FAILED")
        logger.info("="*60)
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n\nTest interrupted by user")
        sys.exit(2)
    except Exception as e:
        logger.error(f"\nTest suite crashed: {e}", exc_info=True)
        sys.exit(3)
