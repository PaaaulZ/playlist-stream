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

    AVAILABLE_COMMANDS = "\np: Pause/Unpause\ns: Stop\nn: Next track\n++: Volume +10\n+: Volume +1\n--: Volume -10\n-: Volume -1\nc: Current status\n>: Seek forward 10 seconds\n>>: Seek forward 1 minute\n<: Seek backwards 1 second\n<<: Seek backwards 1 minute\nt: Search for timestamps (official YouTube API)\ntu: Seek to timestamp (posted by uploader in the comments)\ntd: Seek to timestamp (posted by uploader in the video description)\ntc: Seek to timestamp (posted by users in the comments)\ntld: Seek to track (shows tracklist searching in the video description)\ntlc: Seek to track (shows tracklist searching in the comments)\n\nCommand: "
    logger = None

    def __init__(self):

        self.description = "Main class, contains script logic."
        self.author = "PaaaulZ"
        self.logger = logging.getLogger(__name__)
        fh = logging.FileHandler('playlist-streamer.log')
        logging.basicConfig(format='%(asctime)s - [%(levelname)s]: %(message)s', level=logging.DEBUG)
        self.logger.addHandler(fh)
        self.utils = Utils()

    def get_data(self,playlist_id,video_index,logger):

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
            video = result
            logger.info("URL given is a video. Ignoring starting and ending indexes")

        description = self.utils.remove_non_ascii(video['description'])
        title = self.utils.remove_non_ascii(video['title'])
        uploader = self.utils.remove_non_ascii(video['uploader'])
        duration = self.utils.convert_time(video['duration'])
        video_id = video['id']

        chapters = []
        if video['chapters'] is not None:

            # Check if the video has embedded timestamps (chapters)

            for chapter in video['chapters']:
                chapters.append(Timestamp(chapter['start_time'],chapter['title']))

        for video_format in video['formats']:
            if video_format['format_id'] == '140':
                # 140 is the m4a audio format.
                url = video_format['url']
                audio_data = AudioData(title,uploader,description,duration,url,video_id,chapters)
                return audio_data

        return None

class AudioData:

    def __init__(self,title,uploader,description,duration,url,video_id,chapters):

        self.title = title
        self.uploader = uploader
        self.description = description
        self.duration = duration
        self.url = url
        self.video_id = video_id
        self.chapters = chapters
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

    def search_for_timestamps_comments(self,video_id,video_uploader,by_uploader=True,is_tracklist = False):

        """Searches for timestamps in the comments. If by_uploader = True accepts only timestamps posted by the video uploader"""

        if is_tracklist:
            DESCRIPTION_INDEX = 0
            TIME_INDEX = 1
        else:
            TIME_INDEX = 0
            DESCRIPTION_INDEX = 1

        timestamps = []
        comments_downloader = YoutubeCommentsDownloader.Downloader()
        comments = comments_downloader.get_comments(video_id)

        for comment_string in comments:
            comment = json.loads(comment_string)
            author = comment['author']
            text = comment['text']

            # If author is video_uploader timestamps are trusted.

            # Finds timestamp with the following formats 
            # hh:mm:ss description 
            # or
            # (mm:ss description)

            if is_tracklist:
                maybe_timestamps = re.findall(r'(.+?)((?:(?:\d+:)?\d+)?:\d+)\n?',text)
            else:
                maybe_timestamps = re.findall(r'((?:(?:\d+:)?\d+)?:\d+)\s?(.+)\n?',text)

            if len(maybe_timestamps) > 2:
                # Found timestamps (more than 2 just to be sure they are timestamps)
                # Are they trusted? Do I care?
                if by_uploader:
                    # We only want timestamps from vide_uploader
                    if author == video_uploader:
                        for maybe_timestamp in maybe_timestamps:
                            timestamps.append(Timestamp(maybe_timestamp[TIME_INDEX],maybe_timestamp[DESCRIPTION_INDEX]))
                else:
                    # We only want timestamps from other users
                    if author != video_uploader:
                        print(f"{author} --- {by_uploader}")
                        for maybe_timestamp in maybe_timestamps:
                                timestamps.append(Timestamp(maybe_timestamp[TIME_INDEX],maybe_timestamp[DESCRIPTION_INDEX]))

        return timestamps

    def search_for_timestamps_description(self,video_description,is_tracklist = False):

        """Searches for timestamps in the video description."""

        if is_tracklist:
            DESCRIPTION_INDEX = 0
            TIME_INDEX = 1
        else:
            TIME_INDEX = 0
            DESCRIPTION_INDEX = 1

        # Finds timestamp with the following formats 
        # hh:mm:ss description 
        # or
        # (mm:ss description)

        timestamps = []

        if is_tracklist:
            maybe_timestamps = re.findall(r'(.+?)((?:(?:\d+:)?\d+)?:\d+)\n?',video_description)
        else:
            maybe_timestamps = re.findall(r'((?:(?:\d+:)?\d+)?:\d+)\s?(.+)\n?',video_description)

        if len(maybe_timestamps) > 2:
            # Found timestamps (more than 2 just to be sure they are timestamps)

            for maybe_timestamp in maybe_timestamps:
                timestamps.append(Timestamp(maybe_timestamp[TIME_INDEX],maybe_timestamp[DESCRIPTION_INDEX]))


        return timestamps


    def get_milliseconds_from_hhmmss(self,time_str):

        split_time =  time_str.split(':')

        if len(split_time) == 3:
            h, m, s = time_str.split(':')
        else:
            # Come on, it can only be hh:mm:ss or mm:ss.
            h = 0
            m, s = time_str.split(':')

        return (int(h) * 3600 + int(m) * 60 + int(s))*1000

    def parse_timestamp_selection(self,timestamps,timestamp_selection,logger):

        # Return the correct TimeStamp object from the TimeStamp array or None if invalid (also print error)

        if timestamp_selection == 0:
            return None
        else:
            if timestamp_selection <= len(timestamps):
                return timestamps[timestamp_selection-1]
            else:
                logger.error("Invalid timestamp id.")
                return None



