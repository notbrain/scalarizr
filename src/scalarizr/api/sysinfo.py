'''
Created on Nov 25, 2011

@author: marat

Pluggable API to get system information similar to SNMP, Facter(puppet), Ohai(chef)
'''

from __future__ import with_statement

import os
import logging
import sys
import re

from scalarizr import rpc
from scalarizr.util import system2, dns, disttool

LOG = logging.getLogger(__name__)

class SysInfoAPI(object):

	_HOSTNAME = '/etc/hostname'
	_DISKSTATS = '/proc/diskstats'
	_PYTHON = ['/usr/bin/', '/usr/local/bin/']
	_CPUINFO = '/proc/cpuinfo'
	_NETSTAT = '/proc/net/dev'


	def __init__(self):
		self._diskstats = None
		self._cpuinfo = None
		self._netstat = None


	def _check_python_path(self, path):
		py_name = os.path.basename(path)
		if py_name.lower().startswith('python') and len(py_name) >= 6:
			#filtering name as `python2.7-config` and other analogy
			if not re.search('[^ \-.+0-9]', py_name[6:]):
				return True


	def _readvar(self, PATH, test_value):
		if not test_value:
				with open(PATH, "r") as fp:
					lines = fp.readlines()
		else:
			lines = test_value
		return lines 


	def add_extension(self, extension):
		'''
		@param extension: Object with some callables to extend SysInfo public interface
		@type extension: object
		@note: Duplicates resolves by overriding old function with a new one
		'''
		for name in dir(extension):
			attr = getattr(extension, name)
			if not name.startswith('_') and callable(attr):
				if hasattr(self, name):
					LOG.warn('Duplicate attribute %s. Overriding %s with %s', 
							name, getattr(self, name), attr)
				setattr(self, name, attr)


	@rpc.service_method
	def fqdn(self, fqdn=None):
		'''
		Get/Update host FQDN
		@param fqdn: Fully Qualified Domain Name to set for this host
		@rtype: str: Current FQDN
		'''
		if fqdn:
			# changing permanent hostname
			try:
				with open(self._HOSTNAME, 'r') as fp:
					old_hn = fp.readline().strip()
				with open(self._HOSTNAME, 'w+') as fp:
					fp.write('%s\n' % fqdn)
			except:
				raise Exception, 'Can`t write file `%s`.' % \
					self._HOSTNAME, sys.exc_info()[2]
					
			# changing runtime hostname
			system2(('hostname', '%s' % fqdn))
			
			# changing hostname in hosts file
			if old_hn:
				hosts = dns.HostsFile()
				hosts._reload()
				if hosts._hosts:
					for index in range(0, len(hosts._hosts)):
						if isinstance(hosts._hosts[index], dict) and \
										hosts._hosts[index]['hostname'] == old_hn:
							hosts._hosts[index]['hostname'] = fqdn
					hosts._flush()
					
			return fqdn
		
		else:
			with open(self._HOSTNAME, 'r') as fp:
				return fp.readline().strip()


	@rpc.service_method
	def block_devices(self):
		'''
		Block devices list
		@return: List of block devices including ramX and loopX
		@rtype: list 
		'''
		lines = self._readvar(self._DISKSTATS, self._diskstats)
		devicelist = []
		for value in lines:
			devicelist.append(value.split()[2])
		return devicelist


	@rpc.service_method
	def uname(self):
		'''
		Return system information
		@rtype: dict
		
		Sample:
		{'kernel_name': 'Linux',
		'kernel_release': '2.6.41.10-3.fc15.x86_64',
		'kernel_version': '#1 SMP Mon Jan 23 15:46:37 UTC 2012',
		'nodename': 'marat.office.webta',			
		'machine': 'x86_64',
		'processor': 'x86_64',
		'hardware_platform': 'x86_64'}
		'''
		
		uname = disttool.uname()
		return {
			'kernel_name': uname[0],
			'nodename': uname[1],
			'kernel_release': uname[2],
			'kernel_version': uname[3],#' '.join(uname[3:len(uname)-4]),
			'machine': uname[4],
			'processor': uname[5],
			'hardware_platform': disttool.arch()#uname[-2]
		}


	@rpc.service_method
	def dist(self):
		'''
		Return Linux distribution information 
		@rtype: dict
		
		Sample:
		{'id': 'Fedora',
		'release': '15',
		'codename': 'Lovelock',
		'description': 'Fedora release 15 (Lovelock)'}
		'''
		
		linux_dist = disttool.linux_dist()
		return {
			'id': linux_dist[0],
			'release': linux_dist[1],
			'codename': linux_dist[2],
			'description': '%s %s (%s)' % (linux_dist[0], linux_dist[1], linux_dist[2])
		}


	@rpc.service_method
	def pythons(self):
		'''
		Return installed Python versions
		@rtype: list
		
		Sample:
		['2.7.2+', '3.2.2']
		'''

		res = []
		for path in self._PATH:
			# @fixme use glob module: glob.glob('/usr/bin/python[0-9].[0-9]')
			out = system2(('find', path, '-name', 'python*'))[0]
			if '\n' in out:
				out = out.split('\n')
				for lp in out:
					if self._check_python_path(lp):
						res.append(lp)
			elif out:
				if self._check_python_path(out.strip()):
						res.append(out.strip())

		#check full correct version
		LOG.debug('SysInfoAPI.pythons: variants of python bin paths: `%s`. They`ll be \
				checking now.', res)
		result = []
		for pypath in res:
			(out, err, rc) = system2((pypath, '-V'))
			if rc == 0:
				result.append((out or err).strip())
			else: 
				LOG.debug('SysInfoAPI.pythons: can`t execute `%s -V`, details: %s',\
						pypath, err or out)
		return map(lambda x: x[6:].strip(), list(set(result)))


	@rpc.service_method
	def cpu_info(self):
		'''
		Return CPU info from /proc/cpuinfo
		@rtype: list
		'''

		lines = self._readvar(self._CPUINFO, self._cpuinfo)
		res = []
		index = 0
		while index < len(lines):
			core = {}
			while index < len(lines):
				if ':' in lines[index]:
					tmp = map(lambda x: x.strip(), lines[index].split(':'))
					(key, value) = list(tmp) if len(list(tmp)) == 2 else (tmp, None)
					if key not in core.keys():
						core.update({key:value})
					else:
						break
				index += 1
			res.append(core)
		return res


	@rpc.service_method
	def load_average(self):
		'''
		Return Load average (1, 5, 15) in 3 items list  
		'''

		return os.getloadavg()


	@rpc.service_method
	def disk_stats(self):
		'''
		Disks I/O statistics
		@rtype: [{
			<device>: Linux device name
			<read>: {
				<num>: total number of reads completed successfully
				<sectors>: total number of sectors read successfully
				<bytes>: total number of bytes read successfully
			}
			<write>: {
				<num>: total number of writes completed successfully
				<sectors>: total number of sectors written successfully
				<bytes>: total number of bytes written successfully
			}
		}, ...]
		'''
		
		#http://www.kernel.org/doc/Documentation/iostats.txt
		lines = self._readvar(self._DISKSTATS, self._diskstats)
		devicelist = []
		for value in lines:
			params = value.split()[2:]
			device = params[0]
			for i in range(1, len(params)-1):
				params[i] = int(params[i])
			if len(params) == 12:
				read = {'num': params[1], 'sectors': params[3], 'bytes': params[3]*512}
				write = {'num': params[5], 'sectors': params[7], 'bytes': params[7]*512}
			elif len(params) == 5:
				read = {'num': params[1], 'sectors': params[2], 'bytes': params[2]*512}
				write = {'num': params[3], 'sectors': params[4], 'bytes': params[4]*512}
			else:
				raise Exception, 'number of column in %s is unexpected. Count of column =\
					 %s' % (self._DISKSTATS, len(params)+2)
			devicelist.append({'device': device, 'write': write, 'read': read})
		return devicelist


	@rpc.service_method
	def net_stats(self):
		'''
		Network I/O statistics
		@rtype: [{
			<iface>: Network interface name
			<receive>: {
				<bytes>: total received bytes
				<packets>: total received packets
				<errors>: total receive errors
			}
			<transmit>: {
				<bytes>: total transmitted bytes
				<packets>: total transmitted packets
				<errors>: total transmit errors
			}
		}, ...]
		'''
		
		lines = self._readvar(self._NETSTAT, self._netstat)
		res = []
		for row in lines:
			if ':' not in row:
				continue
			row = row.split(':')
			iface = row.pop(0).strip()
			columns = map(lambda x: x.strip(), row[0].split())
			res.append({'iface': iface,
				'receive': {'bytes': columns[0], 'packets': columns[1], 'errors': columns[2]},
				'transmit': {'bytes': columns[8], 'packets': columns[9], 'errors': columns[10]},
				})
		return res