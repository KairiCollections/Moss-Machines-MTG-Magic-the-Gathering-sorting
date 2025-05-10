import json
import os
import requests
import glob
import time
import threading
import queue
import imagehash
from datetime import datetime, timedelta
from PIL import Image, ImageFile
from tqdm import tqdm

ImageFile.LOAD_TRUNCATED_IMAGES = True

def organize_images_into_subfolders(image_dir):
    """Organize images into subfolders based on first character of filename (0-9,a-f)"""
    print("Organizing images into subfolders...")
    subfolders = [str(i) for i in range(10)] + [chr(i) for i in range(ord('a'), ord('f')+1)]
    for folder in subfolders:
        os.makedirs(os.path.join(image_dir, folder), exist_ok=True)
    moved_count = 0
    for filename in os.listdir(image_dir):
        if filename.endswith('.png'):
            first_char = filename[0].lower()
            if first_char in '0123456789abcdef':
                src = os.path.join(image_dir, filename)
                dst = os.path.join(image_dir, first_char, filename)
                try:
                    os.rename(src, dst)
                    moved_count += 1
                except Exception as e:
                    print(f"Error moving {filename}: {str(e)}")
    print(f"Organized {moved_count} images into subfolders")

def get_original_style_hash(img):
    phash = imagehash.phash(img, hash_size=16)
    hash_str = str(phash)
    if hash_str.startswith('0x'):
        hash_str = hash_str[2:]
    return hash_str.ljust(64, '0')[:64]

def download_png(session, card_id, png_url, image_dir):
    first_char = card_id[0].lower()
    save_dir = os.path.join(image_dir, first_char)
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"{card_id}.png")
    if os.path.exists(save_path) and os.path.getsize(save_path) > 1024:
        return True
    for attempt in range(3):
        try:
            response = session.get(png_url, stream=True, timeout=30)
            response.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            if os.path.exists(save_path) and os.path.getsize(save_path) > 1024:
                return True
            os.remove(save_path)
        except Exception as e:
            if os.path.exists(save_path):
                os.remove(save_path)
        time.sleep(1)
    return False

def download_worker(session, download_queue, image_dir, download_results, progress_bar):
    while True:
        item = download_queue.get()
        if item is None:
            print("Download worker received shutdown signal.")
            download_queue.task_done()
            break
        card_id, card = item
        if card is None:
            download_results[card_id] = False
            progress_bar.update(1)
            download_queue.task_done()
            continue
        png_url = card.get('image_uris', {}).get('png')
        if not png_url:
            download_results[card_id] = False
            progress_bar.update(1)
            download_queue.task_done()
            continue
        success = download_png(session, card_id, png_url, image_dir)
        download_results[card_id] = success
        progress_bar.update(1)
        download_queue.task_done()

def hash_worker(hash_queue, image_dir, hashes_file, results, progress_bar):
    while True:
        card_id = hash_queue.get()
        if card_id is None:
            print("Hash worker received shutdown signal.")
            hash_queue.task_done()
            break
        try:
            first_char = card_id[0].lower()
            png_path = os.path.join(image_dir, first_char, f"{card_id}.png")
            if os.path.exists(png_path) and os.path.getsize(png_path) > 1024:
                with Image.open(png_path) as img:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    r, g, b = img.split()
                    hashes = {
                        'r_phash': get_original_style_hash(r),
                        'g_phash': get_original_style_hash(g),
                        'b_phash': get_original_style_hash(b)
                    }
                    if all(len(h) == 64 and all(c in '0123456789abcdef' for c in h) for h in hashes.values()):
                        results[card_id] = hashes
                    else:
                        print(f"Hash format mismatch for {card_id}")
                        results[card_id] = None
            else:
                results[card_id] = None
        except Exception as e:
            print(f"Error hashing {card_id}: {str(e)}")
            results[card_id] = None
        progress_bar.update(1)
        hash_queue.task_done()

