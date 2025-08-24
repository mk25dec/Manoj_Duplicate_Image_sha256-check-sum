# _1streamlit_duplicate_finder_logic.py

import os
import hashlib
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# ... (rest of the file is unchanged, only find_duplicate_files is modified) ...
CHUNK_SIZE_SMALL = 4096
CHUNK_SIZE_LARGE = 65536

def get_small_hash(path):
    # ... (unchanged)
    try:
        with open(path, 'rb') as f:
            chunk = f.read(CHUNK_SIZE_SMALL)
            return hashlib.sha256(chunk).hexdigest()
    except (IOError, OSError):
        return None

def get_full_hash(path):
    # ... (unchanged)
    hasher = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            while chunk := f.read(CHUNK_SIZE_LARGE):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (IOError, OSError):
        return None

def find_duplicate_files(folder_paths: list[str], exclude_paths: list[str] = None) -> dict:
    """
    Finds duplicate files in the given folders, respecting an exclusion list.
    NOW RETURNS: {hash: {'paths': [path1, path2], 'size': file_size_in_bytes}}
    """
    if exclude_paths is None:
        exclude_paths = []

    normalized_scan_paths = {os.path.abspath(os.path.normpath(p)) for p in folder_paths}
    valid_exclude_paths = [p for p in exclude_paths if os.path.abspath(os.path.normpath(p)) not in normalized_scan_paths]
    normalized_exclude_paths = [os.path.abspath(os.path.normpath(p)) for p in valid_exclude_paths]

    unique_roots_to_scan = []
    last_root = None
    for path in sorted(list(normalized_scan_paths)):
        if last_root is None or not path.startswith(last_root + os.sep):
            unique_roots_to_scan.append(path)
            last_root = path

    files_by_size = defaultdict(list)
    all_filepaths = []

    print("Stage 0: Discovering and filtering files...")
    for folder_path in unique_roots_to_scan:
        for root, _, filenames in os.walk(folder_path):
            normalized_root = os.path.abspath(os.path.normpath(root))
            if any(normalized_root.startswith(excluded_dir) for excluded_dir in normalized_exclude_paths):
                continue
            for filename in filenames:
                filepath = os.path.join(root, filename)
                if os.path.exists(filepath) and not os.path.islink(filepath):
                    all_filepaths.append(filepath)

    print("Stage 1: Indexing files by size...")
    with ThreadPoolExecutor() as executor:
        future_to_path = {executor.submit(os.path.getsize, path): path for path in all_filepaths}
        for future in as_completed(future_to_path):
            path = future_to_path[future]
            try:
                size = future.result()
                if size > 0:
                    files_by_size[size].append(path)
            except Exception:
                pass

    potential_duplicates_by_size = {size: paths for size, paths in files_by_size.items() if len(paths) > 1}

    files_by_small_hash = defaultdict(list)
    print("Stage 2: Performing partial hash check...")
    paths_to_check_small_hash = [path for paths in potential_duplicates_by_size.values() for path in paths]

    with ThreadPoolExecutor() as executor:
        future_to_path = {executor.submit(get_small_hash, path): path for path in paths_to_check_small_hash}
        for future in as_completed(future_to_path):
            path = future_to_path[future]
            try:
                small_hash = future.result()
                if small_hash: files_by_small_hash[small_hash].append(path)
            except Exception: pass

    potential_duplicates_by_small_hash = {h: paths for h, paths in files_by_small_hash.items() if len(paths) > 1}

    files_by_full_hash = defaultdict(list)
    print("Stage 3: Performing full hash on remaining candidates...")
    paths_to_check_full_hash = [path for paths in potential_duplicates_by_small_hash.values() for path in paths]

    with ThreadPoolExecutor() as executor:
        future_to_path = {executor.submit(get_full_hash, path): path for path in paths_to_check_full_hash}
        for future in as_completed(future_to_path):
            path = future_to_path[future]
            try:
                full_hash = future.result()
                if full_hash: files_by_full_hash[full_hash].append(path)
            except Exception: pass

    final_duplicates_by_hash = {h: paths for h, paths in files_by_full_hash.items() if len(paths) > 1}

    # --- THIS IS THE NEW PART ---
    # Restructure the output to include the file size for each duplicate set.
    # We already have this info from Stage 1, so it's very fast.
    final_duplicates_with_size = {}
    for hash_val, paths in final_duplicates_by_hash.items():
        if paths:
            # All files in the set have the same size, so we can just get it from the first one.
            try:
                size = os.path.getsize(paths[0])
                final_duplicates_with_size[hash_val] = {'paths': paths, 'size': size}
            except OSError:
                continue # Skip if file has been deleted since scan started

    print(f"Scan complete. Found {len(final_duplicates_with_size)} sets of duplicates.")
    return final_duplicates_with_size