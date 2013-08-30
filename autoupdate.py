#!/usr/bin/env python
# coding:utf-8
# autoupdate.py
# Author: Wang Wei Qiang <wwqgtxx@gmail.com>


import sys
import os
import glob

sys.path += glob.glob('%s/*.egg' % os.path.dirname(os.path.abspath(__file__)))

try:
	if 'threading' in sys.modules:
		del sys.modules['threading']
	import gevent
	import gevent.socket
	import gevent.monkey
	gevent.monkey.patch_all()
except (ImportError, SystemError):
	gevent = None
try:
	import OpenSSL
except ImportError:
	OpenSSL = None

from simpleproxy import LocalProxyServer
from simpleproxy import server
from simpleproxy import logging
from simpleproxy import common as proxyconfig
from common import sysconfig as common
from common import FileUtil
from common import Config
from common import __config__
from common import __file__
from common import Common
from makehash import makehash
from sign import verify
from sign import sign

import os
import sys
import re
import ConfigParser
import hashlib
import thread
import urllib2
import random



class Updater(object):
	def __init__(self,serverurl,old_file_sha1_ini,dir):
		proxies = {'http':'%s:%s'%('127.0.0.1', proxyconfig.LISTEN_PORT),'https':'%s:%s'%('127.0.0.1', proxyconfig.LISTEN_PORT)}
		self.opener = urllib2.build_opener(urllib2.ProxyHandler(proxies))
		self.server = str(serverurl)
		self.old_file_sha1_ini = old_file_sha1_ini
		self.dir = dir
	def netopen(self,filename):
		print 'Getting	'+filename
		file = self.opener.open(self.server+filename).read()
		print 'Get	'+filename+'				OK!'
		return file
	def getfile(self,filename):
		while 1:
			try:
				file = self.netopen(filename)
				return file
			except Exception as e:
				print e
				return
	def writefile(self,filename,sha1v):
		file = self.getfile(filename)
		path = self.dir+filename
		if os.path.isfile(path):
			input = FileUtil.open(path,"r")
			oldfile = input.read()
			input.close()
		else:
			oldfile = None
		output = FileUtil.open(path,"wb")
		output.write(file)
		print 'Update	'+filename+'				OK!'
		output.close()
		input = FileUtil.open(path,"rb")
		sha1vv = FileUtil.get_file_sha1(input)
		#print sha1v.strip()
		#print sha1vv.strip()
		input.close()
		if sha1v.strip()==sha1vv.strip() :
			print 'Verify	'+filename+'				OK!'
		else:
			print 'Verify	'+filename+'				Fail!'
			if oldfile:
				output = FileUtil.open(path,"wb")
				output.write(oldfile)
				output.close()
			print 'Recover	'+filename+'				OK!'
		if filename.strip() == '/autoupdate.ini'.strip():
			newconfig = Config(__config__)
			newconfig.writeconfig('autoupdate', 'server',common.AUTOUPDATE_SERVER_STR)
			print 'ReWrite	/autoupdate.ini				OK!'
			common.reloadini()
			print 'ReLoad	/autoupdate.ini				OK!'
	def getnewsha1(self,path,oldsha1):
		output = FileUtil.open(path,"wb")
		output.write(self.netopen('/'+common.CONFIG_SHA1)) 
		output.close()
		input = FileUtil.open(path,"r")
		tmp2 = input.read()
		input.close()
		hash = self.netopen('/'+common.CONFIG_SIGN)
		print 'Verifing Hash Table.....'
		ok = verify(tmp2,hash)
		if not ok:
			print 'Verify Failed!'
			sys.exit()
		print 'Verify Successful1!'

	def update(self):
		print 'Checking for new update...'
		versionfile = self.netopen('/'+common.CONFIG_VERSIONFILE)
		print "Show Server Version Message:"
		print versionfile
		oldsha1 = self.old_file_sha1_ini
		path = common.CONFIG_SHA1+'.tmp'
		FileUtil.if_has_file_remove(path)
		self.getnewsha1(path,oldsha1)
		newsha1 = Config(path)
		for path, sha1v in newsha1.getsection('FILE_SHA1'):
			if not (sha1v == oldsha1.getconfig('FILE_SHA1',path)):
				oldpath = path
				path = path.replace('$path$','')
				path = path.replace('\\','/')
				self.writefile(path,sha1v)
		FileUtil.if_has_file_remove(path)



def main():
	dir = FileUtil.cur_file_dir()
	os.chdir(dir)
	sys.stdout.write(common.info())
	sys.stdout.write(proxyconfig.info())
	thread.start_new_thread(server.serve_forever, tuple())
	sha1 = makehash(dir)
	updater = Updater(common.AUTOUPDATE_SERVER[0],sha1,dir)
	updater.update()

	#for path, sha1v in sha1.getsection('FILE_SHA1'):
		#newpath = path.replace('$path$',dir)
		#print newpath + ' = ' + sha1v

if __name__ == '__main__':
	main()