def download_bulk_data(script_dir):
    bulk_data_url = "https://api.scryfall.com/bulk-data"
    try:
        response = requests.get(bulk_data_url, timeout=30)
        response.raise_for_status()
        bulk_data = response.json()
        default_cards = next((item for item in bulk_data['data'] if item['type'] == 'default_cards'), None)
        if not default_cards:
            print("Error: Could not find default cards in bulk data")
            return False
        existing_json_files = glob.glob(os.path.join(script_dir, "default*.json"))
        newest_file_time = None
        if existing_json_files:
            newest_file = max(existing_json_files, key=os.path.getmtime)
            newest_file_time = datetime.fromtimestamp(os.path.getmtime(newest_file))
        bulk_data_time = datetime.strptime(default_cards['updated_at'], "%Y-%m-%dT%H:%M:%S.%f%z")
        bulk_data_time = bulk_data_time.replace(tzinfo=None)
        if newest_file_time:
            time_diff = bulk_data_time - newest_file_time
            if time_diff < timedelta(days=7):
                print(f"Warning: Bulk data is only {time_diff.days} days newer than existing files")
                answer = input("Do you want to proceed with download anyway? (y/n): ").strip().lower()
                if answer != 'y':
                    print("Download cancelled by user")
                    return False
        for json_file in existing_json_files:
            try:
                os.remove(json_file)
                print(f"Deleted old file: {os.path.basename(json_file)}")
            except Exception as e:
                print(f"Error deleting file {json_file}: {str(e)}")
        print(f"Downloading new bulk data (updated at {bulk_data_time})...")
        download_url = default_cards['download_uri']
        file_name = f"default-{bulk_data_time.strftime('%Y%m%d')}.json"
        file_path = os.path.join(script_dir, file_name)
        os.makedirs(script_dir, exist_ok=True)
        with requests.get(download_url, stream=True, timeout=120) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            progress_bar = tqdm(total=total_size, unit='iB', unit_scale=True, desc="Downloading bulk data")
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    progress_bar.update(len(chunk))
                    f.write(chunk)
            progress_bar.close()
        print(f"Download completed. Saved to {file_name}")
        time.sleep(2)
        return True
    except Exception as e:
        print(f"Error downloading bulk data: {str(e)}")
        return False

