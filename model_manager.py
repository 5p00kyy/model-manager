#!/usr/bin/env python3
import logging
import multiprocessing
import os
import re
import shutil
import sys
import time
from typing import List, Tuple

from huggingface_hub import HfApi, snapshot_download
import inquirer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

# Constants
MAX_MODELS = 50
GGUF_TAG = "gguf"
MULTIPART_REGEX = r'(.+)-\d{1,5}-of-\d{1,5}\.gguf$'
CACHE_FILE = "models/model_md5_hashes.json"

# Enable faster downloads
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

# Setup logging
import logging
logging.basicConfig(filename='model_manager.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

api = HfApi()
console = Console()



def download_model(repo_id: str, selected_files: List[str], is_update: bool = False) -> None:
    """
    Download selected GGUF files for a model.
    For redownloads, fetches remote GGUF files and deletes locals to force fresh download.
    """
    local_dir = f"models/{repo_id}"

    if is_update:
        # Fetch current remote GGUF files for redownload
        try:
            files = api.list_repo_files(repo_id)
            selected_files = [f for f in files if f.endswith('.gguf')]
        except Exception as e:
            console.print(f"Could not fetch remote files: {e}, using provided files")

        # Delete existing local GGUF files to force redownload
        for f in selected_files:
            local_file = os.path.join(local_dir, f)
            if os.path.exists(local_file):
                os.remove(local_file)

    patterns = [f"*{os.path.basename(f)}" for f in selected_files]



    total_size = 0
    try:
        repo_info = api.model_info(repo_id)
        if repo_info.siblings:
            total_size = sum(
                sibling.size for sibling in repo_info.siblings
                if sibling.size and sibling.rfilename in selected_files
            )
        if total_size > 0:
            console.print(f"Total size: {total_size / 1e9:.2f} GB")
        else:
            console.print("Size: Unknown")
    except Exception as e:
        console.print(f"Could not fetch size info: {e}")
        logging.error(f"Size fetch failed for {repo_id}: {e}")

    # Check disk space
    if total_size > 0:
        try:
            usage = shutil.disk_usage(local_dir[0])
            if usage.free < total_size * 1.1:  # 10% buffer
                console.print(f"Warning: Low disk space ({usage.free / 1e9:.2f} GB free)")
        except Exception as e:
            logging.warning(f"Disk space check failed: {e}")

    action = "Redownloading" if is_update else "Downloading"
    console.print(f"{action} to {local_dir}...")
    logging.info(f"Starting {action.lower()} for {repo_id}: {selected_files}")
    start_time = time.time()
    try:
        snapshot_download(repo_id=repo_id, local_dir=local_dir, allow_patterns=patterns)
        elapsed = time.time() - start_time





        console.print(f"{action} complete in {elapsed:.2f} seconds.")
        logging.info(f"{action} complete for {repo_id} in {elapsed:.2f}s")
    except Exception as e:
        console.print(f"{action} failed: {e}")
        logging.error(f"{action} failed for {repo_id}: {e}")

def search_and_download() -> None:
    while True:  # outer loop for re-search
        while True:
            query = inquirer.text(message="Enter search keywords for GGUF models (e.g., 'Llama', 'GPT')")
            if query and query.strip():
                query = query.strip()
                break
            console.print("Query cannot be empty. Please try again.")

        try:
            with console.status("[bold green]Searching for models...[/bold green]"):
                models = list(api.list_models(search=query, filter="gguf", limit=MAX_MODELS, sort="downloads", direction=-1))
            if not models:
                console.print(f"No models found for '{query}'. Try different keywords or check your connection.")
                continue  # back to query
        except Exception as e:
            console.print(f"Search failed: {e}")
            logging.error(f"Search failed for '{query}': {e}")
            continue

        table = Table(title="Search Results")
        table.add_column("Index", style="cyan")
        table.add_column("Model Name")
        table.add_column("Author")
        table.add_column("Downloads")
        for i, model in enumerate(models):
            author = model.author or model.id.split('/')[0]
            table.add_row(str(i+1), model.id, author, str(model.downloads or 0))
        console.print(table)

        if len(models) < 10:
            console.print(f"Only {len(models)} models found. Try broader keywords for more results.")

        selected_model = None
        while True:  # inner loop for action and fetch
            action = inquirer.text(message="Enter model index to select, 'r' to research with new query, or 'q' to quit")
            if action.lower() == 'q':
                return
            elif action.lower() == 'r':
                break  # to outer for research
            else:
                try:
                    idx = int(action) - 1
                    if 0 <= idx < len(models):
                        selected_model = models[idx]
                        # Validate repo exists
                        try:
                            api.model_info(selected_model.id)
                        except Exception as e:
                            print(f"Error: Model repo not found or inaccessible: {e}")
                            continue  # back to action
                        # Fetch files
                        try:
                            with console.status("[bold green]Fetching model files...[/bold green]"):
                                files = api.list_repo_files(selected_model.id)
                            print(f"DEBUG: Fetched {len(files)} files from repo.")
                            if files:
                                print(f"DEBUG: First 5 files: {files[:5]}")
                            gguf_files = [f for f in files if f.lower().endswith('.gguf')]
                            print(f"DEBUG: Found {len(gguf_files)} GGUF files.")
                            if not gguf_files:
                                print("No GGUF files found in this repo. Try another model.")
                                continue  # back to action

                            quant_groups = {}
                            for f in gguf_files:
                                match = re.match(MULTIPART_REGEX, f)
                                if match:
                                    base = match.group(1)
                                    if base not in quant_groups:
                                        quant_groups[base] = []
                                    quant_groups[base].append(f)
                                else:
                                    quant_groups[f] = [f]

                            quant_list = sorted(quant_groups.keys())
                            if not quant_list:
                                print("No quants available.")
                                continue  # back to action

                            table = Table(title="Available Quants")
                            table.add_column("Index", style="cyan")
                            table.add_column("Quant Name")
                            table.add_column("Files")
                            for i, base in enumerate(quant_list):
                                files = quant_groups[base]
                                num_files = len(files)
                                table.add_row(str(i+1), base, str(num_files))
                            console.print(table)

                            while True:
                                try:
                                    quant_action = inquirer.text(message="Enter quant index to download, or 'q' to quit")
                                    if quant_action.lower() == 'q':
                                        return
                                    idx = int(quant_action) - 1
                                    if 0 <= idx < len(quant_list):
                                        base = quant_list[idx]
                                        selected_files = quant_groups[base]
                                        break
                                    else:
                                        print("Invalid index. Please enter a number from 1 to", len(quant_list))
                                except ValueError:
                                    print("Invalid input. Enter a number or 'q'.")
                                except Exception as e:
                                    print(f"Selection failed: {e}. Please try again.")

                            # Success, proceed to download
                            logging.info(f"Selected quant for {selected_model.id}: {selected_files}")
                            download_model(selected_model.id, selected_files)
                            return  # exit function after download

                        except Exception as e:
                            print(f"Error fetching files: {e}")
                            logging.error(f"File fetch failed for {selected_model.id}: {e}")
                            continue  # back to action
                        # Success, proceed
                        break  # exit inner loop
                    else:
                        print("Invalid index. Please enter a number from 1 to", len(models))
                except ValueError:
                    print("Invalid input. Enter a number, 'r', or 'q'.")

        if action.lower() == 'r':
            continue  # back to query

        if selected_model is None:
            print("No model selected.")
            continue

questions = [
    inquirer.List('choice',
                  message="Select an option",
                  choices=['Search and Download GGUF Models', 'Models', 'Exit'],
                  ),
]

def main() -> None:
    """
    Main entry point for the model manager.
    """
    try:
        while True:
            answers = inquirer.prompt(questions)
            if answers is None:
                break
            choice = answers['choice']
            if choice == 'Exit':
                break
            elif choice == 'Search and Download GGUF Models':
                search_and_download()
            elif choice == 'Models':
                list_downloaded_models()
    except KeyboardInterrupt:
        console.print("\nExiting...")
        logging.info("User exited via Ctrl+C")
        sys.exit(0)
    except Exception as e:
        console.print(f"Unexpected error: {e}")
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)

