# -*- coding: utf-8 -*-
import leancloud
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
from youtubesearchpython import Video, ResultMode
import spacy
import re
nlp = spacy.load("en_core_web_sm")


def captions(uri, **params):
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
    transcript_type = ''
    try:
        # find_generated_transcript
        transcript = transcript_list.find_manually_created_transcript(langs)
        transcript_type = 'manually'
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        try:
            transcript = transcript_list.find_generated_transcript(langs)
            transcript_type = 'generated'
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            transcript_type = 'no subtitle'
            return transcript_type, None
    return transcript_type, transcript.fetch()
    # print(transcript)
    # for t in transcript.fetch():
    #    result += f" 00{t['start']}00 {t['text']} ".format(t)
    #    #result += f"{t['text']}".format(t)
    # return result


def mergeToDoc(transcripts):
    doc = ''
    for t in transcripts:
        doc += f"00{t['start']}00 {t['text']} ".format(t)
    return doc


def breakUpToSentences(doc):
    import spacy
    from spacy.lang.en import English
    nlp_simple = English()
    # nlp_simple.add_pipe(nlp_simple.add_pipe('sentencizer'))
    nlp_simple.add_pipe('sentencizer')

    return nlp_simple(doc).sents


def breakUpToToken(text):
    sentence = {'seekTo': '', 'words': []}
    doc = nlp(text.text)
    # print(text.text)
    for token in doc:
        match = re.match("00[0-9]+.[0-9]+00", token.text)
        if(match):
            if (sentence['seekTo'] == ''):
                sentence['seekTo'] = match[0]
            continue
        sentence['words'].append(token.text)
    return sentence


def format(doc):
    # 特殊字符的替换
    doc = doc.replace("&gt;", ">")
    doc = doc.replace("<i>", " ")
    doc = doc.replace("</i> ", " ")
    # 删除所有换行
    doc = doc.replace("\n", " ")
    #  替换所有不间断空格 \u00A0
    doc = doc.replace("\u00A0", " ")
    #  多个空格替换为一个
    doc = re.sub(r'\\s{2,}', " ", doc)
    return doc


def getSentences(uri):
    sentences = []
    transcript_type, transcripts = captions(uri)
    print(transcript_type)
    if(transcript_type == 'manually'):
        doc = mergeToDoc(transcripts)
        doc = format(doc)
        sentences_text = breakUpToSentences(doc)
        for s in sentences_text:
            sentences.append(breakUpToToken(s))
    if(transcript_type == 'generated'):
        pass
    if(transcript_type == 'no subtitle'):
        pass
    return sentences


def getVideoInfo(uri):
    '''
    Getting information about video or its formats using video link or video ID.

    `Video.get` method will give both information & formats of the video
    `Video.getInfo` method will give only information about the video.
    `Video.getFormats` method will give only formats of the video.

    You may either pass link or ID, method will take care itself.
    '''

    videoInfo = Video.getInfo(uri, mode=ResultMode.json)
    return videoInfo


def buildArticle(uri, user, sentences, videoInfo):
    Article = leancloud.Object.extend('Article')
    article = Article()
    article.set('owner', user)
    article.set('sentences', sentences)
    article.set('thumbnail', videoInfo['thumbnails']
                [len(videoInfo['thumbnails'])-1]['url'])
    article.set('title', videoInfo['title'])
    article.set('channel', videoInfo['channel']['id'])
    article.set('avatar', videoInfo['avatar'])
    article.set('youtube', uri)
    # article.WordCount = computeArticleWordCount(article.Sentences)
    return article


def getContent(uri, engine):
    #sentences = getSentences(uri)
    sentences = []
    videoInfo = getVideoInfo(uri)
    article = buildArticle(uri, engine.current.user, sentences, videoInfo)
    return article.dump()


if __name__ == "__main__":
    uri = 'https://www.youtube.com/watch?v=MYpcImFEDJg'
    #youtube.youtube(uri, engine)
