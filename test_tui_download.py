#!/usr/bin/env python3
"""
Comprehensive test script for Model Manager TUI download functionality.
Tests the download system without requiring user interaction.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.hf_client import HuggingFaceClient
from src.services.storage import StorageManager
from src.services.downloader import DownloadManager
from src.config import MODELS_DIR, METADATA_FILE
from src.utils.helpers import format_size, format_speed, format_time

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("test_download.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class DownloadTester:
    """Test harness for download functionality."""
    
    def __init__(self):
        self.hf_client = HuggingFaceClient()
        self.storage = StorageManager(MODELS_DIR, METADATA_FILE)
        self.downloader = DownloadManager(self.hf_client, self.storage)
        
        self.progress_updates = []
        self.test_results = {
            "file_size_fetch": False,
            "validation": False,
            "download_start": False,
            "progress_callbacks": 0,
            "download_complete": False,
            "ui_would_update": False
        }
    
    def progress_callback(self, progress_data):
        """Capture progress updates."""
        logger.info(f"PROGRESS UPDATE: {progress_data.get('current_file', 'unknown')}")
        logger.info(f"  Overall: {progress_data.get('overall_downloaded', 0)}/{progress_data.get('overall_total', 0)}")
        logger.info(f"  Speed: {format_speed(progress_data.get('speed', 0))}")
        logger.info(f"  ETA: {format_time(progress_data.get('eta', 0))}")
        
        self.progress_updates.append(progress_data)
        self.test_results["progress_callbacks"] += 1
        
        # Simulate UI update logic
        try:
            overall_pct = (
                progress_data.get("overall_downloaded", 0)
                / max(progress_data.get("overall_total", 1), 1)
                * 100
            )
            logger.debug(f"  UI would show: {overall_pct:.1f}% complete")
            self.test_results["ui_would_update"] = True
        except Exception as e:
            logger.error(f"  UI update simulation failed: {e}")
    
    async def test_file_size_fetching(self, repo_id):
        """Test file size fetching from HuggingFace."""
        logger.info(f"\n{'='*60}")
        logger.info(f"TEST 1: File Size Fetching for {repo_id}")
        logger.info(f"{'='*60}")
        
        try:
            file_sizes = self.hf_client.get_file_sizes(repo_id)
            
            if not file_sizes:
                logger.error("FAIL: No file sizes returned")
                return False
            
            logger.info(f"SUCCESS: Retrieved {len(file_sizes)} file sizes")
            for filename, size in list(file_sizes.items())[:5]:
                logger.info(f"  {filename}: {format_size(size)}")
            
            if all(size == 0 for size in file_sizes.values()):
                logger.warning("WARNING: All file sizes are 0 - API may not have metadata")
                return False
            
            self.test_results["file_size_fetch"] = True
            return True
            
        except Exception as e:
            logger.error(f"FAIL: Exception during file size fetch: {e}", exc_info=True)
            return False
    
    async def test_gguf_file_listing(self, repo_id):
        """Test GGUF file listing."""
        logger.info(f"\n{'='*60}")
        logger.info(f"TEST 2: GGUF File Listing for {repo_id}")
        logger.info(f"{'='*60}")
        
        try:
            gguf_files = self.hf_client.list_gguf_files(repo_id)
            
            if not gguf_files:
                logger.error("FAIL: No GGUF files found")
                return None
            
            logger.info(f"SUCCESS: Found {len(gguf_files)} GGUF files")
            for filename in gguf_files[:5]:
                logger.info(f"  {filename}")
            
            return gguf_files
            
        except Exception as e:
            logger.error(f"FAIL: Exception during GGUF listing: {e}", exc_info=True)
            return None
    
    async def test_download_validation(self, repo_id, files, total_size):
        """Test download validation."""
        logger.info(f"\n{'='*60}")
        logger.info(f"TEST 3: Download Validation")
        logger.info(f"{'='*60}")
        logger.info(f"  Repo: {repo_id}")
        logger.info(f"  Files: {len(files)}")
        logger.info(f"  Total Size: {format_size(total_size)}")
        
        try:
            valid, error_msg = await self.downloader.validate_download(repo_id, files, total_size)
            
            if valid:
                logger.info("SUCCESS: Validation passed")
                self.test_results["validation"] = True
                return True
            else:
                logger.error(f"FAIL: Validation failed: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"FAIL: Exception during validation: {e}", exc_info=True)
            return False
    
    async def test_download(self, repo_id, files):
        """Test actual download process."""
        logger.info(f"\n{'='*60}")
        logger.info(f"TEST 4: Download Process")
        logger.info(f"{'='*60}")
        logger.info(f"  Repo: {repo_id}")
        logger.info(f"  Files to download: {len(files)}")
        
        self.test_results["download_start"] = True
        start_time = time.time()
        
        try:
            success = await self.downloader.download_model(
                repo_id,
                files,
                progress_callback=self.progress_callback
            )
            
            elapsed = time.time() - start_time
            
            if success:
                logger.info(f"SUCCESS: Download completed in {elapsed:.2f}s")
                logger.info(f"  Progress callbacks received: {self.test_results['progress_callbacks']}")
                self.test_results["download_complete"] = True
                return True
            else:
                logger.error("FAIL: Download returned False")
                return False
                
        except Exception as e:
            logger.error(f"FAIL: Exception during download: {e}", exc_info=True)
            return False
    
    def print_summary(self):
        """Print test summary."""
        logger.info(f"\n{'='*60}")
        logger.info("TEST SUMMARY")
        logger.info(f"{'='*60}")
        
        total_tests = len([k for k in self.test_results.keys() if k != "progress_callbacks"])
        passed_tests = sum(1 for k, v in self.test_results.items() 
                          if k != "progress_callbacks" and v is True)
        
        logger.info(f"Tests Passed: {passed_tests}/{total_tests}")
        logger.info(f"\nDetailed Results:")
        for test, result in self.test_results.items():
            if test == "progress_callbacks":
                logger.info(f"  {test}: {result} callbacks received")
            else:
                status = "PASS" if result else "FAIL"
                logger.info(f"  {test}: {status}")
        
        logger.info(f"\nProgress Updates:")
        logger.info(f"  Total callbacks: {len(self.progress_updates)}")
        if self.progress_updates:
            logger.info(f"  First update: {self.progress_updates[0].get('current_file', 'N/A')}")
            logger.info(f"  Last update: {self.progress_updates[-1].get('current_file', 'N/A')}")
            
            if self.progress_updates[-1].get('completed'):
                logger.info(f"  Status: COMPLETED")
        
        return passed_tests == total_tests


async def main():
    """Main test execution."""
    logger.info("="*60)
    logger.info("Model Manager Download System Test Suite")
    logger.info("="*60)
    
    tester = DownloadTester()
    
    # Test with a very small GGUF model - TheBloke's TinyLlama quantized version
    test_repo = "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF"
    
    # Step 1: Test file size fetching
    sizes_ok = await tester.test_file_size_fetching(test_repo)
    if not sizes_ok:
        logger.warning("File size fetching had issues, but continuing...")
    
    # Step 2: List GGUF files
    gguf_files = await tester.test_gguf_file_listing(test_repo)
    if not gguf_files:
        logger.error("CRITICAL: Cannot proceed without GGUF files")
        return False
    
    # Find smallest file for testing (Q2_K is usually smallest)
    file_sizes = tester.hf_client.get_file_sizes(test_repo)
    test_files = [f for f in gguf_files if "Q2_K" in f.upper()][:1]  # Just one file
    
    if not test_files:
        # Fallback to smallest file
        test_files = sorted(gguf_files, key=lambda f: file_sizes.get(f, 0))[:1]
    
    logger.info(f"\nSelected test file: {test_files[0]}")
    total_size = sum(file_sizes.get(f, 0) for f in test_files)
    logger.info(f"Total download size: {format_size(total_size)}")
    
    # Step 3: Test validation
    valid_ok = await tester.test_download_validation(test_repo, test_files, total_size)
    if not valid_ok:
        logger.error("CRITICAL: Validation failed, cannot proceed")
        return False
    
    # Step 4: Test actual download
    logger.info("\nStarting actual download test...")
    logger.info("This may take a few minutes depending on connection speed...")
    
    download_ok = await tester.test_download(test_repo, test_files)
    
    # Print summary
    all_passed = tester.print_summary()
    
    if all_passed:
        logger.info("\n✓ ALL TESTS PASSED")
        return True
    else:
        logger.info("\n✗ SOME TESTS FAILED - Check log for details")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
        sys.exit(2)
    except Exception as e:
        logger.error(f"Test suite crashed: {e}", exc_info=True)
        sys.exit(3)
