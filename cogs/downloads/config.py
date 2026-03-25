import os

DOWNLOADS_FOLDER = "downloads"
MAX_DISCORD_SIZE = 25 * 1024 * 1024

SITES_SUPORTADOS = [
    "tiktok.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "youtu.be",
    "facebook.com",
    "reddit.com",
    "soundcloud.com",
]

MAX_FILESIZE_MB = 25
COOLDOWN_SECONDS = 30

def get_downloads_folder():
    if not os.path.exists(DOWNLOADS_FOLDER):
        os.makedirs(DOWNLOADS_FOLDER)
    return DOWNLOADS_FOLDER
