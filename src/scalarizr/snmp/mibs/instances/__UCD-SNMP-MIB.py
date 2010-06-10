from sys import version
from time import time
from pysnmp import majorVersionId
import os, re
from pyasn1.type import constraint, namedval
( Integer, OctetString, ) = mibBuilder.importSymbols("ASN1", "Integer", "OctetString")
( DisplayString,) = mibBuilder.importSymbols("SNMPv2-TC", "DisplayString")



( MibScalarInstance,
  TimeTicks,
  Integer32,
  Counter32,
  MibTableRow,
  MibTableColumn,
  Opaque) = mibBuilder.importSymbols(
    'SNMPv2-SMI',
    'MibScalarInstance',
    'TimeTicks',
    'Integer32',
    'Counter32',
    'MibTableRow',
    'MibTableColumn',
    'Opaque'
	)

( 
 memory,
  memTotalSwap,
  memAvailSwap,
  memTotalReal,
  memTotalFree,
  memShared,
  memBuffer,
  memCached,
  ssCpuRawUser,
  ssCpuRawNice,
  ssCpuRawIdle,
  ssCpuRawSystem,
  systemStats,
  laTable,
  laEntry,
  laIndex,
  laNames,
  laLoad, 
  laConfig, 
  laLoadInt, 
  laLoadFloat, 
  laErrorFlag,
  laErrMessage
     ) = mibBuilder.importSymbols(
    'UCD-SNMP-MIB',
    'memory',
    'memTotalSwap',
    'memAvailSwap',
    'memTotalReal',
    'memTotalFree',
    'memShared',
    'memBuffer',
    'memCached',
    'ssCpuRawUser',
    'ssCpuRawNice',
    'ssCpuRawIdle',
    'ssCpuRawSystem',
    'systemStats',
      'laTable',
	  'laEntry',
	  'laIndex',
	  'laNames',
	  'laLoad', 
	  'laConfig', 
	  'laLoadInt', 
	  'laLoadFloat', 
	  'laErrorFlag',
	  'laErrMessage'
    )

#class Float(Opaque):
#    subtypeSpec = Opaque.subtypeSpec+constraint.ValueSizeConstraint(7,7)
#    fixedLength = 7
#    pass

class UCDErrorFlag(Integer):
    subtypeSpec = Integer.subtypeSpec+constraint.SingleValueConstraint(0,1,)
    namedValues = namedval.NamedValues(("noError", 0), ("error", 1), )
    pass
   
class MemTotalReal(Integer32):
	def clone(self, **kwargs):
		if kwargs.get('value') is None:
			kwargs['value'] = _get_memory_value('MemTotal')
			return apply(Integer32.clone, [self], kwargs)
		
class MemTotalSwap(Integer32):
	def clone(self, **kwargs):
		if kwargs.get('value') is None:
			kwargs['value'] = _get_memory_value('SwapTotal')
			return apply(Integer32.clone, [self], kwargs)

class MemAvailSwap(Integer32):
	def clone(self, **kwargs):
		if kwargs.get('value') is None:
			kwargs['value'] = _get_memory_value('SwapFree')
			return apply(Integer32.clone, [self], kwargs)

class MemTotalFree(Integer32):
	def clone(self, **kwargs):
		if kwargs.get('value') is None:
			kwargs['value'] = _get_memory_value('MemFree')
			return apply(Integer32.clone, [self], kwargs)

class MemShared(Integer32):
	def clone(self, **kwargs):
		if kwargs.get('value') is None:
			kwargs['value'] = _get_memory_value('Shmem')
			return apply(Integer32.clone, [self], kwargs)

class MemBuffer(Integer32):
	def clone(self, **kwargs):
		if kwargs.get('value') is None:
			kwargs['value'] = _get_memory_value('Buffers')
			return apply(Integer32.clone, [self], kwargs)
		
class MemCached(Integer32):
	def clone(self, **kwargs):
		if kwargs.get('value') is None:
			kwargs['value'] = _get_memory_value('^Cached:')
			return apply(Integer32.clone, [self], kwargs)

class SsCpuRawUser(Counter32):
	def clone(self, **kwargs):
		if kwargs.get('value') is None:
			kwargs['value'] = _get_cpu_value('user')
			return apply(Counter32.clone, [self], kwargs)

class SsCpuRawNice(Counter32):
	def clone(self, **kwargs):
		if kwargs.get('value') is None:
			kwargs['value'] = _get_cpu_value('nice')
			return apply(Counter32.clone, [self], kwargs)

class SsCpuRawIdle(Counter32):
	def clone(self, **kwargs):
		if kwargs.get('value') is None:
			kwargs['value'] = _get_cpu_value('idle')
			return apply(Counter32.clone, [self], kwargs)

class SsCpuRawSystem(Counter32):
	def clone(self, **kwargs):
		if kwargs.get('value') is None:
			kwargs['value'] = _get_cpu_value('system')
			return apply(Counter32.clone, [self], kwargs)



