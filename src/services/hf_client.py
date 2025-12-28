"""HuggingFace API client wrapper."""

import logging
import time
from typing import Any, TypeVar

from huggingface_hub import HfApi

from src.exceptions import HuggingFaceError, NetworkError

logger = logging.getLogger(__name__)

# Type variable for cached values
T = TypeVar("T")


class HuggingFaceClient:
    """
    Client for interacting with HuggingFace Hub API.

    Provides methods to search models, retrieve model information, list files,
    and get repository metadata. Includes caching support for API responses.

    Attributes:
        api: HuggingFace API client instance
        _cache: Internal cache for API responses
        _cache_duration: Cache duration in seconds (default: 300)
    """

    def __init__(self, cache_duration: int = 300) -> None:
        """
        Initialize the HuggingFace API client with empty cache.

        Args:
            cache_duration: Cache TTL in seconds (default: 300 = 5 minutes)
        """
        self.api: HfApi = HfApi()
        self._cache: dict[str, tuple[Any, float]] = {}
        self._cache_duration: int = cache_duration

    def _get_cached(self, key: str) -> tuple[bool, Any]:
        """
        Get a cached value if it exists and hasn't expired.

        Args:
            key: Cache key

        Returns:
            Tuple of (hit, value) where hit is True if cache hit, False otherwise
        """
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_duration:
                logger.debug(f"Cache hit for key: {key}")
                return True, value
            else:
                # Expired, remove from cache
                del self._cache[key]
                logger.debug(f"Cache expired for key: {key}")
        return False, None

    def _set_cache(self, key: str, value: Any) -> None:
        """
        Store a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = (value, time.time())
        logger.debug(f"Cached value for key: {key}")

    def clear_cache(self) -> None:
        """Clear all cached values."""
        self._cache.clear()
        logger.info("Cache cleared")

    def get_cache_stats(self) -> dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache size and valid entry count
        """
        now = time.time()
        valid_count = sum(
            1 for _, (_, ts) in self._cache.items() if now - ts < self._cache_duration
        )
        return {"total_entries": len(self._cache), "valid_entries": valid_count}

    def search_models(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """
        Search for GGUF models on HuggingFace Hub.

        Filters results to only include models with GGUF files and sorts by
        download count in descending order. Results are cached for the configured
        cache duration.

        Args:
            query: Search query string to match against model names/descriptions
            limit: Maximum number of results to return (default: 50)

        Returns:
            List of dictionaries containing model metadata including repo_id,
            author, name, downloads, likes, description, and tags.
            Returns empty list on error.

        Raises:
            HuggingFaceError: If the API request fails
        """
        cache_key = f"search:{query}:{limit}"
        hit, cached_result = self._get_cached(cache_key)
        if hit:
            return cached_result

        try:
            models = list(
                self.api.list_models(
                    search=query, filter="gguf", limit=limit, sort="downloads", direction=-1
                )
            )

            result = []
            for model in models:
                model_data = self._extract_model_data(model)
                if model_data:
                    result.append(model_data)

            logger.info(f"Found {len(result)} models for query: {query}")
            self._set_cache(cache_key, result)
            return result

        except OSError as e:
            logger.error(f"Network error searching models: {e}", exc_info=True)
            raise NetworkError(f"Network error during search: {e}") from e
        except Exception as e:
            logger.error(f"Error searching models: {e}", exc_info=True)
            raise HuggingFaceError(f"Failed to search models: {e}") from e

    def get_model_info(self, repo_id: str) -> dict[str, Any] | None:
        """
        Get detailed information about a specific model.

        Results are cached for the configured cache duration.

        Args:
            repo_id: Repository ID (e.g., 'TheBloke/Llama-2-7B-GGUF')

        Returns:
            Dictionary containing model metadata, or None if model not found

        Raises:
            HuggingFaceError: If the API request fails
        """
        cache_key = f"model_info:{repo_id}"
        hit, cached_result = self._get_cached(cache_key)
        if hit:
            return cached_result

        try:
            model = self.api.model_info(repo_id)
            result = self._extract_model_data(model)
            if result:
                self._set_cache(cache_key, result)
            return result
        except OSError as e:
            logger.error(f"Network error fetching model info for {repo_id}: {e}", exc_info=True)
            raise NetworkError(f"Network error fetching model info: {e}") from e
        except Exception as e:
            logger.error(f"Error fetching model info for {repo_id}: {e}", exc_info=True)
            raise HuggingFaceError(f"Failed to get model info: {e}") from e

    def list_gguf_files(self, repo_id: str) -> list[str]:
        """
        List all GGUF files in a repository.

        Filters repository files to only include those with .gguf extension.
        Results are cached for the configured cache duration.

        Args:
            repo_id: Repository ID

        Returns:
            List of GGUF filenames found in the repository.

        Raises:
            HuggingFaceError: If the API request fails
        """
        cache_key = f"gguf_files:{repo_id}"
        hit, cached_result = self._get_cached(cache_key)
        if hit:
            return cached_result

        try:
            files = self.api.list_repo_files(repo_id)
            gguf_files = [f for f in files if f.lower().endswith(".gguf")]
            logger.info(f"Found {len(gguf_files)} GGUF files in {repo_id}")
            self._set_cache(cache_key, gguf_files)
            return gguf_files
        except OSError as e:
            logger.error(f"Network error listing files for {repo_id}: {e}", exc_info=True)
            raise NetworkError(f"Network error listing files: {e}") from e
        except Exception as e:
            logger.error(f"Error listing files for {repo_id}: {e}", exc_info=True)
            raise HuggingFaceError(f"Failed to list files: {e}") from e

    def get_file_sizes(self, repo_id: str) -> dict[str, int]:
        """
        Get sizes for all files in a repository.

        Results are cached for the configured cache duration.

        Args:
            repo_id: Repository ID

        Returns:
            Dictionary mapping filename to size in bytes.

        Note:
            Some files may have size=0 if metadata is not available from HF API.
            This is not necessarily an error condition.

        Raises:
            HuggingFaceError: If the API request fails
        """
        cache_key = f"file_sizes:{repo_id}"
        hit, cached_result = self._get_cached(cache_key)
        if hit:
            return cached_result

        try:
            # Request file metadata explicitly
            model_info = self.api.model_info(repo_id, files_metadata=True)
            sizes: dict[str, int] = {}

            if hasattr(model_info, "siblings") and model_info.siblings:
                logger.debug(f"Processing {len(model_info.siblings)} files for {repo_id}")

                for sibling in model_info.siblings:
                    # More robust attribute checking
                    if not hasattr(sibling, "rfilename"):
                        logger.warning(f"Sibling missing rfilename attribute in {repo_id}")
                        continue

                    filename = sibling.rfilename

                    # Check for size attribute and handle None/missing cases
                    if hasattr(sibling, "size"):
                        if sibling.size is not None and sibling.size > 0:
                            sizes[filename] = int(sibling.size)
                            logger.debug(f"File {filename}: {sibling.size:,} bytes")
                        elif sibling.size == 0:
                            # Size is explicitly 0 - this might be a valid empty file
                            sizes[filename] = 0
                            logger.debug(f"File {filename}: 0 bytes (empty file)")
                        else:
                            # Size is None
                            sizes[filename] = 0
                            logger.warning(f"File {filename}: size is None, defaulting to 0")
                    else:
                        # No size attribute at all
                        sizes[filename] = 0
                        logger.warning(f"File {filename}: no size attribute, defaulting to 0")
            else:
                logger.warning(f"No siblings found for {repo_id}")

            logger.info(f"Fetched sizes for {len(sizes)} files in {repo_id}")
            self._set_cache(cache_key, sizes)
            return sizes

        except OSError as e:
            logger.error(f"Network error getting file sizes for {repo_id}: {e}", exc_info=True)
            raise NetworkError(f"Network error getting file sizes: {e}") from e
        except Exception as e:
            logger.error(f"Error getting file sizes for {repo_id}: {e}", exc_info=True)
            raise HuggingFaceError(f"Failed to get file sizes: {e}") from e

    def get_commit_sha(self, repo_id: str) -> str | None:
        """
        Get the current commit SHA for a repository.

        Note: This method does NOT cache results since commit SHAs are used
        for update checking and need to be fresh.

        Args:
            repo_id: Repository ID

        Returns:
            40-character commit SHA string, or None if error occurs

        Raises:
            HuggingFaceError: If the API request fails
        """
        try:
            model_info = self.api.model_info(repo_id)
            return getattr(model_info, "sha", None)
        except OSError as e:
            logger.error(f"Network error getting commit SHA for {repo_id}: {e}", exc_info=True)
            raise NetworkError(f"Network error getting commit SHA: {e}") from e
        except Exception as e:
            logger.error(f"Error getting commit SHA for {repo_id}: {e}", exc_info=True)
            raise HuggingFaceError(f"Failed to get commit SHA: {e}") from e

    def _extract_model_data(self, hf_model: Any) -> dict[str, Any] | None:
        """
        Extract standardized model data from HuggingFace model object.

        Args:
            hf_model: HuggingFace ModelInfo object

        Returns:
            Dictionary with standardized model fields, or None if extraction fails
        """
        try:
            author = getattr(hf_model, "author", None) or hf_model.id.split("/")[0]
            name = hf_model.id.split("/")[-1]

            # Safely get card data
            description = ""
            if hasattr(hf_model, "cardData") and hf_model.cardData:
                if isinstance(hf_model.cardData, dict):
                    description = hf_model.cardData.get("description", "")

            return {
                "repo_id": hf_model.id,
                "author": author,
                "name": name,
                "downloads": getattr(hf_model, "downloads", 0) or 0,
                "likes": getattr(hf_model, "likes", 0) or 0,
                "last_modified": getattr(hf_model, "lastModified", None),
                "description": description,
                "tags": getattr(hf_model, "tags", []) or [],
            }
        except Exception as e:
            logger.error(f"Error extracting model data: {e}", exc_info=True)
            return None
