# Credits
# OpenSubtitles: https://github.com/agonzalezro/python-opensubtitles
# MP4 Automater: https://github.com/mdhiggins/sickbeard_mp4_automator
##############################################################################################
import os
import sys
import logging, re
import time
import urllib
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
TMDB_URL = 'https://api.tmdb.org/3/movie/%s?api_key=a3dc111e66105f6387e99393813ae4d5&append_to_response=releases,credits&language=%s'
TVDB_URL = 'http://thetvdb.com/api/D4DDDAEFAD083E6F/series/%s'
SETTINGS = {
    'opensubtitles_server'  : 'http://api.opensubtitles.org/xml-rpc',
    'user_agent'            : 'plexapp.com v9.0',
    'language'              : Prefs['language'],
    'username'              : Prefs['username'],
    'password'              : Prefs['password']
}

def IsFFMpegSet():
    if Prefs['FFMPEG_PATH'] and Prefs['FFPROBE_PATH']:
        return True
    return False

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
        self.acodec = Prefs['acodec']
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
            raise SystemExit('Canceled')

    def isActive(self):
        if plexToolsThread <> None:
            if plexToolsThread.isAlive():
                return True
        return False

lm = LogManager(logging.DEBUG)
sys.stdout = lm
plexToolsThread = None

##############################################################################################
def Start():
    ObjectContainer.title1 = TITLE
    ObjectContainer.art = R(ART)
    ObjectContainer.header = 'PlexTools'
    DirectoryObject.thumb = R(ICON)
    DirectoryObject.art = R(ART)

def ValidatePrefs():
    if Prefs['auto_download']:
        Log.Info('Starting Auto Downloader')
        Thread.Create(AutoDownload)

##############################################################################################
@handler('/video/plextools', TITLE, art=ART, thumb=ICON)
def MainMenu():
    oc = ObjectContainer()

    directories = XML.ElementFromURL(SECTIONS % (HOST), cacheTime=0).xpath('//Directory')
    for directory in directories:
        oc.add(
            DirectoryObject(
                key = Callback(ShowSubMenu, key = SECTION % (directory.get('key')), type=directory.get('type')),
                title = directory.get('title'),
                thumb = directory.get('thumb'),
                art = directory.get('art')
            )
        )

    oc.add(PrefsObject(title = 'Preferences', thumb = R(ICON_PREFS)))
    if IsFFMpegSet():
        oc.add(DirectoryObject(key = Callback(GetConversions, junk=str(Util.Random())), title = 'MP4 conversions in progress'))
    return oc

##############################################################################################
@route('/video/plextools/showsubmenu')
def ShowSubMenu(key, type=None):
    xml = XML.ElementFromURL(HOST + key)
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
                oc.add(PopupDirectoryObject(key = Callback(ShowSubMenu, key=nkey, type=type), title = element.get('title'), thumb = thumb, art = art))
            else:
                oc.add(PopupDirectoryObject(key = Callback(ShowTaskMenu, key=nkey, type=type), title = element.get('title'), thumb = thumb, art = art))
        else:
            oc.add(PopupDirectoryObject(key = Callback(ShowTaskMenu, key=nkey, type=type), title = element.get('title'), thumb = thumb, art = art))
    if IsFFMpegSet():
        try: oc.add(PopupDirectoryObject(key = Callback(ShowTaskMenu, key=key, type=type), title = 'Select All Items', thumb = R(ICON)))
        except: Log.Exception('There was an error adding All Items [%s]', e.message)
    return oc

