'''
Created on Sep 23, 2010

@author: marat
'''
import time
import os
from ConfigParser import ConfigParser

class FarmUIError(Exception):
	pass

EC2_ROLE_DEFAULT_SETTINGS = {
	'aws.availability_zone' : 'us-east-1a',
	'aws.instance_type' : 't1.micro'
}

EC2_MYSQL_ROLE_DEFAULT_SETTINGS = {
	'mysql.ebs_volume_size' : '1'
}

class FarmUI:
	sel = None
	farm_id = None	
	servers = None
	def __init__(self, sel):
		self.sel = sel
		self.servers = []
	
	def use(self, farm_id):
		self.servers = []
		self.farm_id = farm_id
		login(self.sel)
		self.sel.open('/farms_add.php?id=%s' % self.farm_id)
		self.sel.wait_for_page_to_load(30000)
		time.sleep(1)
		if self.sel.is_text_present('Unrecoverable error'):
			raise Exception("Farm %s doesn't exist" % self.farm_id)
		
	def add_role(self, role_name, min_servers=1, max_servers=2, settings=None):
		if not 'farms_add.php?id=' in self.sel.get_location():
			raise FarmUIError("Farm's settings page hasn't been opened. Use farm first")
		try:
			self.sel.click('//span[text()="%s"]' % role_name)
		except:
			raise Exception("Role '%s' doesn't exist" % role_name)
		
		pic = self.sel.get_attribute('//span[text()="%s"]/../../td[2]/img/@src' % role_name)
		if 'iconUnCheckAll' in pic:
			self.sel.click('//span[text()="%s"]/../../td[2]/img[@src="%s"]' % (role_name, pic))
		elif 'iconCheckAll' in pic:
			self.sel.click('//span[text()="%s"]' %  role_name)
			pass
		elif 'iconUncheckDis' in pic:
			raise Exception("Cannot enable role %s: Cannot check in user interface")
		else:
			raise Exception("Nothing to do")
		
		self.sel.type('scaling.min_instances', min_servers)
		self.sel.type('scaling.max_instances', max_servers)
		
		if settings and isinstance(settings, dict):
			for option, value in settings.iteritems():
				try:
					self.sel.type(option, value)
				except:
					pass
					
	def remove_role(self, role_name):
		if not 'farms_add.php?id=' in self.sel.get_location():
			raise Exception("Farm's settings page hasn't been opened. Use farm first")
		try:
			self.sel.click('//span[text()="%s"]' % role_name)
		except:
			raise Exception("Role '%s' doesn't exist" % role_name)
		
		pic = self.sel.get_attribute('//span[text()="%s"]/../../td[2]/img/@src' % role_name)
		
		if 'iconCheckAll' in pic:
			self.sel.click('//span[text()="%s"]/../../td[2]/img[@src="%s"]' % (role_name, pic))
	
	
	def save(self):
		if not 'farms_add.php?id=' in self.sel.get_location():
			raise Exception("Farm's settings page hasn't been opened. Use farm first")

		try:
			self.sel.click('button_js')
			self.sel.wait_for_page_to_load(15000)
		except:
			try:
				text = self.sel.get_text('//div[@class="viewers-messages viewers-errormessage"]/')
				raise FarmUIError('Something wrong with saving farm %s : %s' % (self.farm_id, text))
			except FarmUIError, e:
				print str(e)
			except Exception, e:
				print 'Cannot save farm for unknown reason'
			
	def launch(self):
		if not hasattr(self, 'farm_id'):
			raise FarmUIError("Can't launch farm without farm_id: use the farm first")
		
		self.sel.open('/farms_control.php?farmid=%s' % self.farm_id)
		self.sel.wait_for_page_to_load(30000)

		if self.sel.is_text_present("Would you like to launch"):
			self.sel.click('cbtn_2')
			self.sel.wait_for_page_to_load(30000)
		else:
			self.sel.open('/')
			raise Exception('Farm %s has been already launched' % self.farm_id)
	
	def terminate(self, keep_ebs=False, remove_from_dns=True):
		if not hasattr(self, 'farm_id'):
			raise FarmUIError("Can't launch farm without farm_id: use the farm first")

		#TODO: use 'keep_ebs' argument
		self.sel.open('/farms_control.php?farmid=%s' % self.farm_id)
		if self.sel.is_text_present("You haven't saved your servers"):
			self.sel.click('cbtn_3')
			self.sel.wait_for_page_to_load(30000)
		if self.sel.is_text_present('Delete DNS zone from nameservers'):
			if remove_from_dns:
				self.sel.check('deleteDNS')
			else:
				self.sel.uncheck('deleteDNS')
			self.sel.click('cbtn_2')
			self.sel.wait_for_page_to_load(30000)
			try:
				self.sel.get_text('//div[@class="viewers-messages viewers-successmessage"]/')
			except:
				try:
					text = self.sel.get_text('//div[@class="viewers-messages viewers-errormessage"]/')
					raise FarmUIError('Something wrong with terminating farm %s : %s' % (self.farm_id, text))
				except FarmUIError, e:
					print str(e)
				except Exception, e:
					print 'Cannot terminate farm for unknown reason'
		else:
			self.sel.open('/')
			raise Exception('Farm %s has been already terminated' % self.farm_id)
		
	def get_public_ip(self, server_id, timeout = 45):
		start_time = time.time()
		while time.time() - start_time < timeout:
			self.sel.open('server_view_extended_info.php?server_id=%s' % server_id)
			self.sel.wait_for_page_to_load(15000)
			try:
				public_ip = self.sel.get_text('//table[@id="Webta_InnerTable_Platform specific details"]/tbody/tr[8]/td[2]').strip()
			except:
				raise FarmUIError('Server %s doesn\'t exist')
			if public_ip:
				break
		else:
			raise FarmUIError("Cannot retrieve server's public ip. Server id: %s " % server_id)
		self.servers.append(public_ip)
		return public_ip
	
def login(sel):
	config = ConfigParser()
	
	_user_ini = os.path.expanduser('~/.scalr-dev/integ_test.ini')
	if not os.path.exists(_user_ini):
		raise Exception("User's ini file with scalr's settings doesn't exist")
	config.read(_user_ini)
	try:
		login = config.get('general', 'scalr_net_login')
		password = config.get('general', 'scalr_net_password')
	except:
		raise Exception("User's ini file doesn't contain username or password")

	sel.delete_all_visible_cookies()
	sel.open('/')
	sel.click('//div[@class="login-trigger"]/a')
	sel.type('login', login)
	sel.type('pass', password)
	sel.check('keep_session')
	sel.click('//form/button')
	sel.wait_for_page_to_load(30000)
	if sel.get_location().find('/client_dashboard.php') == -1:
		raise Exception('Login failed.')

def reset_farm(ssh, farm_id):
	pass

def exec_cronjob(ssh, name):
	pass