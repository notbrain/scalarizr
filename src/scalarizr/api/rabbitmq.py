'''
Created on Feb 25, 2011

@author: uty
'''


from scalarizr.util.cryptotool import pwgen
from scalarizr.services.rabbitmq import rabbitmq as rabbitmq_svc
from scalarizr.services.rabbitmq import __rabbitmq__
from scalarizr import rpc

class RabbitMQAPI:

    @rpc.service_method
    def reset_password(self, new_password=None):
        """ Reset password for RabbitMQ user 'scalr'. Return new password  """
        if not new_password:
            new_password = pwgen(10)
        rabbitmq_svc.set_user_password('scalr', new_password)
        __rabbitmq__['password'] = new_password
        return new_password