def main():
    start_time = time.time()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_dir = os.path.join(script_dir, "card_images_png")
    hashes_path = os.path.join(script_dir, "card_hashes.json")
    # Ensure directories exist
    os.makedirs(script_dir, exist_ok=True)
    os.makedirs(image_dir, exist_ok=True)

    # Download bulk data
    if not download_bulk_data(script_dir):
        print("Bulk data download failed or was cancelled. Exiting.")
        return

    # Load existing hashes
    if not os.path.exists(hashes_path):
        with open(hashes_path, 'w') as f:
            json.dump({}, f)
    try:
        with open(hashes_path, 'r') as f:
            existing_hashes = json.load(f)
        print(f"Loaded {len(existing_hashes)} existing hashes")
        sample = next(iter(existing_hashes.values()))
        print(f"Sample hash format: {sample['r_phash'][:16]}... (length: {len(sample['r_phash'])})")
    except Exception as e:
        print(f"Error loading hashes file: {str(e)}")
        return

    # Find missing images
    print("\n=== FINDING MISSING IMAGES ===")
    existing_images = set()
    for first_char in '0123456789abcdef':
        subfolder = os.path.join(image_dir, first_char)
        if os.path.exists(subfolder):
            existing_images.update(
                f.split('.')[0] for f in os.listdir(subfolder)
                if f.endswith('.png')
            )

    cards_to_download = {}
    for json_file in glob.glob(os.path.join(script_dir, "default*.json")):
        with open(json_file, 'r', encoding='utf-8') as f:
            for card in json.load(f):
                if card is None:
                    continue
                card_id = card.get('id')
                if (card_id and 
                    card_id not in existing_images and 
                    card_id not in existing_hashes and
                    not card.get('digital', False)):
                    cards_to_download[card_id] = card

    total_to_download = len(cards_to_download)
    print(f"Found {total_to_download} images needing download (missing both image and hash)")

    if total_to_download > 0:
        print("\n=== DOWNLOADING IMAGES ===")
        download_results = {}
        download_queue = queue.Queue()
        download_progress = tqdm(total=total_to_download, desc="Downloading", unit="card")

        with requests.Session() as session:
            session.headers.update({'User-Agent': 'Mozilla/5.0'})
            download_threads = []
            for _ in range(20):
                t = threading.Thread(
                    target=download_worker,
                    args=(session, download_queue, image_dir, download_results, download_progress)
                )
                t.start()
                download_threads.append(t)

            for card_id, card in cards_to_download.items():
                download_queue.put((card_id, card))
            print("All download tasks enqueued.")

            download_queue.join()
            print("Download queue completed.")
            # Signal threads to finish
            for _ in range(20):
                download_queue.put(None)
            for t in download_threads:
                t.join()
            print("Download threads joined.")

        successful_downloads = sum(1 for r in download_results.values() if r)
        print(f"Successfully downloaded: {successful_downloads}/{total_to_download}")

        organize_images_into_subfolders(image_dir)
    else:
        print("No images need downloading - all files already exist or have hashes")
        successful_downloads = 0

    # Find images needing hashes
    print("\n=== FINDING IMAGES NEEDING HASHES ===")
    all_image_files = set()
    for first_char in '0123456789abcdef':
        subfolder = os.path.join(image_dir, first_char)
        if os.path.exists(subfolder):
            all_image_files.update(
                f.split('.')[0] for f in os.listdir(subfolder)
                if f.endswith('.png')
            )
    cards_needing_hashes = [card_id for card_id in all_image_files if card_id not in existing_hashes]
    total_to_hash = len(cards_needing_hashes)
    print(f"Found {total_to_hash} images needing hashes")

    if total_to_hash > 0:
        print("\n=== PROCESSING HASHES ===")
        hash_results = {}
        hash_queue = queue.Queue()
        hash_progress = tqdm(total=total_to_hash, desc="Hashing", unit="card")

        hash_threads = []
        for _ in range(8):
            t = threading.Thread(
                target=hash_worker,
                args=(hash_queue, image_dir, hashes_path, hash_results, hash_progress)
            )
            t.start()
            hash_threads.append(t)

        for card_id in cards_needing_hashes:
            hash_queue.put(card_id)
        print("Hashing tasks enqueued.")

        hash_queue.join()
        print("Hash queue completed.")
        # Signal threads to finish
        for _ in range(8):
            hash_queue.put(None)

        for t in hash_threads:
            t.join()
        print("Hash worker threads joined.")

        # Save new hashes
        try:
            with open(hashes_path, 'r') as f:
                current_hashes = json.load(f)
            for card_id, hashes in hash_results.items():
                if hashes:
                    current_hashes[card_id] = hashes
            with open(hashes_path, 'w') as f:
                json.dump(current_hashes, f, indent=2)
            print(f"\nAdded {len(hash_results)} new hashes.")
        except Exception as e:
            print(f"Error updating hashes file: {str(e)}")
    else:
        print("No images need hashing - all hashes already exist")
        updated_hashes = 0

    # Final verification
    try:
        with open(hashes_path, 'r') as f:
            final_hashes = json.load(f)
        print(f"\nFinal verification:")
        print(f"Total hashes in file: {len(final_hashes)}")
        new_hashes = {k: v for k, v in final_hashes.items() if k in cards_needing_hashes}
        if new_hashes:
            sample_id, sample_hash = next(iter(new_hashes.items()))
            print(f"Sample new hash for {sample_id}:")
            print(f"r_phash: {sample_hash['r_phash']}")
            print(f"(Length: {len(sample_hash['r_phash'])})")
    except Exception as e:
        print(f"Error during final verification: {str(e)}")

    elapsed_time = time.time() - start_time
    print(f"\n=== RESULTS ===")
    print(f"Total images downloaded: {successful_downloads}")
    print(f"Total hashes added: {len(hash_results) if 'hash_results' in locals() else 0}")
    print(f"Total time: {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    main()