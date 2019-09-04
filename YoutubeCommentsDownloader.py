import time
import json
import requests
from lxml.cssselect import CSSSelector
import lxml.html

class Downloader:

    YOUTUBE_COMMENTS_URL = 'https://www.youtube.com/all_comments?v=dQw4w9WgXcQ'
    YOUTUBE_COMMENTS_AJAX_URL = 'https://www.youtube.com/comment_ajax'
    USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36'

    def find_text(self,html, key, num_chars):

        # Find specified value in HTML tags.

        pos_begin = html.find(key) + len(key) + num_chars
        pos_end = html.find('"', pos_begin)

        return html[pos_begin : pos_end]

    def get_comments_html(self,html):

        # Get data (author and comment text) from the HTML code

        wholehtml = lxml.html.fromstring(html)
        item_sel = CSSSelector('.comment-item')
        text_sel = CSSSelector('.comment-text-content')
        author_sel = CSSSelector('.user-name')

        for item in item_sel(wholehtml):
            yield { 'author': author_sel(item)[0].text_content(), 'text': text_sel(item)[0].text_content() }

    def ajax_request(self,session, url, params, data, retries=10, sleep=20):

        # Make the Ajas request to fetch comments for page 1

        for _ in range(retries):
            response = session.post(url, params=params, data=data)
            if response.status_code == 200:
                response_dict = json.loads(response.text)
                return response_dict.get('page_token', None), response_dict['html_content']
            else:
                time.sleep(sleep)


    def download_comments(self,youtube_id):

        # Prepare the request for Youtube Ajax page.
        # We need a valid session, the video id and some parameters to tell the Ajax page what we want and how we want it (comments ordered by time)

        session = requests.Session()
        session.headers['User-Agent'] = self.USER_AGENT

        response = session.get(self.YOUTUBE_COMMENTS_URL.format(youtube_id=youtube_id))
        html = response.text

        # We need to find the token or we get locked out for attempted XSRF
        page_token = self.find_text(html, 'data-token', 2)
        session_token = self.find_text(html, 'XSRF_TOKEN', 4)

        for comment in self.get_comments_html(html):
            yield comment

        while page_token:

            data = { 'video_id': youtube_id, 'session_token': session_token }
            params = {'action_load_comments': 1, 'order_by_time': True, 'filter': youtube_id }
            params['order_menu'] = True

            response = self.ajax_request(session, self.YOUTUBE_COMMENTS_AJAX_URL, params, data)

            if not response:
                # That's ok, I'll retry
                break

            page_token, html = response

            for comment in self.get_comments_html(html):
                    yield comment


    def get_comments(self,video_id):

        # Collect all comments fetched and organize them in a JSON string to return
        
        current_comment_index = 0
        comments = []

        for comment in self.download_comments(video_id):

            
            comments.append(json.dumps(comment, ensure_ascii=False))
            current_comment_index += 1

            if current_comment_index >= 50:
                break
        
        return comments