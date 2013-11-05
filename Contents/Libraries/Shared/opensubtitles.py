from xmlrpclib import ServerProxy

class OpenSubtitles(object):
    '''OpenSubtitles API wrapper.

    Please check the official API documentation at:
    http://trac.opensubtitles.org/projects/opensubtitles/wiki/XMLRPC
    '''

    def __init__(self, settings):
        self.settings = settings
        self.xmlrpc = ServerProxy(self.settings['opensubtitles_server'],
                                  allow_none=True)
        self.language = self.settings['language']
        self.token = None

    def _get_from_data_or_none(self, key):
        '''Return the key getted from data if the status is 200,
        otherwise return None.
        '''
        status = self.data.get('status').split()[0]
        return self.data.get(key) if '200' == status else None

    def login(self, username, password):
        '''Returns token is login is ok, otherwise None.
        '''
        self.data = self.xmlrpc.LogIn(username, password,
                                 self.language,  self.settings['user_agent'])
        token = self._get_from_data_or_none('token')
        if token:
            self.token = token
        return token

    def logout(self):
        '''Returns True is logout is ok, otherwise None.
        '''
        data = self.xmlrpc.LogOut(self.token)
        return '200' in data.get('status')

    def search_subtitles(self, params):
        '''Returns a list with the subtitles info.
        '''
        self.data = self.xmlrpc.SearchSubtitles(self.token, params)
        return self._get_from_data_or_none('data')

    def try_upload_subtitles(self, params):
        '''Return True if the subtitle is on database, False if not.
        '''
        self.data = self.xmlrpc.TryUploadSubtitles(self.token, params)
        return self._get_from_data_or_none('alreadyindb') == 1

    def upload_subtitles(self, params):
        '''Returns the URL of the subtitle in case that the upload is OK,
        other case returns None.
        '''
        self.data = self.xmlrpc.UploadSubtitles(self.token, params)
        return self._get_from_data_or_none('data')
        
    def download_subtitles(self, params):
        self.data = self.xmlrpc.DownloadSubtitles(self.token, params)
        return self.get_from_data_or_none('data')
        
    def download_subtitles(self, params):
        self.data = self.xmlrpc.DownloadSubtitles(self.token, params)
        return self.get_from_data_or_none('data')

    def no_operation(self):
        '''Return True if the session is actived, False othercase.

        .. note:: this method should be called 15 minutes after last request to
                  the xmlrpc server.
        '''
        data = self.xmlrpc.NoOperation(self.token)
        return '200' in data.get('status')

    def auto_update(self, program):
        '''Returns info of the program: last_version, url, comments...
        '''
        data = self.xmlrpc.AutoUpdate(program)
        return data if '200' in data.get('status') else None

    def search_movies_on_imdb(self, params):
        self.data = self.xmlrpc.SearchMoviesOnIMDB(self.token, params)
        return self.data