##############################################################################################
@route('/video/plextools/showtaskmenu')
def ShowTaskMenu(key, type):
    xml = XML.ElementFromURL(HOST + key)
    files = xml.xpath('//Media/Part/@file')
    movies = None
    if type=='movie' and Prefs['enable_rename']:
        movies = xml.xpath('//Video')
        if len(movies) == 0: movies = None
    oc = ObjectContainer(title2='Tasks', no_history=True, no_cache=True)
    if files and (len(files) == 1):
        oc.add(PopupDirectoryObject(key = Callback(DownloadSubtitles, key=key, type=type), title = 'Download Subtitles'))
    if movies:
        if len(movies) == 1:
            try:
                (basepath, oldFolderName, newFolderName) = getNewVideoFolderName(movies[0])
                if newFolderName <> None:
                    oc.add(PopupDirectoryObject(key = Callback(RenameFolders, key=key, type=type), title = 'Rename Folder to "' + newFolderName + '"'))
            except: pass
        else:
            oc.add(PopupDirectoryObject(key = Callback(RenameFolders, key=key, type=type), title = 'Rename All %s Movie Folders' % len(movies)))
    if IsFFMpegSet() and files and (len(files) > 0):
        if len(files) > 1:
            oc.add(PopupDirectoryObject(key = Callback(ConvertToMP4, files=files), title = 'Convert All %s Videos to MP4' % len(files)))
        if len(files) < 40:  #limit how many to display
            for i,file in enumerate(files):
                try:
                    (path, fn) = os.path.split(file)
                    dn = fn if len(fn) < 43 else fn[:20]+"..."+fn[len(fn)-20:]
                    filtered_string = urllib.unquote(dn).decode('utf8')
                    oc.add(PopupDirectoryObject(key = Callback(ConvertToMP4, files=[file]), title = 'Convert to MP4: %s' % filtered_string))
                except Exception, e:
                    Log.Exception('There was an error adding file (%s) [%s]', file, e.message)
    return oc

##############################################################################################
@route('/video/plextools/downloadsubtitles')
def DownloadSubtitles(key, type):
    subtitles = []
    video = XML.ElementFromURL(HOST + key).xpath('//Video')[0]
    root,filename = GetPaths(video)
    oc = ObjectContainer(no_cache=True, title2='Subtitles')
    if video:
        try:
            type = video.get('type')
            guid = GetIMDBID(video.get('guid'))
            season = video.get('parentIndex')
            episode = video.get('index')
            subtitles.append({'type':type, 'root':root, 'filename':filename, 'season':season, 'episode':episode, 'id':guid})

            data = SearchSubtitles(subtitles, auto=False)
            if len(data) == 0:
                return ObjectContainer(header='No Subtitles Found', message='No subtitles could be found for your selected language')
            else:
                for item in data:
                    oc.add(PopupDirectoryObject(key = Callback(GetSubtitleStatus, url=item['SubDownloadLink'], root=root, filename=filename), summary='Filename: ' + filename, title = item['MovieReleaseName'] + ' (' + item['SubDownloadsCnt'] + ' downloads)'))
        except Exception, e:
            Log.Exception('There was an error connecting to Opensubtitles.org (%s)', e.message)
            return ObjectContainer(header='Error', message='There was an error connecting to Opensubtitles.org')
    return oc

##############################################################################################
@route('/video/plextools/getsubtitlestatus')
def GetSubtitleStatus(url, root, filename):
    response = WriteSubtitle(url, root, filename)
    if response == 1:
        UpdateLibrary()
        message='Subtitle successfully saved'
    else:
        message='There was a problem saving your subtitle'

    return ObjectContainer(header='Download Subtitles', message=message)

##############################################################################################
@route('/video/plextools/renamefolders')
def RenameFolders(key, type):
    global plexToolsThread
    if lm.isActive():
        Log.Info('Rename not started - thread already running')
        return ObjectContainer(header='Cannot rename folder', message='Cannot run yet.  Conversion or Renaming is already in progress')
    xml = XML.ElementFromURL(HOST + key)
    movies = xml.xpath('//Video')
    if movies and (len(movies) > 0):
        try:
            plexToolsThread = Thread.Create(renamemovies, movies=movies)
            message = 'Renaming of Folders has started'
        except Exception, e:
            Log.Exception('There was an error renaming folders [%s]', e.message)
            message = 'There was an error renaming folders'
    else:
        Log.Warn('Rename Folders did not find any movies to rename')
        message = 'Unable to find any folders to rename'

    return ObjectContainer(header='Rename Folders', message=message)

