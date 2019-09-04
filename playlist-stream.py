import youtube_dl
import argparse
import vlc
import logging.config
import os
import datetime
import time
import sys
import re
import YoutubeCommentsDownloader
import json
from unidecode import unidecode

class PlaylistStream:

    AVAILABLE_COMMANDS = "\np: Pause/Unpause\ns: Stop\nn: Next track\n++: Volume +10\n+: Volume +1\n--: Volume -10\n-: Volume -1\nc: Current status\n>: Seek forward 10 seconds\n>>: Seek forward 1 minute\n<: Seek backwards 1 second\n<<: Seek backwards 1 minute\nt: Search for timestamps\n\nCommand: "
    logger = None

    def __init__(self):

        self.description = "Main class, contains script logic."
        self.author = "PaaaulZ"
        self.logger = logging.getLogger(__name__)
        fh = logging.FileHandler('playlist-streamer.log')
        logging.basicConfig(format='%(asctime)s - [%(levelname)s]: %(message)s', level=logging.DEBUG)
        self.logger.addHandler(fh)
        self.utils = Utils()
        
    def get_data(self,playlist_id,video_index):

        options = {'outtmpl': '%(id)s%(ext)s'}

        if (video_index is not None):
            options['playlistend'] = video_index
            options['playliststart'] = video_index    
    
        downloader = youtube_dl.YoutubeDL(options)

        with downloader:
            result = downloader.extract_info(playlist_id,download=False)

        if 'entries' in result:
            # Can be a playlist or a list of videos
            if len(result['entries']) > 0:
                # Take the first video, we load videos one by one.
                video = result['entries'][0]
            else:
                # Not enough videos?
                raise IndexError("No results found. Starting/Ending index not in video count")
        else:
            # The URL is for a single video, not a playlist.
            raise Exception("The URL given is not a playlist")

        description = self.utils.remove_non_ascii(video['description'])
        title = self.utils.remove_non_ascii(video['title'])
        uploader = self.utils.remove_non_ascii(video['uploader'])
        duration = self.utils.convert_time(video['duration'])
        video_id = result['entries'][0]

        for video_format in video['formats']:
            if video_format['format_id'] == '140':
                # 140 is m4a audio format.
                url = video_format['url']
                audio_data = AudioData(title,uploader,description,duration,url,video_id)
                return audio_data

        return None

class AudioData:

    def __init__(self,title,uploader,description,duration,url,video_id):

        self.title = title
        self.uploader = uploader
        self.description = description
        self.duration = duration
        self.url = url
        self.video_id = video_id
        return

class Timestamp:

    def __init__(self,time,description):
        self.time = time
        self.description = description
        return



class Utils:

    def convert_time(self,seconds):
        return str(datetime.timedelta(seconds=seconds))
    
    def convert_time_ms(self,milliseconds):
        return str(datetime.timedelta(milliseconds=milliseconds))
    
    def clear_screen(self): 
        # Windows clear screen
        if os.name == 'nt': 
            _ = os.system('cls') 
        # Linux/Unix clear screeen
        else: 
            _ = os.system('clear')             
        return

    def remove_non_ascii(self,text):
        return unidecode(str(text))

    def search_for_timestamps(self,video_id):

        timestamps = []
        comments_downloader = YoutubeCommentsDownloader.Downloader()
        comments = comments_downloader.get_comments(video_id)

        print(comments)

        # author, comment = json.loads(comments)

        # maybe_timestamps = re.findall(r'\d{1,2}(:\d{1,2})(:\d{1,2})?\s+\W?.+',comment)

        # for maybe_timestamp in maybe_timestamps:

        #     print(maybe_timestamp)


        # # \d{1,2}(:\d{1,2})(:\d{1,2})?\s+\W?.+

        return timestamps


