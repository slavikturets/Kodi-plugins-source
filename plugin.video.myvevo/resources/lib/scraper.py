# -*- coding: utf-8 -*-
# KodiAddon for myVEVO
#
from t1mlib import t1mAddon
import json
import re
import urllib
import urllib2
import cookielib
import xbmcplugin
import xbmcgui
import xbmc
import datetime
import HTMLParser
import re
import json
import sys
import os

h = HTMLParser.HTMLParser()
uqp = urllib.unquote_plus
qp  = urllib.quote_plus
UTF8 = 'utf-8'
VEVOAPI = 'https://apiv2.vevo.com'

class myAddon(t1mAddon):

  def getAutho(self, getMe=False):
      if self.addon.getSetting('login_name') != '':
          vevoName = self.addon.getSetting('login_name')
          vevoPswd = self.addon.getSetting('login_pass')
          udata = urllib.urlencode({'username': vevoName, 'password':vevoPswd, 'grant_type':'password'})
      else:
          udata = ' '
      uheaders = self.defaultHeaders.copy()
      uheaders['X-Requested-With'] = 'XMLHttpRequest'
      uheaders['Connection'] = 'keep-alive'
      html  = self.getRequest('http://www.vevo.com/auth', udata , uheaders)
      a = json.loads(html)
      if not getMe:
          return a['access_token']
      uheaders['Authorization'] = 'Bearer %s' % a['access_token']
      html = self.getRequest(VEVOAPI+'/me', None, uheaders)
      b = json.loads(html)
      return (a['access_token'], b.get('id'))


  def getAPI(self,url):
      autho = self.getAutho()
      uheaders = self.defaultHeaders.copy()
      uheaders['Authorization'] = 'Bearer %s' % autho
      uheaders['Connection'] = 'keep-alive'
      html = self.getRequest(url, None , uheaders)
      return json.loads(html)


  def getAddonMenu(self,url,ilist):
      menu = [('TV Channels',VEVOAPI+'/tv/channels?withShows=true&hoursAhead=24&token=','GE'),
              ('New releases',VEVOAPI+'/now?page=1&size=50&token=','GE'),
              ('Genres','/genres?page=1&size=50', 'GC'),
              ('Favorite Artists','GM','GM'),
              ('My Playlists','GS','GS'),
              ('Search','Search', 'GE')]
      for name, url, mode in menu:
          ilist = self.addMenuItem(name, mode, ilist, url, self.addonIcon, self.addonFanart, None, isFolder=True)
      return(ilist)


  def getAddonCats(self,url,ilist):
      xbmcplugin.setContent(int(sys.argv[1]), 'files')
      if not url.startswith('http'):
          url = VEVOAPI + url
      a = self.getAPI(url)
      infoList = None
      originUrl = url
      nextUrl = None
      if '&genre=' in originUrl:
          nextUrl = a['paging'].get('next')
          a = a['artists']
      for b in a:
          name = b['name']
          thumb = b['thumbnailUrl']
          if '&genre=' in originUrl:  
              mode = 'GE'
              url = VEVOAPI+'/artist/%s/videos?size=50&page=1&sort=MostRecent' % b['urlSafeName']
          else: 
             mode = 'GC'
             url = '/artists?page=1&size=50&genre=%s' % b['urlSafeName']
          ilist = self.addMenuItem(name, mode, ilist, url, thumb, thumb, infoList, isFolder=True)
      if nextUrl is not None:
          nextUrl += ('&genre='+originUrl.rsplit('&genre=',1)[1])
          name = '[COLOR blue]Next Page[/COLOR]'
          ilist = self.addMenuItem(name, 'GC', ilist, nextUrl, self.addonIcon, self.addonFanart, infoList, isFolder=True)
      return(ilist)


  def updateList(self, token = None, pid = None, cmd = None, name = None, desc = None, isrc = None, imageUrl = None):
      MAXPLISTITEMS = 25
      if token is None:
          token = self.getAutho()
      html = self.getRequest(VEVOAPI + ('/playlist/%s?token=%s' % (pid, token)))
      a = json.loads(html)
      ud = 'playlistId=%s' % qp(pid)
      if name is None:
          name = a['name']
      ud += '&name=%s' % qp(name)
      if desc is None:
          desc = a['description']
      ud += "&description=%s" % qp(desc)
      if imageUrl is None:
          imageUrl = a['imageUrl']
      ud += "&imageUrl=%s" % qp(imageUrl)
      b = a["videos"]
      if (cmd == 'ADDITEM') and (len(b) >= MAXPLISTITEMS):
          xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s)' % ( 'VEVO', 'List is Full', 5000) )
          return                 
      for c in b:
          if (cmd == 'DELITEM') and (c['isrc'] == isrc):
              continue
          else:
              ud += "&Isrcs=%s" % qp(c['isrc'])
      if cmd == 'ADDITEM':
          ud += "&Isrcs=%s" % qp(isrc)
      azheaders = self.defaultHeaders.copy()
      azheaders['X-Requested-With'] = 'XMLHttpRequest'
      url = VEVOAPI + ('/me/playlist/%s?token=%s' % (pid, token))
      html  = self.getRequest(url, ud , azheaders, rmethod = 'PUT')
      return


  def getAddonShows(self,url,ilist):
      token, uid = self.getAutho(getMe = True)
      pid = url[2:]
      func = url[:2]
      uheaders = self.defaultHeaders
      uheaders['X-Requested-With'] = 'XMLHttpRequest'
      if func == 'DP':
          url = VEVOAPI + ('/me/playlist/%s?token=%s') % (pid, token)
          html = self.getRequest(url, ' ', uheaders, rmethod='DELETE')
      elif func == 'RL':
          html = self.getRequest(VEVOAPI + ('/playlist/%s?token=%s' % (pid, token)))
          a = json.loads(html)
          oldname = a["name"]
          keyb = xbmc.Keyboard(oldname, 'Rename List')
          keyb.doModal()
          if (keyb.isConfirmed()):
              newname = keyb.getText()
              if len(newname) > 0: 
                  self.updateList(token = token, pid = pid, cmd = 'REN', name=newname)
      elif func == 'CP':
          keyb = xbmc.Keyboard('', 'Enter New List Name')
          keyb.doModal()
          if (keyb.isConfirmed()):
              text = keyb.getText()
              udata = 'name=%s&Isrcs=undefined' % qp(text)
              url = VEVOAPI + ('/me/playlists?token=%s' % token)
              self.getRequest(url, udata, uheaders)
      xbmcplugin.setContent(int(sys.argv[1]), 'files')
      html = self.getRequest(VEVOAPI + ('/user/%s/playlists?token=%s' % (uid,token)))
      a = json.loads(html)
      for b in a:
          thumb = b.get("thumbnailUrl")
          name = b["name"]
          url = 'GL' + VEVOAPI + '/playlist/%s?token=' % b["playlistId"]
          infoList ={}
          infoList['Title'] = name
          infoList['Plot'] = b.get("description")
          contextMenu = [('Delete Playlist','XBMC.Container.Refresh(%s?mode=GS&url=DP%s)' % (sys.argv[0], b["playlistId"])),
                         ('Rename Playlist','XBMC.Container.Refresh(%s?mode=GS&url=RL%s)' % (sys.argv[0], b["playlistId"]))]
          ilist = self.addMenuItem(name, 'GE', ilist, url, thumb, self.addonFanart, infoList, isFolder=True, cm=contextMenu)
      ilist = self.addMenuItem('[COLOR blue]Create New Playlist[/COLOR]', 'GS', ilist, 'CP' , self.addonIcon, self.addonFanart, None, isFolder=True)
      return(ilist)


  def getAddonEpisodes(self,url,ilist):
      self.defaultVidStream['width']  = 1920
      self.defaultVidStream['height'] = 1080
      xbmcplugin.setContent(int(sys.argv[1]), 'musicvideos')
      playList = None
      if url == 'Search':
          keyb = xbmc.Keyboard('', 'Search')
          keyb.doModal()
          if (keyb.isConfirmed()):
              url = 'https://apiv2.vevo.com/search?page=1&size=50&q=' + keyb.getText().replace(' ','+')
          else:
              return(ilist)
      elif url.startswith('GF'):
          url = 'https://apiv2.vevo.com/search?artistsLimit=1&page=1&size=50&skippedVideos=0&q=' + url[2:]
      elif url.startswith('GL'):
          url = url[2:]
          playList = re.compile('\/playlist\/(.+?)\?', re.DOTALL).search(url).group(1)
      if url.endswith('token='):
          url += self.getAutho()
      if not url.startswith('http'):
          url = 'https://apiv2.vevo.com' + url
      a = self.getAPI(url)
      nextUrl = None
      if type(a) is not list:
          nextUrl = a.get('paging')
          if nextUrl is not None:
              nextUrl = nextUrl.get('next')
      if type(a) is list:
          akeys = ['name', 'stream', 'thumbnailUrl']
      elif a.get('videos') is not None:
          a = a['videos']
          akeys = ['title', 'isrc', 'thumbnailUrl']
      elif a.get('nowPosts') is not None:
          a = a['nowPosts']
          akeys = ['name', 'isrc', 'image']
      for b in a:
          if b is None:
              continue
          url = b.get(akeys[1])
          if url is None:
              continue
          name = b[akeys[0]]
          thumb = b.get(akeys[2])
          infoList = {}
          infoList['Title'] = name
          infoList['Plot'] = b.get('description')
          artists = b.get('artists')
          infoList['Artist'] = [] 
          if artists is not None and artists != []:
              for artist in artists:
                  infoList['Artist'].append(artist['name'] + ' ')
          else:
              infoList['Artist'].append(xbmc.getInfoLabel('ListItem.Artist'))
          infoList['Year'] = b.get('year')
          infoList['duration'] = b.get('duration')
          infoList['mediatype']= 'musicvideo'
          if playList is not None:
              contextMenu = [('Remove From Playlist','XBMC.Container.Update(%s?mode=DF&url=DP%spid%s)' % (sys.argv[0],url, playList))]
          else:
              contextMenu = [('Add to Playlist','XBMC.RunPlugin(%s?mode=DF&url=AP%s)' % (sys.argv[0],url)),
                             ('Add To Library','XBMC.RunPlugin(%s?mode=DF&url=AL%s)' % (sys.argv[0],url))]
          ilist = self.addMenuItem(name,'GV', ilist, url, thumb, thumb, infoList, isFolder=False, cm=contextMenu)
      if nextUrl is not None:
          name = '[COLOR blue]Next Page[/COLOR]'
          ilist = self.addMenuItem(name, 'GE', ilist, nextUrl, self.addonIcon, self.addonFanart, infoList, isFolder=True)
      return(ilist)


  def getAddonMovies(self,url,ilist):
      xbmcplugin.setContent(int(sys.argv[1]), 'musicvideos')
      json_cmd= '{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtists", "params": { "limits": { "start" : 0 }, "properties": [ "thumbnail", "fanart", "genre" ], "sort": { "order": "ascending", "method": "artist", "ignorearticle": true }}, "id": 1}'
      jsonRespond = xbmc.executeJSONRPC(json_cmd)
      a = json.loads(jsonRespond)
      for b in a["result"]["artists"]:
          name = b["artist"].encode(UTF8)
          thumb = b.get("thumbnail", self.addonIcon)
          fanart = b.get("fanart", self.addonFanart)
          url = 'GF'+name.replace(' ','+')
          infoList = {}
          infoList['Title'] = name
          infoList['Plot'] = b.get('description')
          infoList['Artist'] = [name]
          infoList['Year'] = b.get('year')
          infoList['duration'] = b.get('duration')
          infoList['mediatype']= 'musicvideo'
          ilist = self.addMenuItem(name, 'GE', ilist, url, thumb, fanart, infoList, isFolder=True)
      return(ilist)


  def doFunction(self, url):
      func = url[0:2]
      url = url[2:]
      if func == 'DP':
          isrc, pid = url.split('pid',1)
          self.updateList(pid = pid, token = None, cmd = 'DELITEM', isrc = isrc)
      elif func == 'AP':
          token, uid = self.getAutho(getMe = True)
          html = self.getRequest(VEVOAPI + ('/user/%s/playlists?token=%s' % (uid,token)))
          a = json.loads(html)
          ilist=[]
          nlist=[]
          for b in a:
              nlist.append(b['name'])
              ilist.append(b['playlistId'])
          dialog = xbmcgui.Dialog()
          choice = dialog.select('Choose a playlist', nlist)
          pid = ilist[choice]
          self.updateList(pid = pid, token = token, cmd = 'ADDITEM', isrc = url)
      elif func == 'AL':
          artist = xbmc.getInfoLabel('ListItem.Artist').split('/',1)[0]
          artist = artist.replace(':','').replace('-','').replace("'",'').replace('"','').replace('.','')
          title = xbmc.getInfoLabel('ListItem.Title').split('(',1)[0]
          title = title.replace(':','').replace('-','').replace("'",'').replace('"','').replace('/','').replace('.','')
          name = artist.strip() + ' - ' + title.strip()
          profile = self.addon.getAddonInfo('profile').decode(UTF8)
          videosDir  = xbmc.translatePath(os.path.join(profile,'Videos'))
          videoDir  = xbmc.translatePath(os.path.join(videosDir, name))
          if not os.path.isdir(videoDir):
             os.makedirs(videoDir)
          strmFile = xbmc.translatePath(os.path.join(videoDir, name+'.strm'))
          with open(strmFile, 'w') as outfile:
              outfile.write('%s?mode=GV&url=%s' %(sys.argv[0], url))
          json_cmd = '{"jsonrpc":"2.0","method":"VideoLibrary.Scan", "params": {"directory":"%s/"},"id":1}' % videoDir.replace('\\','/')
          jsonRespond = xbmc.executeJSONRPC(json_cmd)


  def getAddonVideo(self,url):
      if not '.m3u8' in url:
          url = ('https://apiv2.vevo.com/video/%s/streams/hls?token=%s' % (url, self.getAutho()))
          a = self.getAPI(url)
          for b in a:
              if b["version"] == 2:
                  url = b['url']
                  break
      liz = xbmcgui.ListItem(path = url)
      infoList ={}
      infoList['Artist'] = []
      infoList['Artist'].append(xbmc.getInfoLabel('ListItem.Artist'))
      infoList['Title'] = xbmc.getInfoLabel('ListItem.Title')
      infoList['Year'] = xbmc.getInfoLabel('ListItem.Year')
      infoList['Plot'] = xbmc.getInfoLabel('ListItem.Plot')
      infoList['Studio'] = xbmc.getInfoLabel('ListItem.Studio')
      infoList['Album'] = xbmc.getInfoLabel('ListItem.Album')
      infoList['Duration'] = xbmc.getInfoLabel('ListItem.Duration')
      infoList['mediatype']= 'musicvideo'
      liz.setInfo('video', infoList)
      xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)