##############################################################################################
@route('/video/plextools/converttomp4', files=list)
def ConvertToMP4(files):
    global plexToolsThread
    if lm.isActive():
        Log.Info('Conversion not started - thread already running')
        return ObjectContainer(header='Cannot convert', message='Cannot run yet. Conversion or Renaming is already in progress')
    message = ''
    if type(files) is str:
        files = [files]
    if files and (len(files) > 0):
        try:
            plexToolsThread = Thread.Create(convert, files=files)
            message = 'Converting to MP4 has started'
        except Exception, e:
            Log.Exception('There was an error converting to mp4 [%s]', e.message)
            message = 'There was an error converting to MP4'
    else:
        message = 'There was an error converting a file'

    return ObjectContainer(header='Convert to MP4', message=message)

##############################################################################################
@route('/video/plextools/getconversions')
def GetConversions(junk):
    oc = ObjectContainer(no_cache=True, no_history=True)
    if lm.isActive():
        oc.add(PopupDirectoryObject(key = Callback(GetConversions, junk=str(Util.Random())), title = str(lm.getStatus())))
        oc.add(PopupDirectoryObject(key = Callback(GetConversions, junk=str(Util.Random())), title = str(lm.getLatest())))
        oc.add(PopupDirectoryObject(key = Callback(GetConversions, junk=str(Util.Random())), title = '[Select to refresh]'))
        oc.add(PopupDirectoryObject(key = Callback(CancelConversions), title = 'Cancel Conversions'))
    else:
        oc.add(PopupDirectoryObject(key = Callback(GetConversions, junk=str(Util.Random())), title = 'No active conversions'))
    return oc

##############################################################################################
@route('/video/plextools/cancelconversions')
def CancelConversions():
    lm.requestExit()
    return ObjectContainer(header='Canceling', message='Canceling conversion. This may take a while to stop.')

##############################################################################################
def AutoDownload():
    subtitles = []
    while Prefs['auto_download']:
        directories = XML.ElementFromURL(SECTIONS % (HOST), cacheTime=0).xpath('//Directory')
        for directory in directories:

            ##### Check inside every loop #####
            if Prefs['auto_download'] == False:
                return
            ###################################

            agent = directory.get('agent')
            type = directory.get('type')
            if agent == 'com.plexapp.agents.none':
                continue
            else:
                key = directory.get('key')
                items = XML.ElementFromURL(HOST + SECTION % (key)).xpath('/*/*')
                for item in items:
                    ##### Check inside every loop #####
                    if Prefs['auto_download'] == False:
                        return
                    ###################################

                    video_path = item.get('key')
                    if type == 'movie':
                        video_data = XML.ElementFromURL(HOST + video_path, cacheTime=0)
                        streams = video_data.xpath("//Stream[@format='srt' and @languageCode='" + SETTINGS['language'] + "']")
                        if len(streams) == 0:
                            root,filename = GetPaths(item)
                            guid = GetIMDBID(video_data.xpath('//Video')[0].get('guid'))
                            subtitles.append({'type':'movie', 'root':root, 'filename':filename, 'id':guid})
                    else:
                        seasons = XML.ElementFromURL(HOST + video_path, cacheTime=0).xpath('//Directory')
                        for season in seasons:

                            ##### Check inside every loop #####
                            if Prefs['auto_download'] == False:
                                return
                            ###################################

                            season_key = season.get('key')
                            episodes = XML.ElementFromURL(HOST + season_key, cacheTime=0).xpath('//Video')
                            for episode in episodes:

                                ##### Check inside every loop #####
                                if Prefs['auto_download'] == False:
                                    return
                                ###################################

                                episode_key = episode.get('key')
                                video = XML.ElementFromURL(HOST + episode_key, cacheTime=0)
                                streams = video.xpath("//Stream[@format='srt' and @languageCode='" + Prefs['language'] + "']")
                                if len(streams) == 0:
                                    data = video.xpath('//Video')[0]
                                    root,filename = GetPaths(data)
                                    guid = GetIMDBID(data.get('guid'))
                                    subtitles.append({'type':'episode', 'root':root, 'filename':filename, 'season':data.get('parentIndex'), 'episode':data.get('index'), 'id':guid})
        SearchSubtitles(subtitles, auto=True)
        subtitles = []
        frequency = int(Prefs['hour_check'])
        sleep_time = frequency * 60 * 60
        Log.Info('Will check for new subtitles again in ' + Prefs['hour_check'] + ' hours')
        while sleep_time > 0:
            sleep_time = sleep_time - 3600
            time.sleep(3600)
    return

