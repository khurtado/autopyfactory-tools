#!/usr/bin/env python


import logging
import logging.handlers

# adding the logging level TRACE to avoid problems
# when we find it in the apf code
logging.TRACE = 5
logging.addLevelName(logging.TRACE, 'TRACE')
def trace(self, msg, *args, **kwargs):
    self.log(logging.TRACE, msg, *args, **kwargs)
logging.Logger.trace = trace

from autopyfactory.configloader import Config, ConfigManager


# -------------------------------------------------------------------------------------------------
#           PARSE INPUTS    
# -------------------------------------------------------------------------------------------------

import getopt
import sys

opts, args = getopt.getopt(sys.argv[1:], '', ['conf=', 'activated=', 'running=', 'pending=', 'status='])

conffile = ""
activated = 0
pending = 0
running = 0
status = 'online'

for o, a in opts:
    if o == '--conf':
        conffile = a
    if o == '--activated':
        activated = int(a)
    if o == '--pending':
        pending = int(a)
    if o == '--running':
        running = int(a)
    if o == '--status':
        status = a


# -------------------------------------------------------------------------------------------------
#           OPEN THE CONF FILE  
# -------------------------------------------------------------------------------------------------

conf = ConfigManager().getConfig(conffile)
section_name = conf.sections()[0]


# -------------------------------------------------------------------------------------------------
#           MOCKS
# -------------------------------------------------------------------------------------------------

class sitestatus(object):
    def __init__(self):
        self.status = status
        self.cloud = section_name 


class wmsinfo(object):
    def __init__(self):
        self.ready = activated

    def valid(self):
        return True

class batch(object):
    def __init__(self):
        self.pending = pending
        self.running = running 
    def valid(self):
        return True



class wmsstatus_plugin(object):
    def getInfo(self, queue="",  maxtime=0):
        return wmsinfo()

    def getSiteInfo(self, site="", maxtime=0):
        return sitestatus()


class batchstatus_plugin(object):
    def getInfo(self, queue="", maxtime=0):
        return batch()



class apfqueue(object):

    def __init__(self):

        self.apfqname = section_name 
        self.qcl = conf 

        self.log = logging.getLogger()
        logStream = logging.FileHandler('/dev/null')    
        FORMAT='%(asctime)s (UTC) [ %(levelname)s ] %(name)s %(filename)s:%(lineno)d : %(message)s'
        formatter = logging.Formatter(FORMAT)
        logStream.setFormatter(formatter)
        self.log.addHandler(logStream)

        self.wmsstatus_plugin = wmsstatus_plugin()
        self.batchstatus_plugin = batchstatus_plugin()

        self.wmsstatusmaxtime = 0
        self.batchstatusmaxtime = 0
    
        self.wmsqueue = section_name 
        self.siteid = section_name


apf = apfqueue()    


        
# -------------------------------------------------------------------------------------------------
#   SCHED PLUGINS   
# -------------------------------------------------------------------------------------------------

scheds = []
scheds_names = conf.get(section_name, 'schedplugin').split(',')
scheds_names = [name.strip() for name in scheds_names]
for name in scheds_names:
    plugin_module = __import__('autopyfactory.plugins.queue.sched.%s' %name, 
        globals(),
        locals(),
        ["%s" % name])

    plugin_class_name = name
    plugin_class = getattr(plugin_module, plugin_class_name)

    sched = plugin_class(apf)
    scheds.append(sched)


print ''
print 'inputs:'
print '   activated : ', activated
print '   pending   : ', pending
print '   running   : ', running
print '   status    : ', status

items = conf.items(section_name)
n = 0
for sched in scheds:
    print ''
    print 'sched plugin %s' %sched.__class__.__name__
    print '   configuration:'
    for k,v in items:
        if k.startswith('sched.'):
            if k.split('.')[1] == sched.__class__.__name__.replace('SchedPlugin','').lower():
                print '      %s = %s ' %(k,v)

    (n, msg) = sched.calcSubmitNum(n)
    print '   output %s ' % n

print ''
print 'Final output %s' %n
print ''



