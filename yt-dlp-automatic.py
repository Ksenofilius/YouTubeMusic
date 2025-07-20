import csv
import os
import sys
import yt_dlp
import requests
from mutagen.flac import FLAC, Picture

DOWNLOAD_FOLDER = "/where/to/download" # choose where to download songs
LOG_FILE = "download_failures.log"
SONGS_CSV_FILE = "songs.csv"


os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def fetch_lyrics(artist, title):
    """Fetch lyrics using lyrics.ovh API."""
    try:
        response = requests.get(f"https://api.lyrics.ovh/v1/{artist}/{title}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("lyrics")
    except Exception as e:
        print(f"Warning: Could not fetch lyrics for {artist} - {title}: {e}")
    return None


def fetch_album_cover(artist, album):
    """Fetch album cover from MusicBrainz or iTunes fallback."""
    # MusicBrainz Cover Art Archive attempt
    try:
        query = f'artist:{artist} AND releasegroup:{album}'
        url = f"https://musicbrainz.org/ws/2/release-group/?query={requests.utils.quote(query)}&fmt=json"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if 'release-groups' in data and data['release-groups']:
            mbid = data['release-groups'][0]['id']
            coverart_url = f"https://coverartarchive.org/release-group/{mbid}/front-500"
            cover_resp = requests.get(coverart_url, timeout=10)
            if cover_resp.status_code == 200:
                return cover_resp.content
    except Exception:
        pass

    # Fallback to iTunes Search API
    try:
        itunes_url = f"https://itunes.apple.com/search?term={requests.utils.quote(artist + ' ' + album)}&entity=album&limit=1"
        resp = requests.get(itunes_url, timeout=10)
        rp_json = resp.json()
        if rp_json['resultCount'] > 0:
            artwork_url = rp_json['results'][0].get('artworkUrl100', '').replace('100x100bb.jpg', '600x600bb.jpg')
            image_resp = requests.get(artwork_url, timeout=10)
            if image_resp.status_code == 200:
                return image_resp.content
    except Exception:
        pass

    return None


def embed_metadata(flac_path, artist, title, album, lyrics, cover_image_bytes):
    """Embed artist, title, album, lyrics, and album cover into FLAC file."""
    try:
        audio = FLAC(flac_path)
        audio['artist'] = artist
        audio['title'] = title
        if album:
            audio['album'] = album
        if lyrics:
            audio['lyrics'] = lyrics

        if cover_image_bytes:
            pic = Picture()
            pic.data = cover_image_bytes
            pic.type = 3  # Cover (front)
            pic.mime = "image/jpeg"
            pic.desc = "Cover"
            audio.clear_pictures()
            audio.add_picture(pic)

        audio.save()
    except Exception as e:
        print(f"Warning: Could not embed metadata for {title}: {e}")


def query_musicbrainz_album(artist, title):
    """
    Search MusicBrainz recording database for artist + title
    Return album name if found, else None
    """
    try:
        base_url = "https://musicbrainz.org/ws/2/recording/"
        query = f'recording:"{title}" AND artist:"{artist}"'
        headers = {'User-Agent': 'MusicDownloaderScript/1.0 ( email@example.com )'}
        params = {'query': query, 'fmt': 'json', 'limit': 1}
        response = requests.get(base_url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        results = response.json()
        if 'recordings' in results and len(results['recordings']) > 0:
            recording = results['recordings'][0]
            if 'releases' in recording and len(recording['releases']) > 0:
                # Albums are equivalent to releases
                album = recording['releases'][0].get('title')
                return album
    except Exception as e:
        print(f"Warning: MusicBrainz search failed for {artist} - {title}: {e}")
    return None


def download_song(artist, title):
    """
    Download song with yt-dlp and return (success, flac_path).
    Album info is retrieved from MusicBrainz.
    """
    query = f"ytsearch1:{artist} {title}"

    output_template = os.path.join(
        DOWNLOAD_FOLDER,
        f"{artist} - {title}.%(ext)s"
        .replace('/', '_')
        .replace('\\', '_')
        .replace(':', '_')
    )

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'flac',
            'preferredquality': '0',
        }],
        'extract_flat': False,
        'noplaylist': True,
        'cachedir': False,
    }

    def progress_hook(d):
        if d['status'] == 'downloading':
            elapsed = d.get('elapsed', 0)
            frac = d.get('downloaded_bytes', 0) / max(d.get('total_bytes', 1), 1)
            percent = frac * 100
            sys.stdout.write(f"\rDownloading {title} - {int(percent)}% {int(elapsed)}s")
            sys.stdout.flush()
        elif d['status'] == 'finished':
            print(f"\rFinished downloading {title}.                            ")

    ydl_opts['progress_hooks'] = [progress_hook]

    flac_path = None

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(query, download=True)
            # Construct expected filename after conversion
            flac_path_candidate = output_template.rsplit('.', 1)[0] + '.flac'
            if os.path.isfile(flac_path_candidate):
                flac_path = flac_path_candidate
    except Exception as e:
        print(f"\nError downloading {artist} - {title}: {e}")
        return False, None

    return True, flac_path


def main():
    failures = []

    with open(SONGS_CSV_FILE, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        if 'Artist' not in reader.fieldnames or 'Title' not in reader.fieldnames:
            print("CSV file must contain 'Artist' and 'Title' columns.")
            return

        for row in reader:
            artist = row['Artist'].strip()
            title = row['Title'].strip()
            if not artist or not title:
                print(f"Skipping invalid row: {row}")
                continue

            print(f"Starting download for: {artist} - {title}")

            success, flac_path = download_song(artist, title)
            if not success or flac_path is None:
                failures.append(f"{artist} - {title}")
                continue

            # Fetch lyrics from lyrics.ovh
            lyrics = fetch_lyrics(artist, title)

            # Get album name from MusicBrainz to ensure album metadata is included
            album = query_musicbrainz_album(artist, title)

            # Fetch album cover using the album name
            cover_image = fetch_album_cover(artist, album) if album else None

            # Embed metadata into FLAC file
            print(f"Embedding metadata for: {artist} - {title}")
            embed_metadata(flac_path, artist, title, album, lyrics, cover_image)

    # Write failures log if any
    if failures:
        with open(LOG_FILE, 'w', encoding='utf-8') as logf:
            for failed in failures:
                logf.write(failed + "\n")
        print(f"Download completed with some failures. See {LOG_FILE} for details.")
    else:
        print("All songs downloaded successfully.")


if __name__ == "__main__":
    main()
