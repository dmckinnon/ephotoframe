import os
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
#from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import requests
import json
from datetime import date, timedelta
import pygame
import random
import pillow_heif
from PIL import Image


# ──────── Configuration ─────────
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']
CLIENT_SECRET_FILE = 'credentials/client_secret.json'

# Run local server flow to get user credentials
flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
creds = flow.run_local_server(port=0)
ALBUM_ID        = 'YOUR ALBUM ID HERE'
TOKEN           = creds.token   # from your OAuth flow
DOWNLOAD_DIR    = 'downloaded_photos'
PAGE_SIZE       = 100           # up to 100 per page

LAST_SYNC_FILE = 'last_sync_date.txt'

DISPLAY_TIME_MS = 15000  # Time to show each photo (in milliseconds)
# ──────── Configuration ─────────

# ──────── Helpers ──────────────
HEADERS = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type':  'application/json',
}
# ──────── Configuration ─────────

def fetch_album_items(album_id):
    """Yield all mediaItems in the given album, one page at a time."""
    url = 'https://photoslibrary.googleapis.com/v1/mediaItems:search'
    body = {'albumId': album_id, 'pageSize': PAGE_SIZE}
    while True:
        resp = requests.post(url, headers=HEADERS, json=body)
        resp.raise_for_status()
        data = resp.json()
        for item in data.get('mediaItems', []):
            yield item
        token = data.get('nextPageToken')
        if not token:
            break
        body['pageToken'] = token

def download_item(item, download_dir):
    """Download a single mediaItem to disk."""
    # append =d to get the full-resolution file
    download_url = item['baseUrl'] + '=d'
    filename     = f"{item['id']}_{item['filename']}"
    path         = os.path.join(download_dir, filename)

    # skip if already downloaded
    if os.path.exists(path):
        return

    r = requests.get(download_url, headers={'Authorization': f'Bearer {TOKEN}'})
    r.raise_for_status()
    with open(path, 'wb') as f:
        f.write(r.content)
    print(f"Downloaded {filename}")

def sync_album():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    for media_item in fetch_album_items(ALBUM_ID):
        download_item(media_item, DOWNLOAD_DIR)

def update_last_sync():
    """Record today's date as the last sync date."""
    with open(LAST_SYNC_FILE, 'w') as f:
        f.write(date.today().isoformat())

def should_sync() -> bool:
    """Determine if it's been 7 days since last sync."""
    if not os.path.exists(LAST_SYNC_FILE):
        return True
    with open(LAST_SYNC_FILE, 'r') as f:
        last = date.fromisoformat(f.read().strip())
    return date.today() - last >= timedelta(days=7)

def load_image_any(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.heic':
        # decode HEIC into a Pillow Image
        heif_file = pillow_heif.read_heif(filepath)
        pil_img = Image.frombytes(
            heif_file.mode, heif_file.size, heif_file.data, "raw"
        )
        # convert mode if needed
        if pil_img.mode != 'RGB':
            pil_img = pil_img.convert('RGB')
        # convert to a pygame Surface
        data = pil_img.tobytes()
        surface = pygame.image.fromstring(data, pil_img.size, pil_img.mode)
        return surface
    else:
        # normal formats (PNG, JPG, etc.)
        return pygame.image.load(filepath).convert()

def display_slideshow():
    """Display the downloaded photos in a daily-random fullscreen slideshow."""
    # Load and sort photos list
    photos = [os.path.join(DOWNLOAD_DIR, f)
              for f in os.listdir(DOWNLOAD_DIR)
              if f.lower().endswith(('jpg', 'jpeg', 'png', 'PNG', 'JPG', 'heic', 'HEIC'))]
    if not photos:
        print("No photos found to display. Please run sync first.")
        return

    # Daily-deterministic shuffle
    today_seed = date.today().isoformat()
    random.seed(today_seed)
    random.shuffle(photos)

    # Initialize Pygame
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.mouse.set_visible(False)
    screen_rect = screen.get_rect()

    try:
        # Show each photo
        for photo_path in photos:
            img = load_image_any(photo_path)
            # Original image size
            iw, ih = img.get_size()

            # Screen (window) size
            sw, sh = screen_rect.size

            # Compute scale: fit to screen by the smaller ratio
            scale = min(sw / iw, sh / ih)
            new_w, new_h = int(iw * scale), int(ih * scale)

            # Scale the image
            img = pygame.transform.scale(img, (new_w, new_h))

            # Compute offsets to center on screen
            x = (sw - new_w) // 2
            y = (sh - new_h) // 2

            # Clear screen (black background)
            screen.fill((0, 0, 0))

            # Blit the centered, aspect-correct image
            screen.blit(img, (x, y))
            pygame.display.flip()
            # Wait for DISPLAY_TIME_MS or until ESC pressed
            start = pygame.time.get_ticks()
            while pygame.time.get_ticks() - start < DISPLAY_TIME_MS:
                for event in pygame.event.get():
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        return
    finally:
        pygame.quit()


# ──────── Main ─────────────────
if __name__ == '__main__':

    # todo: wake upon motion
    while True:
        # wake code

        # Sync weekly
        if should_sync():
            print("Syncing album from Google Photos...")
            sync_album()
        else:
            print("Skipping sync, last sync was within the past week.")

        # Display slideshow
        display_slideshow()

        # sleep code
