# Credits
# OpenSubtitles: https://github.com/agonzalezro/python-opensubtitles
# MP4 Automater: https://github.com/mdhiggins/sickbeard_mp4_automator
###############################################
import os
import sys
import logging
from opensubtitles import OpenSubtitles
from mkvtomp4 import MkvtoMp4

VIDEO_PREFIX = '/video/plextools'
TITLE = 'Plex Tools'
ART = 'art-default.jpg'
ICON = 'icon-default.png'
ICON_PREFS = 'icon-prefs.png'
HOST = 'http://localhost:32400'
SECTIONS = '%s/library/sections/'
SECTION = '%s/library/sections/%s/folder/'

SETTINGS = {
    'opensubtitles_server'  : 'http://plexapp.api.opensubtitles.org/xml-rpc',
    'user_agent'            : 'plexapp.com v9.0',
    'language'              : Prefs['language'],
    'username'              : Prefs['username'],
    'password'              : Prefs['password']
}

class MP4Settings:
    def __init__(self):
        self.ffmpeg = Prefs['FFMPEG_PATH']
        self.ffprobe = Prefs['FFPROBE_PATH']
        self.delete = Prefs['delete']
        self.output_extension = 'mp4'
        self.output_dir = None
        self.relocate_moov = True
        self.processMP4 = True
        self.copyto = None
        self.moveto = None
        self.vcodec = 'h264'
        self.acodec = 'aac'
        self.abitrate = None
        self.iOS = True
        self.awl = Prefs['language']
        self.swl = Prefs['language']
        self.adl = Prefs['language']
        self.sdl = Prefs['language']
        
class LogManager(object):
    def __init__(self, log_level=logging.INFO):        
        self.logger = logging.getLogger('STDOUT')
        self.log_level = log_level
        self.progress = []

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.progress.append(line)
            
    def flush(self):
        for handler in self.logger.handlers:
            handler.flush()
            
    def getCurrentProgress(self):
        if len(self.progress) == 0:
            return ''
        return self.progress[-1]
        
    def reset(self):
        self.progress[:] = []
        
class Core():
    def __init__(self):
        self.lm = LogManager(logging.DEBUG)
        sys.stdout = self.lm    
    
    def getLatest(self):
        return self.lm.getCurrentProgress()
        
    def reset(self):
        self.lm.reset()
    
    def isActive(self):
        if len(self.lm.progress) == 0:
            return False
        else:
            return True
        
core = Core()
        
###############################################
def Start():
    ObjectContainer.title1 = TITLE
    ObjectContainer.art = R(ART)
    DirectoryObject.thumb = R(ICON)
    DirectoryObject.art = R(ART)

###############################################
@handler('/video/plextools', TITLE, art=ART, thumb=ICON)
def MainMenu():
    oc = ObjectContainer()
    
    directories = XML.ElementFromURL(SECTIONS % (HOST), cacheTime=0).xpath('//Directory')
    for directory in directories:
        oc.add(DirectoryObject(key = Callback(ShowSubMenu, url=SECTION % (HOST, directory.get('key')), type=directory.get('type')), title = directory.get('title')))
    
    oc.add(PrefsObject(title = 'Preferences', thumb = R(ICON_PREFS)))
    oc.add(DirectoryObject(key = Callback(GetConversions), title = 'MP4 conversions in progress'))
    return oc

###############################################
@route('/video/plextools/showsubmenu')
def ShowSubMenu(url, type=None):
    oc = ObjectContainer()
    elements = XML.ElementFromURL(url, cacheTime=0).xpath('/*/*')
    for element in elements:
        key = element.get('key')
        if type == 'show':
            if '/library/metadata' not in key:
                oc.add(DirectoryObject(key = Callback(ShowSubMenu, url=HOST+key, type=type), title = element.get('title')))
            else:
                oc.add(DirectoryObject(key = Callback(ShowTaskMenu, key=key, type=type), title = element.get('title')))
        else:
            oc.add(DirectoryObject(key = Callback(ShowTaskMenu, key=key, type=type), title = element.get('title')))

    return oc

