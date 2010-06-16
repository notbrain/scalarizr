'''
Created on May 10, 2010

@author: marat
'''

from scalarizr.util import disttool, system
import re
import os

class FstoolError(BaseException):
	NO_FS = -666
	CANNOT_MOUNT = -667
	
	message = None
	code = None
	
	def __init__(self, *args):
		BaseException.__init__(self, *args)
		self.message = args[0]
		try:
			self.code = args[1]
		except IndexError:
			pass


class Fstab:
	"""
	Wrapper over /etc/fstab
	"""
	LOCATION = None
	filename = None	
	_entries = None
	_re = None
	
	def __init__(self, filename=None):
		self.filename = filename if not filename is None else self.LOCATION
		self._entries = None
		self._re = re.compile("^(\\S+)\\s+(\\S+)\\s+(\\S+)\\s+(\\S+).*$")
		
	def list_entries(self, rescan=False):
		if not self._entries or rescan:
			self._entries = []
			f = open(self.filename, "r")
			for line in f:
				if line[0:1] == "#":
					continue
				m = self._re.match(line)
				if m:
					self._entries.append(TabEntry(
						m.group(1), m.group(2), m.group(3), m.group(4), line.strip()
					))
			f.close()
			
		return list(self._entries)
	
	def append(self, entry):
		line = "\n" + "\t".join([entry.device, entry.mpoint, entry.fstype, entry.options])
		try:
			f = open(self.filename, "a")
			f.write(line)
		finally:
			f.close()
			
	def contains(self, devname=None, mpoint=None, rescan=False):
		return any((mpoint and entry.mpoint == mpoint) or (devname and entry.device) \
				for entry in self.list_entries(rescan))
		
	def find(self, devname=None, mpoint=None, fstype=None, rescan=False):
		ret = list(entry for entry in self.list_entries(rescan) if \
				(devname and entry.device == devname) or \
				(mpoint and entry.mpoint == mpoint) or \
				(fstype and entry.fstype == fstype))
		return ret
	

class Mtab(Fstab):
	"""
	Wrapper over /etc/mtab
	"""
	LOCAL_FS_TYPES = None	

		
class TabEntry(object):
	device = None
	mpoint = None
	fstype = None
	options = None	
	value = None
	
	def __init__(self, device, mpoint, fstype, options, value=None):
		self.device = device
		self.mpoint = mpoint
		self.fstype = fstype
		self.options = options		
		self.value = value

		
if disttool.is_linux():
	Fstab.LOCATION = "/etc/fstab"	
	Mtab.LOCATION = "/etc/mtab"
	Mtab.LOCAL_FS_TYPES = ('ext2', 'ext3', 'xfs', 'jfs', 'reiserfs', 'tmpfs')
	
elif disttool.is_sun():
	Fstab.LOCATION = "/etc/vfstab"	
	Mtab.LOCATION = "/etc/mnttab"
	Mtab.LOCAL_FS_TYPES = ('ext2', 'ext3', 'xfs', 'jfs', 'reiserfs', 'tmpfs', 
		'ufs', 'sharefs', 'dev', 'devfs', 'ctfs', 'mntfs',
		'proc', 'lofs',   'objfs', 'fd', 'autofs')
	

def mount (device, mpoint, options=()):
	if not os.path.exists(mpoint):
		os.makedirs(mpoint)
	
	options = " ".join(options) 
	out = system("mount %(options)s %(device)s %(mpoint)s 2>&1" % vars())[0]
	if out.find("you must specify the filesystem mkfstype") != -1:
		raise FstoolError("No filesystem found on device '%s'" % (device), FstoolError.NO_FS)
	
	mtab = Mtab()
	if not mtab.contains(device):
		raise FstoolError("Cannot mount device '%s'. %s" % (device, out), FstoolError.CANNOT_MOUNT)

def umount():
	pass

def mkfs():
	pass