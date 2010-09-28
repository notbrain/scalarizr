import os, re
import logging
import threading
import weakref
import time
import sys
import socket


class UtilError(BaseException):
	pass


class LocalObject:
	def __init__(self, creator, pool_size=10):
		self._logger = logging.getLogger(__name__)
		self._creator = creator		
		self._object = threading.local()
		
		self._all_conns = set()
		self.size = pool_size
	
	def do_create(self):
		return self._creator()
	
	def get(self):
		try:
			o = self._object.current
			if o():
				return o()
			else:
				self._logger.debug("Current weakref is empty")
		except AttributeError, e:
			self._logger.debug("Caught: %s", e)
		
		self._logger.debug("Creating new object...")
		o = self.do_create()
		self._logger.debug("Created %s", o)
		self._object.current = weakref.ref(o)
		self._logger.debug("Added weakref %s", self._object.current)
		self._all_conns.add(o)
		if len(self._all_conns) > self.size:
			self.cleanup()
		return o
	
	def cleanup(self):
		for conn in list(self._all_conns):
			self._all_conns.discard(conn)
			if len(self._all_conns) <= self.size:
				return
	
class SqliteLocalObject(LocalObject):
	def do_create(self):
		return _SqliteConnection(self, self._creator)
	
class _SqliteConnection(object):
	_conn = None
	#_lo = None
	_creator = None
	
	def __init__(self, lo, creator):
		#self._lo = lo
		self._creator = creator
	
	def get_connection(self):
		if not self._conn:
			self._conn = self._creator()
		return self._conn
	
def cached(f, cache={}):
	'''
	Decorator
	'''
	def g(*args, **kwargs):
		key = (f, tuple(args), frozenset(kwargs.items()))
		if key not in cache:
			cache[key] = f(*args, **kwargs)
		return cache[key]
	return g	

def firstmatched(function, sequence, default=None):
	for s in sequence:
		if function(s):
			return s
			break
	else:
		return default	






def daemonize():
	# First fork
	pid = os.fork()
	if pid > 0:
		sys.exit(0) 	
	
	os.chdir("/")
	os.setsid()
	os.umask(0)
	
	# Second fork
	pid = os.fork()
	if pid > 0:
		sys.exit(0)
		
	# Redirect standard file descriptors
	sys.stdout.flush()
	sys.stderr.flush()
	si = file(os.devnull, 'r')
	so = file(os.devnull, 'a+')
	se = file(os.devnull, 'a+', 0)
	os.dup2(si.fileno(), sys.stdin.fileno())
	os.dup2(so.fileno(), sys.stdout.fileno())
	os.dup2(se.fileno(), sys.stderr.fileno())
	
	
def system(args, shell=True):
	import subprocess
	logger = logging.getLogger(__name__)
	logger.debug("system: %s", args)
	p = subprocess.Popen(args, shell=shell, env={'LANG' : 'en_US'}, 
			stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out, err = p.communicate()
	if out:
		logger.debug("stdout: " + out)
		#print "stdout: " + out
	if err:
		logger.warning("stderr: " + err)
		#print "stderr: " + err
	return out, err, p.returncode


def wait_until(target, args=None, sleep=5, logger=None):
	args = args or ()
	while not target(*args):
		if logger:
			logger.debug("Wait %d seconds before the next attempt", sleep)
		time.sleep(sleep)


def xml_strip(el):
	for child in list(el.childNodes):
		if child.nodeType==child.TEXT_NODE and child.nodeValue.strip() == '':
			el.removeChild(child)
		else:
			xml_strip(child)
	return el	

def url_replace_hostname(url, newhostname):
	import urlparse	
	r = url if isinstance(url, tuple) else urlparse.urlparse(url)
	r2 = list(r)
	r2[1] = newhostname
	if r.port:
		r2[1] += ":" + str(r.port)
	return urlparse.urlunparse(r2)
	


def read_shebang(path=None, script=None):
	if path:
		file = first_line = None
		try:
			file = open(path, 'r')
			first_line = file.readline()
		finally:
			if file:
				file.close()
	elif script:
		if not isinstance(script, basestring):
			raise ValueError('argument `script` should be a basestring subclass')
		eol_index = script.find(os.linesep)
		first_line = eol_index != -1 and script[0:eol_index] or script
	else:
		raise ValueError('one of arguments `path` or `script` should be passed')

	shebang = re.search(re.compile('^#!(\S+)\s*'), first_line)
	if shebang:
		return shebang.group(1)
	return None

def parse_size(size):
	"""
	Read string like 10K, 12M, 1014B and return size in bytes
	"""
	ret = str(size)
	dim = ret[-1]		
	ret = float(ret[0:-1])
	if dim.lower() == "b":
		pass		
	elif dim.lower() == "k":
		ret *= 1024
	elif dim.lower() == "m":
		ret *= 1048576	
	
	return ret
	
def format_size(size, precision=2):
	"""
	Format size in Bytes, KBytes and MBytes
	"""
	ret = float(size)
	dim = "B"
	if ret > 1000:
		ret = ret/1000
		dim = "K"
	if ret > 1000:
		ret = ret/1000
		dim = "M"
		
	s = "%."+str(precision)+"f%s"
	return s % (ret, dim)	

def backup_file(filename):
	import shutil
	logger = logging.getLogger(__name__)
	max_backups = 50
	
	for i in range(0, max_backups):
		bkname = '%s.bak.%s' % (filename, i)		
		if not os.path.exists(bkname):
			logger.debug('Backuping %s to %s', filename, bkname)
			shutil.copy(filename, bkname)
			return bkname
	raise UtilError("Max backups limit %d exceed for file %s" % (max_backups, filename))


"""
def timethis(what):
	try:
		import time
	except ImportError:
		import timemodule as time
	from contextlib import contextmanager	
	
	@contextmanager
	def benchmark():
		start = time.time()
		yield
		end = time.time()
		print("%s : %0.3f seconds" % (what, end-start))
	if hasattr(what,"__call__"):
		def timed(*args,**kwargs):
			with benchmark():
				return what(*args,**kwargs)
		return timed
	else:
		return benchmark()
"""

def init_tests():
	logging.basicConfig(
			format="%(asctime)s - %(levelname)s - %(name)s - %(message)s", 
			stream=sys.stdout, 
			level=logging.DEBUG)
	import scalarizr as szr
	from scalarizr.bus import bus
	bus.etc_path = os.path.realpath(os.path.dirname(__file__) + "/../../../test/resources/etc")
	szr._init()
	bus.cnf.bootstrap()

def get_free_devname():
	dev_list = os.listdir('/dev')
	for letter in map(chr, range(111, 123)):
		device = 'sd'+letter
		if not device in dev_list:
			return '/dev/'+device