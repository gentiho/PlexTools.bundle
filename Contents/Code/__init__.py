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
SECTION = '/library/sections/%s/all/'
SECTIONS = '%s/library/sections/'



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
        self.abitrate = int(Prefs['abitrate'])
        self.iOS = True
        self.awl = Prefs['language']
        self.swl = Prefs['language']
        self.adl = Prefs['language']
        self.sdl = Prefs['language']

#Used to communicate with the conversion thread.  Make sure to only read from the
#main thread.  Calling write() or flush() could make the main thread exit if
#self.exitNow is set.
class LogManager(object):
    def __init__(self, log_level=logging.INFO):        
        self.status = 'init'
        self.exitNow = False
        self.logger = logging.getLogger('STDOUT')
        self.log_level = log_level
        self.progress = []

    def write(self, buf):
        self.checkAndExit()
        for line in buf.rstrip().splitlines():
            #Log.Debug('lm.write():%s', line)
            self.progress.append(line)
            
    def flush(self):
        self.checkAndExit()
        for handler in self.logger.handlers:
            handler.flush()
            
    def getLatest(self):
        if len(self.progress) == 0:
            return ''
        return self.progress[-1]

    def getStatus(self):
        return self.status

    def setStatus(self, s):
        self.status = s
        
    def reset(self):
        self.status = ''
        self.progress[:] = []
        self.exitNow = False

    def requestExit(self):
        self.exitNow = True

    def shouldExit(self):
        return(self.exitNow)

    def checkAndExit(self): 
        if self.exitNow:
            Log.Debug('Conversion thread requested to exit');
            #raise a SystemExit exception within the conversion thread
            raise SystemExit('Canceled')
    
    def isActive(self):
        if plexToolsThread <> None:
            if plexToolsThread.isAlive():
                return True
        return False
      
lm = LogManager(logging.DEBUG)
sys.stdout = lm 
plexToolsThread = None
        
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
        #Log.Debug(XML.StringFromElement(directory))
        oc.add(
            DirectoryObject(
                key = Callback(ShowSubMenu, key = SECTION % (directory.get('key')), type=directory.get('type')), 
                title = directory.get('title'), 
                thumb = directory.get('thumb'), 
                art = directory.get('art')
            )
        )
    
    oc.add(PrefsObject(title = 'Preferences', thumb = R(ICON_PREFS)))
    oc.add(DirectoryObject(key = Callback(GetConversions, junk=str(Util.Random())), title = 'MP4 conversions in progress'))
    return oc

###############################################
@route('/video/plextools/showsubmenu')
def ShowSubMenu(key, type=None):
    xml = XML.ElementFromURL(HOST + key)
    #Log.Debug(XML.StringFromElement(xml))
    elements = xml.xpath('/*/*')
    try: title2 = xml.xpath('//MediaContainer')[0].get('title1')
    except: title2 = 'Plex Tools'
    oc = ObjectContainer(title2=title2,no_cache=True)
    for element in elements:
        nkey = element.get('key')
        art = element.get('art')
        thumb = element.get('thumb')        
        if type == 'show':
            if '/children' in nkey:
                oc.add(DirectoryObject(key = Callback(ShowSubMenu, key=nkey, type=type), title = element.get('title'), thumb = thumb, art = art))
            else:
                oc.add(DirectoryObject(key = Callback(ShowTaskMenu, key=nkey, type=type), title = element.get('title'), thumb = thumb, art = art))
        else:
            oc.add(DirectoryObject(key = Callback(ShowTaskMenu, key=nkey, type=type), title = element.get('title'), thumb = thumb, art = art))
    try: oc.add(DirectoryObject(key = Callback(ShowTaskMenu, key=key, type=type), title = 'Convert All Items', thumb = R(ICON)))
    except: Log.Exception('There was an error adding All Items [%s]', e.message)
    return oc

