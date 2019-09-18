# Playlist Stream
## A tool that allows you to listen to Youtube videos without being on Youtube with the video open. Good for podcasts, ASMR and music.

### Why?

I listen daily at work to ASMR and old music that I can only find on Youtube but I hate to have a browser tab that I can't close and a video running just to listen to the audio.
This tool allows you to create a playlist on Youtube and listen to it without having to load the entire video or using a browser tab.

### Why is it special?

It's not. This is good for me, and for you if you have the same problem. I plan to add some nice features in the future to make it special but for now it's just a "Youtube audio player" that I'm developing to improve my Python skills.
I have some nice ideas about the ASMR part so maybe this tool can become an ASMR app, who knows.

For now the only interesting idea that I have is to make it work with **timestamps**. If a video contains timestamps in the description this tool will let you choose where to skip anytime you want. This can be useful for full albums, ASMR videos, multi topic podcasts, ecc...

### What do I need to do to use it?

1. Install Python requirements:
   `pip install -r requirements.txt`
2. Install VLC media player
  Install the correct version for your (x86 or x64). Get it from [Videolan official site](https://www.videolan.org/)
3. Run it
  `python playlist-stream.py [args]`


### Arguments

>usage: ['--help'] [-h] [-p P] [-s S] [-e E] [-v V]

>optional arguments:  
>  -h, --help  show this help message and exit  
>  -p P        The youtube playlist/video URL  
>  -s S        Starting index (play videos after this number)  
>  -e E        Ending index (play videos before this number)  
>  -v V        Starting volume (from 0 to 200)  


**You can see the full list of supported arguments by calling `python playlist-stream.py --help` or `python playlist-stream.py -h` for short.**