def main(argv):

    parser = argparse.ArgumentParser(argv)
    parser.add_argument("-p", help="The youtube playlist URL", type=str)
    parser.add_argument("-s", help="Starting index (play videos after this number)", type=int)
    parser.add_argument("-e", help="Ending index (play videos before this number)", type=int)
    parser.add_argument("-v", help="Starting volume (from 0 to 200)", type=int)

    args = parser.parse_args()

    if args.p is None:
        raise Exception("No playlist URL specified")

    playlist_id = args.p

    if args.s is None:
        start_index = 0
    else:
        start_index = args.s

    end_index = args.e
    current_index = start_index

    if end_index is not None:
        if start_index > end_index:
            raise IndexError("Starting index id is greater than ending id")

    if args.v is not None:
        if args.v < 0 or args.v > 200:
            raise ValueError("Volume is too low or too high. Min is 0, Max is 200")
        starting_volume = args.v
    else:
        starting_volume = 100


    # Initialize objects (utilities and main object)
    ps = PlaylistStream()

    # Initialize VLC player.
    player = vlc.MediaPlayer() 
    player.audio_set_volume(starting_volume)

    while current_index <= end_index:
        
        try:
            # TODO: Remove second current_index (end_index) if it works
            data = ps.get_data(playlist_id,current_index)
        except youtube_dl.utils.DownloadError:
            # Can't download infos for this video, most of the times is geoblocked/private.
            ps.logger.warning(f"Skipping index {current_index} because the video is private or unknown error!")
            current_index += 1
            continue

        current_index += 1

        # Start playing
        player.set_mrl(data.url)
        player.play()


        while player.is_playing:

            time.sleep(1)
            ps.utils.clear_screen()
            ps.logger.info("---------")
            ps.logger.info(f"Currently playing {data.title} by {data.uploader} [{data.duration}]")   
            ps.logger.info("---------")
            selection = input(ps.AVAILABLE_COMMANDS)

            if selection in ('p','P'):
                # Pause/Unpause player
                if player.is_playing:
                    player.pause()
                    ps.logger.info("Player paused")
                else:
                    player.pause()
                    ps.logger.info("Player unpaused")
            elif selection in ('s','S'):
                # Stop the player and closes the script
                player.stop()
                ps.logger.info("Player stopped!")
                sys.exit()
            elif selection in ('n','N'):
                # Next track (stop the player and skip this iteration)
                player.pause()
                break
            elif selection in ('d','D'):
                ps.logger.debug(data.description)
            elif selection == '++':
                player.audio_set_volume(player.audio_get_volume() + 10)
                ps.logger.info(f"Volume +10 [{player.audio_get_volume()}]")
            elif selection == '+':
                player.audio_set_volume(player.audio_get_volume() + 1)
                ps.logger.info(f"Volume +1 [{player.audio_get_volume()}]")
            elif selection == '--':
                player.audio_set_volume(player.audio_get_volume() - 10)
                ps.logger.info(f"Volume -10 [{player.audio_get_volume()}]")
            elif selection == '-':
                player.audio_set_volume(player.audio_get_volume() - 1)
                ps.logger.info(f"Volume -1 [{player.audio_get_volume()}]")
            elif selection in ('c','C'):
                # Display current status (current track, time)
                # Is it paused/stopped?
                status = 'Playing' if player.is_playing() else 'Paused/Stopped'
                elapsed = ps.utils.convert_time_ms(player.get_time())
                print(f"\n{status} {data.title}\n")
                print(f"{elapsed} / {data.duration}\n")
                time.sleep(1)
            elif selection == '>':
                # Seek forward 10 seconds
                player.set_time(player.get_time() + 10000)
            elif selection == '>>':
                # Seek forward 1 minute
                player.set_time(player.get_time() + 60000)
            elif selection == '<':
                # Seek backwards 10 seconds
                player.set_time(player.get_time() - 10000)
            elif selection == '<<':
                # Seek backwards 1 minute
                player.set_time(player.get_time() - 60000)
            elif selection == 't':
                # Shows timestamps

                # comments_downloader = YoutubeCommentsDownloader.Downloader()
                # comments = comments_downloader.get_comments('y8F1Poye3BI')
                #  ps.utils.search_for_timestamps(data.video_id)
                # ps.logger.info(comments)

                ps.logger.debug("[WIP]")

                time.sleep(3)
            else:
                ps.logger.info(f"Unknown command {selection}")
            pass

    # If we are out of this loop the playlist is over.
    logging.info("That was the last track. Stopping")
    player.stop()
    sys.exit()
    return

    

if __name__ == "__main__":

    main(sys.argv[1:])