###############################################
@route('/video/plextools/showtaskmenu')
def ShowTaskMenu(key, type):
    xml = XML.ElementFromURL(HOST + key)
    #Log.Debug(XML.StringFromElement(xml))
    files = xml.xpath('//Media/Part/@file')
    oc = ObjectContainer(title2='Tasks', no_history=True, no_cache=True)
    #oc.add(DirectoryObject(key = Callback(DownloadSubtitles, key=key, type=type), title = 'Download %s %s' % (len(files),'Subtitle' if len(files)==1 else String.Pluralize('Subtitle'))))  #commented out since right now we only get 1 subtitle
    if files and len(files) == 1:
        oc.add(DirectoryObject(key = Callback(DownloadSubtitles, key=key, type=type), title = 'Download Subtitles'))
    if files and (len(files) > 0):
        if len(files) > 1:
            oc.add(DirectoryObject(key = Callback(ConvertToMP4, files=files), title = 'Convert All %s Videos to MP4' % len(files)))
        if len(files) < 40:  #limit how many to display
            for i,file in enumerate(files):
                try:
                    (path, fn) = os.path.split(file)
                    dn = fn if len(fn) < 43 else fn[:20]+"..."+fn[len(fn)-20:]
                    oc.add(DirectoryObject(key = Callback(ConvertToMP4, files=[file]), title = 'Convert to MP4: %s' % dn))
                except Exception, e:
                    Log.Exception('There was an error adding file (%s) [%s]', file, e.message)
    return oc

###############################################
@route('/video/plextools/downloadsubtitles')
def DownloadSubtitles(key, type):
    data = []
    oc = ObjectContainer(no_cache=True, title2='Subtitles')
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
@route('/video/plextools/converttomp4', files=list)
def ConvertToMP4(files):
    global plexToolsThread
    if lm.isActive():
        Log.Info('Conversion not started - one already running')
        return MessageContainer('Cannot convert', 'Conversion already in progress')
    message = ''
    if type(files) is str:
        files = [files]
    if files and (len(files) > 0):
        Log.Debug('Converting %s file(s)', str(len(files)))
        try:            
            plexToolsThread = Thread.Create(convert, files=files)
            #Debug.Log(type(t))
            message = 'Converting to MP4 has begun'
        except Exception, e:
            Log.Exception(e)
            message = 'There was an error converting to MP4'
    else:
        message = 'There was an error converting a file'
    #oc = GetConversions('3.14')
    #oc.add(MessageContainer('Convert to MP4', message))
    #return oc
    return(MessageContainer('Convert to MP4', message))

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
        Log.Exception(e)
        message = 'There was an error saving the subtitle'

    return MessageContainer('Download Subtitles', message)
    
###############################################
@route('/video/plextools/getconversions')
def GetConversions(junk):
    oc = ObjectContainer(no_cache=True, no_history=True)
    if lm.isActive():
        oc.add(DirectoryObject(key = Callback(GetConversions, junk=str(Util.Random())), title = str(lm.getStatus()) + ' - [Click to refresh]'))
        oc.add(DirectoryObject(key = Callback(GetConversions, junk=str(Util.Random())), title = str(lm.getLatest()) + ' - [Click to refresh]'))
        oc.add(DirectoryObject(key = Callback(CancelConversions), title = 'Cancel Conversions'))
    else:
        oc.add(DirectoryObject(key = Callback(GetConversions, junk=str(Util.Random())), title = 'No active conversions'))
    return oc

###############################################
@route('/video/plextools/cancelconversions')
def CancelConversions():
    lm.requestExit()
    return MessageContainer('Canceling', 'Canceling conversion.  This may take a while for ffmpeg to stop.')

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
    
def convert(files):
    try:
        lm.setStatus('Initializing %s files' % str(len(files)))
        for i,file in enumerate(files):
            if lm.shouldExit():
                Log.Warn('Conversion Cancelled')
                break
            try:
                Log.Info('Converting %s', file)
                converter = MkvtoMp4(MP4Settings())
                if len(files) == 1:
                    lm.setStatus('Converting ' + file)
                else:
                    lm.setStatus('Converting file %s of %s' % (str(i+1), str(len(files))))
                output = converter.process(file, True)
                if len(files) == 0:
                    lm.setStatus('Optimizing ' + file)
                else:
                    lm.setStatus('Optimizing file %s of %s' % (str(i+1), str(len(files))))
                converter.QTFS(output['output'])
                #Thread.Sleep(5)
                print 'Conversion of ' + file + ' completed'
                Log.Info('Completed %s', file)
            except Exception, e:
                Log.Exception('There was an error converting the file (%s) [%s]', file, e.message)
        lm.reset()
        lm.setStatus('Done')
    except Exception, e:
        Log.Exception('There was an error converting to mp4 [%s]', e.message)
        lm.reset()
        lm.setStatus('Done - Error')
    except BaseException:  #catch the SystemExit exception
        Log.Warn('Conversion thread canceled')
        lm.reset()
        lm.setStatus('Cancelled')
