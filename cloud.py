# coding: utf-8

import sys
import json
from leancloud import Engine
from leancloud import LeanEngineError
try:
    from urllib.parse import urlparse, urlencode, parse_qsl
    from urllib.request import urlopen
    from urllib.error import HTTPError, URLError
    from http.client import HTTPException
except ImportError:
    from urlparse import urlparse, parse_qsl
    from urllib import urlencode
    from urllib2 import urlopen, HTTPError, URLError
    from httplib import HTTPException
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from youtubesearchpython import Video, Channel, ResultMode

engine = Engine()


@engine.define
def captions(uri, **params):
    video_imd = uri
    if uri.startswith('http'):
        queries = dict(parse_qsl(urlparse(uri).query))

        video_id = queries.get('v')
        # 支持 app 分享出来的链接
        if video_id is None:
            video_id = urlparse(uri).path.replace("/", "")
        if video_id is None:
            return "no subtitle"
        print(f'get video_id={video_id}')

    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    # filter for manually created transcripts
    langs = ['en', 'en-GB', 'en-US', 'en-CA']
    result = ''
    try:
        # find_generated_transcript
        transcript = transcript_list.find_manually_created_transcript(langs)
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        try:
            transcript = transcript_list.find_generated_transcript(langs)
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            return 'no subtitle'

    for t in transcript.fetch():
        result += f" 00{t['start']}00 {t['text']} ".format(t)
    return result


@engine.define
def videoInfo(uri, **params):
    '''
    Getting information about video or its formats using video link or video ID.

    `Video.get` method will give both information & formats of the video
    `Video.getInfo` method will give only information about the video.
    `Video.getFormats` method will give only formats of the video.

    You may either pass link or ID, method will take care itself.
    '''

    videoInfo = Video.getInfo(uri, mode=ResultMode.json)
    channelId = videoInfo['channel']['id']
    videoInfo['avatar'] = Channel.get(channelId)["thumbnails"][-1]["url"]
    return videoInfo
