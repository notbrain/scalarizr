'''
Created on Sep 23, 2010

@author: marat
'''
import time
import os
from ConfigParser import ConfigParser
from szr_integtest import config
from scalarizr.libs.metaconf import NoPathError
import paramiko
from szr_integtest_libs import exec_command, clean_output
from selenium import selenium

class FarmUIError(Exception):
	pass

EC2_ROLE_DEFAULT_SETTINGS = {
	'aws.availability_zone' : 'us-east-1a',
	'aws.instance_type' : 't1.micro'
}

EC2_MYSQL_ROLE_DEFAULT_SETTINGS = {
	'mysql.ebs_volume_size' : '1'
}

class ScalrConsts:
	class Platforms:
		PLATFORM_EC2 	= 'Amazon EC2'
		PLATFORM_RS  	= 'Rackspace'
	class Behaviours:
		BEHAVIOUR_BASE  = 'Base images'
		BEHAVIOUR_APP   = 'Application servers'
		BEHAVIOUR_MYSQL = 'Database servers' 


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
		self.sel.open('farms_builder.php?id=%s' % self.farm_id)
		self.sel.wait_for_page_to_load(30000)
		time.sleep(1)

		
	def add_role(self, role_name, min_servers=1, max_servers=2, settings=None):

		settings = settings or dict()
		if not 'aws.instance_type' in settings:
			settings['aws.instance_type'] = 't1.micro'
		settings['scaling.min_instances'] = min_servers
		settings['scaling.max_instances'] = max_servers
			
		if not 'farms_builder.php?id=' in self.sel.get_location():
			raise FarmUIError("Farm's settings page hasn't been opened. Use farm first")
	
		self.sel.click('//span[text()="Roles"]')
		self.sel.click('//div[@class="viewers-selrolesviewer-blocks viewers-selrolesviewer-add"]')
		self.sel.wait_for_condition(
				"selenium.browserbot.getCurrentWindow().document.getElementById('viewers-addrolesviewer')", 5000)
		try:
			self.sel.click('//li[@itemname="%s"]' % role_name)
			time.sleep(0.5)
			self.sel.click('//li[@itemname="%s"]/div[@class="info"]/img[1]' % role_name)
			if self.sel.is_element_present('//label[text()="Location:"]'):
				self.sel.click('//label[text()="Platform:"]')
				self.sel.click('//div[text()="Amazon EC2"]')
				self.sel.click('//label[text()="Location:"]')
				self.sel.click('//div[@class="x-combo-list-inner"]/div[text()="AWS / US East 1"]')
				self.sel.click('//button[text()="Add"]')
		except:
			raise Exception("Role '%s' doesn't exist" % role_name)
		try:
			# uncutted 
			self.sel.click('//span[@class="short" and text()="%s"]' % role_name)
		except:
			self.sel.click('//div[@class="full" and text()="%s"]' % role_name)
		
		i = 1
		while True:
			try:
				self.sel.click('//div[@class="viewers-farmrolesedit-tab" and position()=%s]' % i)
				time.sleep(0.3)
				for option, value in settings.iteritems():
					try:
						self.sel.type('//div[@class=" x-panel x-panel-noborder"]//*[@name="%s"]' % option, value)
					except:
						pass
				i += 1
			except:
				break
				
		self.sel.click('//div[@class="viewers-selrolesviewer-blocks viewers-selrolesviewer-add"]')

	def remove_role(self, role_name):
		if not 'farms_builder.php?id=' in self.sel.get_location():
			raise Exception("Farm's settings page hasn't been opened. Use farm first")
		
		self.sel.click('//span[text()="Roles"]')
		
		try:
			self.sel.click('//div[text()="%s"]/../a' % role_name)
			self.sel.click('//button[text()="Yes"]')
		except:
			raise Exception("Role '%s' doesn't exist" % role_name)

			
	def remove_all_roles(self):
		if not 'farms_builder.php?id=' in self.sel.get_location():
			raise Exception("Farm's settings page hasn't been opened. Use farm first")
		
		self.sel.click('//span[text()="Roles"]')
		while True:
			try:
				self.sel.click('//div[@id="viewers-selrolesviewer"]/ul/li/a/')
				self.sel.click('//button[text()="Yes"]')
			except:
				break
		
	def save(self):
		if not 'farms_builder.php?id=' in self.sel.get_location():
			raise Exception("Farm's settings page hasn't been opened. Use farm first")

		self.sel.click('//button[text() = "Save"]')
		while True:
			try:
				text = self.sel.get_text('//div[@id="top-messages"]/div[last()]')
				break
			except:
				continue

		if text != 'Farm saved':
			raise FarmUIError('Something wrong with saving farm %s : %s' % (self.farm_id, text))
			
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
	
