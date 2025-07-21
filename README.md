# yt-dlp-Music
### An educational example demonstrating the use case of the yt-dlp tool.
https://github.com/yt-dlp/yt-dlp

---

I created two variants of the same tool: automatic and manual. The automatic version reads a "songs.csv" file and looks up the songs listed in the file online. The manual version does not read any file; instead, it prompts you to enter the URL, artist, and title.
The script downloads the song itself, then attempts to download the album cover, album name, and song lyrics to embed this information into a single file.

Most common issue is getting a wrong album cover, I might fix it somewhere in the future. Rest of it works well.

---

## Install required packages

```bash
pip install yt-dlp mutagen requests
sudo apt install ffmpeg
```

## Prepare your CSV file
It must have at least two columns with headers: Artist and Title.
Example:
```text
Artist,Title
Coldplay,Yellow
Adele,Hello
```

## How to run the script
**Make sure songs.csv is in the same folder.**

```bash
python yt-dlp-automatic.py
```
or
```bash
python yt-dlp-manual.py
```