def list_downloaded_models() -> None:
    """
    List downloaded GGUF models and allow redownloading them.
    """
    console.print("Listing models...")
    if not os.path.exists('models'):
        console.print("models/ directory not found.")
        return

    # Collect all models
    all_models = []
    for author in os.listdir('models'):
        author_path = os.path.join('models', author)
        if os.path.isdir(author_path):
            for model in os.listdir(author_path):
                model_path = os.path.join(author_path, model)
                if os.path.isdir(model_path):
                    repo_id = f"{author}/{model}"
                    local_ggufs = sorted([f for f in os.listdir(model_path) if f.endswith('.gguf')])
                    if local_ggufs:
                        all_models.append((repo_id, model_path, local_ggufs))

    if not all_models:
        console.print("No models found in models/.")
        return

    table = Table(title="Models")
    table.add_column("Index", style="cyan")
    table.add_column("Model")
    table.add_column("GGUF Files")
    for i, (repo_id, _, local_ggufs) in enumerate(all_models):
        table.add_row(str(i+1), repo_id, ', '.join(local_ggufs))
    console.print(table)

    choices = [f"{i+1}. {repo_id}" for i, (repo_id, _, _) in enumerate(all_models)]
    try:
        select = inquirer.checkbox("Select models to redownload (use space to select, enter to confirm)", choices=choices)
        if select:
            for sel in select:
                idx = int(sel.split('.')[0]) - 1
                repo_id, _, local_ggufs = all_models[idx]
                console.print(f"Redownloading {repo_id}...")
                logging.info(f"Redownloading {repo_id}: {local_ggufs}")
                download_model(repo_id, local_ggufs, is_update=True)
    except Exception as e:
        console.print(f"Selection failed: {e}. Models listed above.")

if __name__ == "__main__":
    main()
