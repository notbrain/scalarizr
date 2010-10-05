'''
Created on Sep 27, 2010

@author: marat
'''
from scalarizr.bus import bus
from scalarizr.queryenv import ScalingMetric
from scalarizr.util import read_shebang
import signal
import os, time, logging
from subprocess import Popen, PIPE
from scalarizr.util import system, kill_childs
from threading import Thread
from Queue import Queue, Empty

# SNMP imports
from pysnmp.smi.builder import MibBuilder
from scalarizr.config import ScalarizrState

(scalr, mtxTable, mtxEntry, mtxIndex, mtxId, mtxName, mtxValue, mtxError) = mibBuilder.importSymbols(
		'SCALING-METRICS-MIB', 
		'scalr', 'mtxTable', 'mtxEntry', 'mtxIndex', 'mtxId', 'mtxName', 'mtxValue', 'mtxError')

(MibTable, MibScalarInstance) = mibBuilder.importSymbols('SNMPv2-SMI','MibTable', 'MibScalarInstance')


_metrics = None
_metrics_timestamp = None


class MtxTableImpl(MibTable):

	EXEC_TIMEOUT = 3
	'''
	Executing timeout for script when obtain metric with 'execute' method 
	'''

	_metrics = None
	_metrics_timestamp = None
	
	def getNextNode(self, name, idx):
		mibBuilder.lastBuildId += 1
		
		# Clean old values
		for k in mibBuilder.mibSymbols['SCALING-METRICS-MIB'].keys():
			if k.startswith('mtxIndex') or k.startswith('mtxId') or k.startswith('mtxName') or k.startswith('mtxValue') or k.startswith('mtxEntry') or k.startswith('mtxError'):
				del mibBuilder.mibSymbols['SCALING-METRICS-MIB'][k]
				
		# Update with new values
		mibBuilder.mibSymbols['SCALING-METRICS-MIB'].update(values())
		return MibTable.getNextNode(self, name, idx)


MtxTableInst = MtxTableImpl(mtxTable.getName())

def values():
	global _metrics
	global _metrics_timestamp
	
	queryenv = bus.queryenv_service
	cnf = bus.cnf
	
	# Obtain scaling metrics from Scalr. Cache result for 30 minutes
	now = time.time()
	if not _metrics or now - _metrics_timestamp > 1800:
		if cnf.state != ScalarizrState.IMPORTING: 
			_metrics = queryenv.get_scaling_metrics()
			_metrics_timestamp = now
		else:
			return dict()

	# TODO: investigate how efficiently will be do calculations in parallel
	
	ret = dict()
	
	ret.update({
		'mtxTable' : MtxTableInst,
		'scalr'    : scalr,
		'mtxIndex' : mtxIndex,
		'mtxId'    : mtxId,
		'mtxName'  : mtxName,
		'mtxValue' : mtxValue,
		'mtxError' : mtxError,
		'mtxEntry' : mtxEntry
		})
	
	index = 0
	queue = Queue()
	for metric in _metrics:
		queue.put(metric)
	
	workers = []
	for i in range(len(_metrics)):
		index += 1
		worker = Thread(target = update_metric, name = 'Worker-%s' % i, args = (queue, index, ret))
		worker.start()
		workers.append(worker)
		
	for worker in workers:
		worker.join()
				
	return ret

def _get_execute( metric):
	if not os.access(metric.path, os.X_OK):
		raise BaseException("File is not executable: '%s'" % metric.path)
	
	proc = Popen(metric.path, stdout=PIPE, stderr=PIPE, close_fds=True)
	start_time = time.time()
	while time.time() - start_time < MtxTableImpl.EXEC_TIMEOUT:
		if proc.poll() is None:
			time.sleep(0.1)
		else:
			break
	else:
		if hasattr(proc, 'kill'):
			# python >= 2.6
			kill_childs(proc.pid)
			proc.terminate()
		else:
			kill_childs(proc.pid)
			os.kill(proc.pid, signal.SIGTERM)
		raise BaseException('Timeouted')
							
	stdout, stderr = proc.communicate()
	
	if proc.returncode > 0:
		raise BaseException(stderr if stderr else 'exitcode: %d' % proc.returncode)
	
	return stdout

def _get_read( metric):
	if not os.access(metric.path, os.R_OK):
		raise BaseException("File is not readable: '%s'" % metric.path)
	
	file = None
	try:
		file = open(metric.path, 'r')
		value = file.readline()
	finally:
		if file:
			file.close()
		del file
	
	return value

def update_metric(queue, index, ret):
	error = ''
	value = 0.0
	try:
		metric = queue.get(False)
	except Empty:
		return
			
	try:
		# Retrieve metric value
		if ScalingMetric.RetriveMethod.EXECUTE == metric.retrieve_method:
			value = _get_execute(metric)
		elif ScalingMetric.RetriveMethod.READ  == metric.retrieve_method:
			value = _get_read(metric)
		else:
			raise BaseException('Unknown retrieve method %s' % metric.retrieve_method)
		
		# Convert value to float
		try:
			value = float(value)
		except ValueError, e:
			raise ValueError("Cannot convert value '%s' to float" % value)
			
	except (BaseException, Exception), e:
		value = 0.0
		error = str(e)[0:255]

		
	# Export MibTableRow

	ret.update({
		'mtxIndex%s' % index : MibScalarInstance(mtxIndex.getName(), (index,), mtxIndex.getSyntax().clone(
			index
		)),
		'mtxId%s' % index : MibScalarInstance(mtxId.getName(), (index,), mtxId.getSyntax().clone(
			int(metric.id)
		)),
		'mtxName%s' % index : MibScalarInstance(mtxName.getName(), (index,), mtxName.getSyntax().clone(
			metric.name
		)),
		'mtxValue%s' % index : MibScalarInstance(mtxValue.getName(), (index,), mtxValue.getSyntax().clone(
			'%.7f' % value
		)),
		'mtxError%s' % index : MibScalarInstance(mtxError.getName(), (index,), mtxError.getSyntax().clone(
			error
		))
	})
	

mibBuilder.mibSymbols["SCALING-METRICS-MIB"] = values()