def SearchSubtitles(subtitles, auto=False):
    try:
        sortedList = []
        update = False
        subs = OpenSubtitles(SETTINGS)
        token = subs.login(SETTINGS['username'], SETTINGS['password'])
        for item in subtitles:
            data = cleanedList = sortedList = []

            if item['type'] == 'episode':
                data = subs.search_subtitles([{'sublanguageid': SETTINGS['language'], 'imdbid':  item['id'], 'season': item['season'], 'episode': item['episode']}])
            else:
                data = subs.search_subtitles([{'sublanguageid': SETTINGS['language'], 'imdbid':  item['id']}])

            if data != False:
                for video in data:
                    if video['SubFormat'] == 'srt':
                        cleanedList.append(video)
                sortedList = sorted(cleanedList, key=lambda k: int(k['SubDownloadsCnt']), reverse=True)
                if auto == True:
                    update = True
                    response = WriteSubtitle(sortedList[0]['SubDownloadLink'], item['root'], item['filename'])

            else:
                Log.Info('There are no subtites for ' + item['filename'] + ' at this time')
        subs.logout()

        if update:
            UpdateLibrary()
    except:
        Log.Exception('Error connecting to Opensubtitles.org')

    return sortedList

def WriteSubtitle(url, root, filename):
    message = 0
    name = os.path.join(root, filename + '.' + SETTINGS['language'] + '.srt')
    try:
        if url:
            gzip = HTTP.Request(url, headers={'Accept-Encoding':'gzip'}).content
            data = ParseSRT(Archive.GzipDecompress(gzip))
            srt = os.open(name, os.O_WRONLY|os.O_CREAT)
            os.write(srt, data + '\n')
            os.close(srt)
            Log.Info(name + ' successfully saved')
            message = 1
    except:
        Log.Exception('There was an error writing subtitle [%s]', name)
        message = 2

    return message

def GetPaths(video):
    full_path = String.Unquote(video.xpath('./Media/Part')[0].get('file'))
    root = os.path.dirname(full_path)
    filename = os.path.basename(full_path).split('.')[:-1]

    path = ''
    for segment in filename:
        path = path + segment + '.'
    filename = path[:-1]
    return root,filename

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

def UpdateLibrary():
    sections = XML.ElementFromURL(SECTIONS % (HOST), cacheTime=0).xpath('//Directory')
    for section in sections:
        key = section.get('key')
        Log.Info('Updating section #' + key)
        data = HTTP.Request(SECTIONS % (HOST) + key + '/refresh', cacheTime=0).content

    return data

def GetIMDBID(node):
    id = 0
    if node:
        if node.startswith('com.plexapp.agents.themoviedb://'):
            guid = node.split('com.plexapp.agents.themoviedb://')[1].split('?')[0]
            id = JSON.ObjectFromURL(TMDB_URL % (guid, 'en'))['imdb_id'][2:]

        elif node.startswith('com.plexapp.agents.thetvdb://'):
            guid = node.split('com.plexapp.agents.thetvdb://')[1].split('?')[0].split('/')[0]
            id = XML.ElementFromURL(TVDB_URL % (guid)).xpath('//IMDB_ID')[0].text[2:]

        elif node.startswith('com.plexapp.agents.imdb://'):
            id = node.split('com.plexapp.agents.imdb://')[1].split('?')[0][2:]

    return id

