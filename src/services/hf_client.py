"""HuggingFace API client wrapper."""

import logging
from typing import Any

from huggingface_hub import HfApi

logger = logging.getLogger(__name__)


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

    def __init__(self) -> None:
        """Initialize the HuggingFace API client with empty cache."""
        self.api: HfApi = HfApi()
        self._cache: dict[str, tuple[Any, float]] = {}
        self._cache_duration: int = 300

    def search_models(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """
        Search for GGUF models on HuggingFace Hub.

        Filters results to only include models with GGUF files and sorts by
        download count in descending order.

        Args:
            query: Search query string to match against model names/descriptions
            limit: Maximum number of results to return (default: 50)

        Returns:
            List of dictionaries containing model metadata including repo_id,
            author, name, downloads, likes, description, and tags.
            Returns empty list on error.
        """
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
            return result

        except Exception as e:
            logger.error(f"Error searching models: {e}")
            return []

    def get_model_info(self, repo_id: str) -> dict[str, Any] | None:
        """
        Get detailed information about a specific model.

        Args:
            repo_id: Repository ID (e.g., 'TheBloke/Llama-2-7B-GGUF')

        Returns:
            Dictionary containing model metadata, or None if model not found or error occurs
        """
        try:
            model = self.api.model_info(repo_id)
            return self._extract_model_data(model)
        except Exception as e:
            logger.error(f"Error fetching model info for {repo_id}: {e}")
            return None

    def list_gguf_files(self, repo_id: str) -> list[str]:
        """
        List all GGUF files in a repository.

        Filters repository files to only include those with .gguf extension.

        Args:
            repo_id: Repository ID

        Returns:
            List of GGUF filenames found in the repository.
            Returns empty list on error.
        """
        try:
            files = self.api.list_repo_files(repo_id)
            gguf_files = [f for f in files if f.lower().endswith(".gguf")]
            logger.info(f"Found {len(gguf_files)} GGUF files in {repo_id}")
            return gguf_files
        except Exception as e:
            logger.error(f"Error listing files for {repo_id}: {e}")
            return []

    def get_file_sizes(self, repo_id: str) -> dict[str, int]:
        """
        Get sizes for all files in a repository.

        Args:
            repo_id: Repository ID

        Returns:
            Dictionary mapping filename to size in bytes.
            Returns empty dict on error.
            
        Note:
            Some files may have size=0 if metadata is not available from HF API.
            This is not necessarily an error condition.
        """
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
            return sizes
            
        except Exception as e:
            logger.error(f"Error getting file sizes for {repo_id}: {e}", exc_info=True)
            return {}

    def get_commit_sha(self, repo_id: str) -> str | None:
        """
        Get the current commit SHA for a repository.

        Args:
            repo_id: Repository ID

        Returns:
            40-character commit SHA string, or None if error occurs
        """
        try:
            model_info = self.api.model_info(repo_id)
            return getattr(model_info, "sha", None)
        except Exception as e:
            logger.error(f"Error getting commit SHA for {repo_id}: {e}")
            return None

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
            logger.error(f"Error extracting model data: {e}")
            return None
