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
import io
from PIL import Image


# ──────── Configuration ─────────
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']
CLIENT_SECRET_FILE = 'credentials/client_secret.json'

# Run local server flow to get user credentials
flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
creds = flow.run_local_server(port=0)
ALBUM_ID        = 'ALBUM ID HERE'
TOKEN           = creds.token   # from your OAuth flow
SLIDESHOW_DIR = '/media/pi/New Volume/downloaded_photos'
DOWNLOAD_DIR    = SLIDESHOW_DIR

PAGE_SIZE       = 100           # up to 100 per page

LAST_SYNC_FILE = 'last_sync_date.txt'

DISPLAY_TIME_MS = 15000  # Time to show each photo (in milliseconds)

SCREEN_WIDTH, SCREEN_HEIGHT = 800, 480#1920, 1080  # adjust to your monitor
# ──────── Configuration ─────────

# ──────── Helpers ──────────────
HEADERS = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type':  'application/json',
}
# ──────── Helpers ─────────

def fetch_album_items(album_id):
    """Yield all mediaItems in the given album, one page at a time."""
    url = 'https://photoslibrary.googleapis.com/v1/mediaItems:search'
    body = {'albumId': album_id, 'pageSize': PAGE_SIZE}
    photos = []
    while True:
        resp = requests.post(url, headers=HEADERS, json=body)
        resp.raise_for_status()
        data = resp.json()
        photos.extend(data.get('mediaItems', []))
        token = data.get('nextPageToken')
        if not token:
            break
        body['pageToken'] = token
    
    return photos

def download_and_convert(item):
    mime_type = item['mimeType']
    filename = item['filename']
    base_name, ext = os.path.splitext(filename)
    local_path = os.path.join(DOWNLOAD_DIR, base_name + '.jpg')
    if os.path.exists(local_path):
        return  # already downloaded

    url = item['baseUrl'] + '=d'
    print(f"Downloading {filename}...")
    res = requests.get(url)
    if res.status_code != 200:
        print(f"Error downloading {filename}: {res.status_code}")
        return

    if mime_type == 'image/heic' or ext == 'heic':
        heic_path = os.path.join(DOWNLOAD_DIR, base_name + '.heic')
        with open(heic_path, 'wb') as f:
            f.write(res.content)
        print(f"Converting {filename} to JPG...")
        os.system(f'convert "{heic_path}" -quality 85 "{local_path}"')
        os.remove(heic_path)
    else:
        with open(local_path, 'wb') as f:
            f.write(res.content)

    print(f"Downloaded {filename}")

def sync_album():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    for media_item in fetch_album_items(ALBUM_ID):
        download_and_convert(media_item)
    update_last_sync()

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

def load_image_any(filepath, screen_size):
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.heic':
        heif_file = pyheif.read(filepath)
        pil_img = Image.frombytes(
            heif_file.mode, heif_file.size, heif_file.data,
            "raw", heif_file.mode, heif_file.stride
        )
    else:
        pil_img = Image.open(filepath)

    # Convert mode if needed
    if pil_img.mode != 'RGB':
        pil_img = pil_img.convert('RGB')

    # Resize to fit screen early (memory saving)
    pil_img.thumbnail(screen_size, Image.LANCZOS)

    data = pil_img.tobytes()
    surface = pygame.image.fromstring(data, pil_img.size, pil_img.mode)
    return surface

def display_slideshow():
    """Display the downloaded photos in a daily-random fullscreen slideshow."""
    # Find all image files
    supported_exts = ('.jpg', '.jpeg', '.png', '.heic')
    image_files = [
        os.path.join(SLIDESHOW_DIR, f)
        for f in os.listdir(SLIDESHOW_DIR)
        if f.lower().endswith(supported_exts)
    ]
    if not image_files:
        print("No photos found to display. Please run sync first.")
        return

    # Daily-deterministic shuffle
    today_seed = date.today().isoformat()
    random.seed(today_seed)
    random.shuffle(image_files)

    # Initialize Pygame
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
    clock = pygame.time.Clock()
    pygame.mouse.set_visible(False)
    screen_rect = screen.get_rect()

    while True:
        # Show each photo
        for img_path in image_files:
            # exit
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    pygame.quit()
                    return -1

            # Load and show one image
            try:
                img = pygame.image.load(img_path)
            except Exception as e:
                print(f"Failed to load {img_path}: {e}")
                continue
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
                        return -1


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
        if display_slideshow() == -1:
            break

        # sleep code