def _get_memory_value(key=None):
	file = open('/proc/meminfo', "r")
	meminfo = file.readlines()
	file.close()
	for line in meminfo:
		if re.match(key, line) :
			return int(line.split()[1])
		
def _get_cpu_value(key=None):
	cpuvalues = {'user' : 1, 'nice' : 2, 'system' : 3, 'idle' : 4}
	if  cpuvalues.has_key(key):
		file = open('/proc/stat', "r")
		cpuinfo = file.readline()
		file.close()
		return int(cpuinfo.split()[cpuvalues[key]])

class GetLaLoad():
	def __init__(self, i=None):
		self.i = i
	def clone(self):
		return laLoad.getSyntax().clone(str(round(os.getloadavg()[self.i], 2)))

class GetLaLoadInt():
	def __init__(self, i=None):
		self.i = i
	def clone(self):
		return laLoadInt.getSyntax().clone(int(os.getloadavg()[self.i]//0.01))
		
#class GetLaLoadFloat():
#	def __init__(self, i=None):
#		self.i = i
#	def clone(self):
#		return laLoadFloat.getSyntax().clone(('%.5f' % os.getloadavg()[1]))
laMax = 12

for i in [0, 1, 2]:
	laIndexInst		= MibScalarInstance(laIndex.getName(), (i,), laIndex.getSyntax().clone(i))
	laNamesInst		= MibScalarInstance(laNames.getName(), (i,), laNames.getSyntax().clone('laLoad-' + str((i+1)*5)))
	laLoadInst		= MibScalarInstance(laLoad.getName(), (i,), GetLaLoad(i))
	laConfigInst	= MibScalarInstance(laConfig.getName(), (i,), laConfig.getSyntax().clone(laMax))
	laLoadIntInst	= MibScalarInstance(laLoadInt.getName(), (i,), GetLaLoadInt(i))
#	laLoadFloatInst = MibScalarInstance(laLoadFloat.getName(), (i,), GetLaLoadFloat(i))
	if laMax > os.getloadavg()[i]:
		laErrorFlagInst = MibScalarInstance(laErrorFlag.getName(), (i,), laErrorFlag.getSyntax().clone(UCDErrorFlag(0)))
		laErrMessageInst= MibScalarInstance(laErrMessage.getName(), (i,), laErrMessage.getSyntax().clone(''))
	else:
		laErrorFlagInst = MibScalarInstance(laErrorFlag.getName(), (i,), laErrorFlag.getSyntax().clone(UCDErrorFlag(1)))
		laErrMessageInst= MibScalarInstance(laErrMessage.getName(), (i,), laErrMessage.getSyntax().clone(str((i+1)*5) + ' min Load Average too high'))
		
	namedSyms = {
		'laIndex' + str(i) : laIndexInst,
		'laNames' + str(i) : laNamesInst,
		'laLoad' + str(i)  : laLoadInst,
		'laConfig' + str(i) : laConfigInst,
		'laLoadInt' + str(i) : laLoadIntInst,
#		'laLoadFloat' + str(i) : laLoadFloatInst,
		'laErrorFlag' + str(i) : laErrorFlagInst,
		'laErrMessage' + str(i) : laErrMessageInst,
	}
	mibBuilder.exportSymbols("__UCD-SNMP-MIB", **namedSyms)
	

__ssCpuRawUser = MibScalarInstance(ssCpuRawUser.name, (0,), SsCpuRawUser(0))
__ssCpuRawNice = MibScalarInstance(ssCpuRawNice.name, (0,), SsCpuRawNice(0))
__ssCpuRawIdle = MibScalarInstance(ssCpuRawIdle.name, (0,), SsCpuRawIdle(0))
__ssCpuRawSystem = MibScalarInstance(ssCpuRawSystem.name, (0,), SsCpuRawSystem(0))
__memTotalReal = MibScalarInstance(memTotalReal.name, (0,), MemTotalReal(0))
__memTotalSwap = MibScalarInstance(memTotalSwap.name, (0,), MemTotalSwap(0))
__memAvailSwap = MibScalarInstance(memAvailSwap.name, (0,), MemAvailSwap(0))
__memTotalFree = MibScalarInstance(memTotalFree.name, (0,), MemTotalFree(0))
__memShared	   = MibScalarInstance(memShared.name, (0,), MemShared(0))
__memBuffer    = MibScalarInstance(memBuffer.name, (0,), MemBuffer(0))
__memCached    = MibScalarInstance(memCached.name, (0,), MemCached(0))

mibBuilder.exportSymbols(
    "__UCD-SNMP-MIB",
    memory		 = memory,
    systemStats  = systemStats,
    memTotalReal = __memTotalReal,
    memTotalSwap = __memTotalSwap,
    memAvailSwap = __memAvailSwap,
    memTotalFree = __memTotalFree,
    memShared    = __memShared,
    memBuffer    = __memBuffer,
    memCached    = __memCached,
    ssCpuRawUser = __ssCpuRawUser,
    ssCpuRawNice = __ssCpuRawNice,
    ssCpuRawIdle = __ssCpuRawIdle,
    ssCpuRawSystem = __ssCpuRawSystem
    )