###############################################
@route('/video/plextools/showtaskmenu')
def ShowTaskMenu(key, type):
    oc = ObjectContainer()
    oc.add(DirectoryObject(key = Callback(DownloadSubtitles, key=key, type=type), title = 'Download Subtitles'))
    oc.add(DirectoryObject(key = Callback(ConvertToMP4, key=key), title = 'Convert to MP4'))
    return oc

###############################################
@route('/video/plextools/downloadsubtitles')
def DownloadSubtitles(key, type):
    data = []
    oc = ObjectContainer()
    video = XML.ElementFromURL(HOST + key).xpath('//Video')[0]
    if video:
        subs = OpenSubtitles(SETTINGS)
        token = subs.login(SETTINGS['username'], SETTINGS['password'])
        full_path = video.xpath('./Media/Part')[0].get('file')
        root, filename = os.path.split(full_path)
        filename = filename.split('.')[0]

        if type == 'show':
            title = video.get('grandparentTitle')
            season = video.get('parentIndex')
            episode = video.get('index')
            if title and season and episode:
                data = subs.search_subtitles([{'sublanguageid': SETTINGS['language'], 'query': title, 'season': season, 'episode': episode}])
        else:
            title = video.get('title')
            if title:
                data = subs.search_subtitles([{'sublanguageid': SETTINGS['language'], 'query': title}])

        subs.logout()
        for item in data:
            oc.add(DirectoryObject(key = Callback(WriteSubtitle, url=item['SubDownloadLink'], root=root, filename=filename), title = item['MovieReleaseName'] + ' (' + item['SubDownloadsCnt'] + ' downloads)'))
    return oc

###############################################
@route('/video/plextools/converttomp4')
def ConvertToMP4(key):
    message = ''
    video = XML.ElementFromURL(HOST + key).xpath('//Video')[0]
    if video:
        file = video.xpath('./Media/Part')[0].get('file')
        try:            
            Thread.Create(convert, file=file)
            message = 'Converting to MP4 has begun'
        except Exception, e:
            Log.Debug(e)
            message = 'There was an error converting the file ' + file
    else:
        message = 'There was an error converting the file'

    return MessageContainer('Convert to MP4', message)

###############################################
@route('/video/plextools/writesubtitle')
def WriteSubtitle(url, root, filename):
    message = ''
    try:
        if url:
            gzip = HTTP.Request(url, headers={'Accept-Encoding':'gzip'}).content
            data = ParseSRT(Archive.GzipDecompress(gzip))
            srt = os.open(root + '\\' + filename + '.' + SETTINGS['language'] + '.srt', os.O_WRONLY|os.O_CREAT)
            os.write(srt, data + '\n')
            os.close(srt)
            message = 'Subtitle downloaded successfully'
        else:
            message = 'Could not find a matching subtitle'

    except Exception, e:
        Log.Debug(e)
        message = 'There was an error saving the subtitle'

    return MessageContainer('Download Subtitles', message)
    
###############################################
@route('/video/plextools/getconversions')
def GetConversions():
    oc = ObjectContainer()
    if core.isActive():
        oc.add(DirectoryObject(key = Callback(GetConversions), title = str(core.getLatest()) + ' - Click to refresh'))
    else:
        oc.add(DirectoryObject(key = Callback(GetConversions), title = 'No active conversions'))    
    return oc
    
###############################################
def ParseSRT(data):
    lines = []
    if data:
        for row in data.split('\r\n'):
            if row == '\n':
                line = row
            else:
                line = row + '\n'
            lines.append(line)
    return ''.join(lines).strip('\r\n')
    
def convert(file):
    converter = MkvtoMp4(MP4Settings())
    output = converter.process(file, True)
    converter.QTFS(output['output'])
    print 'Conversion of ' + file + ' completed'
    core.reset()