##############################################################################################
#parses the video object and figures out correct folder name.  Will raise Exception on error.
#returns (basepath, oldFolderName, None) is the folder name is correct OR
#returns (basepath, oldFolderName, newFolderName) which can be combined with os.path.join(basepath, newFolderName)
def getNewVideoFolderName(video):
    #do checks
    files = video.xpath('Media/Part/@file')
    if not files or len(files) == 0:
        raise Exception('No files found')
    (oldpath, oldfn) = os.path.split(files[0])
    (basepath, oldFolderName) = os.path.split(oldpath)
    if len(files) > 0:  #make sure all the files have the same path
        for f in files:
            if not samefile(oldpath, os.path.split(f)[0]):
                raise Exception('Warning. Multiple paths in included files.  Cannot process.')
    newFolderName = getCleanFilename(String.StripDiacritics(video.get('title')))
    if not newFolderName or len(newFolderName) == 0: raise Exception('Cleaned folder name is empty')
    try:    #only add in year if it's the correct format
        match = re.match(r'(\d{4})', video.get('year'))
        if match: newFolderName = newFolderName + ' (' + video.get('year')+')'
    except Exception, e:
        pass
    newpath = os.path.join(basepath, newFolderName)
    if samefile(oldpath, newpath):
        return (basepath, oldFolderName, None)
    return (basepath, oldFolderName, newFolderName)

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
                    lm.setStatus('Converting video %s of %s' % (str(i+1), str(len(files))))
                output = converter.process(file, True)
                if len(files) == 1:
                    lm.setStatus('Optimizing ' + file)
                else:
                    lm.setStatus('Optimizing video %s of %s' % (str(i+1), str(len(files))))
                converter.QTFS(output['output'])
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

#Converts a file name to something safe.  Tries to be safe for all operating systems
def getCleanFilename(s):
    new = ''
    for c in list(s):
      if not (c in r'<>:"/\|?*'):
        if ord(c)>31:
          new+=c
    new = re.sub(r'(\.+)', '.', new)
    new = re.sub(r'(\.*)$', '', new)
    return new

def samefile(path1, path2):
    return os.path.normcase(os.path.normpath(path1)) == os.path.normcase(os.path.normpath(path2))

def renamemovies(movies):
    try:
        lm.setStatus('Initializing %s files' % str(len(movies)))
        for i,movie in enumerate(movies):
            if lm.shouldExit():
                Log.Warn('Renaming Cancelled')
                break
            try:
                title = String.StripDiacritics(movie.get('title')) #DecodeHTMLEntities
                lm.setStatus('Checking %s of %s' % (str(i+1), str(len(movies))))
                try:
                    (basepath, oldFolderName, newFolderName) = getNewVideoFolderName(movie)
                    if newFolderName == None: continue
                    os.rename(os.path.join(basepath, oldFolderName),os.path.join(basepath, newFolderName))
                    Log.Info('Renamed (%s) to (%s) in %s', oldFolderName, newFolderName, basepath)
                except Exception,e:
                    Log.Exception('Skipping %s [%s]', title, e.message)
                    continue
                print 'Rename of ' + title + ' completed'
            except Exception, e:
                Log.Exception('There was an error renaming the file (%s) [%s]', movie.get('title'), e.message)
        lm.reset()
        lm.setStatus('Done')
        Log.Info('Renaming complete')
    except Exception, e:
        Log.Exception('There was an error renaming folder [%s]', e.message)
        lm.reset()
        lm.setStatus('Done - Error')
    except BaseException:  #catch the SystemExit exception
        Log.Warn('Rename thread canceled')
        lm.reset()
        lm.setStatus('Cancelled')