def import_server(sel, platform_name, behaviour, host, role_name):
	'''
	@return: import shell command
	'''
	login(sel)
	sel.open('szr_server_import.php')
	
	platforms = sel.get_select_options('//td[@class="Inner_Gray"]/table/tbody/tr[2]/td[2]/select')
	if not platform_name in platforms:
		raise Exception('Unknown platform: %s' % platform_name)
	sel.select('//td[@class="Inner_Gray"]/table/tbody/tr[2]/td[2]/select', platform_name)
	
	behaviours = sel.get_select_options('//td[@class="Inner_Gray"]/table/tbody/tr[3]/td[2]/select')
	if not behaviour in behaviours:
		raise Exception('Unknown behaviour: %s' % behaviour)
	sel.select('//td[@class="Inner_Gray"]/table/tbody/tr[3]/td[2]/select', behaviour)
	
	sel.type('//td[@class="Inner_Gray"]/table/tbody/tr[4]/td[2]/input', host)
	sel.type('//td[@class="Inner_Gray"]/table/tbody/tr[5]/td[2]/input', role_name)
	sel.click('cbtn_2')
	sel.wait_for_page_to_load(15000)
	if not sel.is_text_present('Step 2'):
		try:
			text = sel.get_text('//div[@class="viewers-messages viewers-errormessage"]/span')			
			raise FarmUIError('Something wrong with importing server: %s' % text)
		except FarmUIError, e:
			raise
		except:
			raise Exception("Can't import server for unknow reason (Step 1)")
		
	return sel.get_text('//td[@class="Inner_Gray"]/table/tbody/tr[3]/td[1]/textarea')
	
def login(sel):

	try:
		login = config.get('./scalr/admin_login')
		password = config.get('./scalr/admin_password')
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

def exec_cronjob(name):
	cron_keys = ['BundleTasksManager', 'Scaling', 'Poller']
	cron_ng_keys = ['ScalarizrMessaging', 'MessagingQueue']
	if not name in cron_keys and not name in cron_ng_keys:
		raise Exception('Unknown cronjob %s' % name)

	cron_php_path = ('cron-ng/' if name in cron_ng_keys else 'cron/') +'cron.php'
	
	scalr_host = config.get('./scalr/hostname')
	ssh_key_path = config.get('./scalr/ssh_key_path')
	if not os.path.exists(ssh_key_path):
		raise Exception("Key file %s doesn't exist" % ssh_key_path)
	ssh_key_password = config.get('./scalr/ssh_key_password')
	home_path = config.get('./scalr/home_path')
	
	ssh = paramiko.SSHClient()
	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	key = paramiko.RSAKey.from_private_key_file(ssh_key_path, password = ssh_key_password)
	ssh.connect(scalr_host, pkey = key, username='root')
	channel = ssh.invoke_shell()
	clean_output(channel, 5)
	exec_command(channel, 'cd ' + home_path)
	print 'cd %s' % home_path 
	job_cmd = 'php -q ' + cron_php_path + ' --%s' % name
	print job_cmd
	out = exec_command(channel, job_cmd)
	channel.close()
	return out
