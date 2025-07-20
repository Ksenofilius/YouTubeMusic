# YouTubeMusic
### Educational example of yt-dlp tool use case.

---

I made two variants of the same tool - ***automatic** and **manual**. Automatic version reads "songs.csv" file and looks up online for songs listed in the file. Manual does not read any file, instead it prompts you for URL, artist and title.
Script download song itself, but then tries to download album cover, album name, and song lyrics to then embed this information into a single file.

Most common issue is getting a wrong album cover, I might fix it somewhere in the future. Rest of it works really well.