def main(argv):

    parser = argparse.ArgumentParser(argv)
    parser.add_argument("-p", help="The youtube playlist/video URL", type=str)
    parser.add_argument("-s", help="Starting index (play videos after this number)", type=int)
    parser.add_argument("-e", help="Ending index (play videos before this number)", type=int)
    parser.add_argument("-v", help="Starting volume (from 0 to 200)", type=int)

    args = parser.parse_args()

    if args.p is None:
        raise Exception("No playlist/video URL specified")

    playlist_id = args.p

    # Initialize objects (utilities and main object)
    ps = PlaylistStream()

    if args.s is None:
        start_index = 1
        ps.logger.info("No starting index specified, starting from the first/only video")
    else:
        start_index = args.s

    if args.e is None:
        ps.logger.info("No ending index specified, stopping after first video")
        end_index = 1
    else:
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


    # Initialize VLC player.
    player = vlc.MediaPlayer() 
    player.audio_set_volume(starting_volume)

    while current_index <= end_index:
        
        try:
            data = ps.get_data(playlist_id,current_index,ps.logger)
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

            if selection.lower() == 'p':
                # Pause/Unpause player
                player.pause()
                ps.logger.info("Toggled pause")
            elif selection.lower() == 's':
                # Stop the player and closes the script
                player.stop()
                ps.logger.info("Player stopped!")
                sys.exit()
            elif selection.lower() == 'n':
                # Next track (stop the player and skip this iteration)
                player.pause()
                break
            elif selection.lower() == 'd':
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
            elif selection.lower() == 'c':
                # Display current status (current track, time)
                # Is it paused/stopped?
                status = 'Playing' if player.is_playing() else 'Paused/Stopped'
                elapsed = ps.utils.convert_time_ms(player.get_time())
                current_volume = player.audio_get_volume()
                print(f"\n{status} {data.title}\n")
                print(f"{elapsed} / {data.duration} [{current_volume}]\n")
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
            elif selection.lower() == 't':

                # Gets chapters from YouTube API (or is it a youtube_dl functionality)?
                # Some videos do not have this parameter so I'll keep the other functions (get from description, comments, comments by uploader)

                timestamps = data.chapters

                if len(timestamps) > 0:
                    print("0) Cancel")
                    for i in range(len(timestamps)):
                        print(f"{i+1}) {ps.utils.convert_time(timestamps[i].time)}: {timestamps[i].description}")
                else:
                    ps.logger.info(f"No timestamps found posted by {data.uploader} in the first 50 comments")
                    continue

                try:
                    timestamp_selection = int(input("Seek to timestamp number: "))
                except ValueError:
                    ps.logger.error("Invalid timestamp id (not a number)")
                    continue

                selected_timestamp = ps.utils.parse_timestamp_selection(timestamps,timestamp_selection,ps.logger)

                if selected_timestamp is not None:
                    ps.logger.info(f"Seeking to {selected_timestamp.description}")
                    # Chapters are in seconds float/double, we don't need decimals and we need milliseconds for VLC set_time function
                    vlc_converted_time = int(selected_timestamp.time) * 1000
                    player.set_time(vlc_converted_time)
                    time.sleep(1)
                else:
                    continue          
            elif selection.lower() == 'tu':
                # Shows timestamps by uploader
                timestamps = ps.utils.search_for_timestamps_comments(data.video_id,data.uploader)

                if len(timestamps) > 0:
                    print("0) Cancel")
                    for i in range(len(timestamps)):
                        print(f"{i+1}) {timestamps[i].time}: {timestamps[i].description}")
                else:
                    ps.logger.info(f"No timestamps found posted by {data.uploader} in the first 50 comments")
                    continue

                try:
                    timestamp_selection = int(input("Seek to timestamp number: "))
                except ValueError:
                    ps.logger.error("Invalid timestamp id (not a number)")
                    continue

                selected_timestamp = ps.utils.parse_timestamp_selection(timestamps,timestamp_selection,ps.logger)

                if selected_timestamp is not None:
                    ps.logger.info(f"Seeking to {selected_timestamp.description}")
                    player.set_time(ps.utils.get_milliseconds_from_hhmmss(selected_timestamp.time))
                    time.sleep(1)
                else:
                    continue                
            elif selection.lower() == 'tc':
                # Shows timestamps by users in the comments
                timestamps = ps.utils.search_for_timestamps_comments(data.video_id,data.uploader,False)

                if len(timestamps) > 0:
                    print("0) Cancel")
                    for i in range(len(timestamps)):
                        print(f"{i+1}) {timestamps[i].time}: {timestamps[i].description}")
                else:
                    ps.logger.info(f"No timestamps posted by users found in the first 50 comments")
                    continue

                try:
                    timestamp_selection = int(input("Seek to timestamp number: "))
                except ValueError:
                    ps.logger.error("Invalid timestamp id (not a number)")
                    continue

                selected_timestamp = ps.utils.parse_timestamp_selection(timestamps,timestamp_selection,ps.logger)

                if selected_timestamp is not None:
                    ps.logger.info(f"Seeking to {selected_timestamp.description}")
                    player.set_time(ps.utils.get_milliseconds_from_hhmmss(selected_timestamp.time))
                    time.sleep(1)
                else:
                    continue    
            elif selection.lower() == 'td':
                # Shows timestamps by users in the comments
                timestamps = ps.utils.search_for_timestamps_description(data.description)

                if len(timestamps) > 0:
                    print("0) Cancel")
                    for i in range(len(timestamps)):
                        print(f"{i+1}) {timestamps[i].time}: {timestamps[i].description}")
                else:
                    ps.logger.info(f"No timestamps found in the video description")
                    continue
                try:
                    timestamp_selection = int(input("Seek to timestamp number: "))
                except ValueError:
                    ps.logger.error("Invalid timestamp id (not a number)")
                    continue

                selected_timestamp = ps.utils.parse_timestamp_selection(timestamps,timestamp_selection,ps.logger)

                if selected_timestamp is not None:
                    ps.logger.info(f"Seeking to {selected_timestamp.description}")
                    player.set_time(ps.utils.get_milliseconds_from_hhmmss(selected_timestamp.time))
                    time.sleep(1)
                else:
                    continue    
            elif selection.lower() == 'tlc':
                # Shows timestamps by users in the comments
                timestamps = ps.utils.search_for_timestamps_comments(data.video_id,data.uploader,False,True)

                if len(timestamps) > 0:
                    print("0) Cancel")
                    for i in range(len(timestamps)):
                        print(f"{i+1}) {timestamps[i].time}: {timestamps[i].description}")
                else:
                    ps.logger.info(f"No timestamps posted by users found in the first 50 comments")
                    continue

                try:
                    timestamp_selection = int(input("Seek to timestamp number: "))
                except ValueError:
                    ps.logger.error("Invalid timestamp id (not a number)")
                    continue

                selected_timestamp = ps.utils.parse_timestamp_selection(timestamps,timestamp_selection,ps.logger)

                if selected_timestamp is not None:
                    ps.logger.info(f"Seeking to {selected_timestamp.description}")
                    player.set_time(ps.utils.get_milliseconds_from_hhmmss(selected_timestamp.time))
                    time.sleep(1)
                else:
                    continue
            elif selection.lower() == 'tld':
                # Shows timestamps by users in the comments
                timestamps = ps.utils.search_for_timestamps_description(data.description,True)

                if len(timestamps) > 0:
                    print("0) Cancel")
                    for i in range(len(timestamps)):
                        print(f"{i+1}) {timestamps[i].time}: {timestamps[i].description}")
                else:
                    ps.logger.info(f"No timestamps found in the video description")
                    continue
                try:
                    timestamp_selection = int(input("Seek to timestamp number: "))
                except ValueError:
                    ps.logger.error("Invalid timestamp id (not a number)")
                    continue

                selected_timestamp = ps.utils.parse_timestamp_selection(timestamps,timestamp_selection,ps.logger)

                if selected_timestamp is not None:
                    ps.logger.info(f"Seeking to {selected_timestamp.description}")
                    player.set_time(ps.utils.get_milliseconds_from_hhmmss(selected_timestamp.time))
                    time.sleep(1)
                else:
                    continue 
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