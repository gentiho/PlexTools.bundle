PlexTools.bundle
================

A Plex plugin that provides the following:
* Downloads subtitles from http://www.opensubtitles.org/ that work correctly with the Roku client
* Converts nearly any type of video to MP4 which can be Direct Played on all Plex clients

Installation Instructions
-------------------------
1.  Install FFMPEG and FFPROBE from http://www.ffmpeg.org/
2.  Copy PlexTools.bundle to your plugin directory
    * Mac: ~/Library/Application Support/Plex Media Server/Plug-ins
    * Windows: C:\Users\[user]\AppData\Local\Plex Media Server\Plug-ins
3.  Make sure to update the plugins settings
    * `OpenSubtitles Username`: OpenSubtitles account name (required)
    * `OpenSubtitles Password`: Password for OpenSubtitles account (required)
    * `OpenSubtitle Language`: Language preference for subtitles (defaults to English)
    * `FFMPEG_PATH`: Path to FFMPEG (required)
    * `FFPROBE_PATH`: Path to FFProbe (required)
    * `Delete Original File`: Delete original video (defaults to false)

Credits
-------------------------
* https://github.com/mdhiggins/sickbeard_mp4_automator
* https://github.com/agonzalezro/python-opensubtitles
