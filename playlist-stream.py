import youtube_dl
import argparse
import vlc
import logging.config
import os
import datetime

AVAILABLE_COMMANDS = "\np: Pause/Unpause\ns: Stop\nn: Next track\n"
logger = None

def convert_time(seconds):

    return str(datetime.timedelta(seconds=seconds))

def clear_screen(): 
  
    # Windows clear screen
    if os.name == 'nt': 
        _ = os.system('cls') 
    # Linux/Unix clear screeen
    else: 
        _ = os.system('clear') 

    return

def get_video_data(playlist_id,start_index,end_index):

    data = {}

    options = {'outtmpl': '%(id)s%(ext)s'}

    if (start_index is not None):
        options['playlistend'] = end_index
    if (end_index is not None):
        options['playliststart'] = start_index    
   
    downloader = youtube_dl.YoutubeDL(options)

    with downloader:
        result = downloader.extract_info(playlist_id,download=False)

    if 'entries' in result:
        # Can be a playlist or a list of videos
        if len(result['entries']) > 0:
            # Take the first video (end_index - start_index will always be 1 here), we load videos one by one.
            video = result['entries'][0]
        else:
            # Not enough videos?
            raise IndexError("No results found. Starting/Ending index not in video count")
    else:
        # The URL is for a single video, not a playlist.
        raise Exception("The URL given is not a playlist")


    data['description'] = video['description']
    data['title'] = video['title']
    data['uploader'] = video['uploader']
    data['duration'] = convert_time(video['duration'])

    for video_format in video['formats']:
        if video_format['format_id'] == '140':
            # 140 is m4a audio format.
            data['url'] = video_format['url']
            return data

    return None


def main():
    parser = argparse.ArgumentParser("playlist-stream")
    parser.add_argument("-p", help="The youtube playlist URL", type=str)
    parser.add_argument("-s", help="Starting index (play videos after this number)", type=int)
    parser.add_argument("-e", help="Ending index (play videos before this number)", type=int)

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
   
    # Initialize VLC player.
    player = vlc.MediaPlayer()

    while current_index <= end_index:
        
        try:
            #video_data = get_video_data(playlist_id,current_index,end_index)
            # TODO: Remove second current_index (end_index) if it works
            video_data = get_video_data(playlist_id,current_index,current_index)
            audio_url = video_data['url']
            uploader = video_data['uploader']
            title = video_data['title']
            duration = video_data['duration']
            # Description for future use of timestamps
            description = video_data['description']
        except youtube_dl.utils.DownloadError:
            # Can't download infos for this video, most of the times is geoblocked/private.
            logger.warning(f"Skipping index {current_index} because the video is private or unknown error!")
            current_index += 1
            continue

        current_index += 1

        # Start playing
        player.set_mrl(audio_url)
        player.play()


        while player.is_playing:
            clear_screen()
            logger.info("---------")
            logger.info(f"Currently playing {title} by {uploader} [{duration}]")   
            selection = input(AVAILABLE_COMMANDS)
            if selection in ('p','P'):
                # Pause/Unpause player
                if player.is_playing:
                    player.pause()
                    logger.info("Player paused")
                else:
                    player.pause()
                    logger.info("Player unpaused")
            if selection in ('s','S'):
                # Stops the player and closes the script
                player.stop()
                logger.info("Player stopped!")
                exit()
            if selection in ('n','N'):
                # Next track
                player.stop()
                break
            pass

    logging.info("That was the last track. Stopping")
    player.stop()
    return

    

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    fh = logging.FileHandler('playlist-streamer.log')
    logging.basicConfig(format='%(asctime)s - [%(levelname)s]: %(message)s', level=logging.DEBUG)
    logger.addHandler(fh)
    main()