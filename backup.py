__author__ = 'chenlei'

#coding: utf-8

from pysnmp.carrier.asynsock.dispatch import AsynsockDispatcher
from pysnmp.carrier.asynsock.dgram import udp, udp6
from pyasn1.codec.ber import decoder
from pysnmp.proto import api
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.proto import rfc1902
import time
#from snmpset4 import NetSnmpSet
#from NetSnmpGet import NetSnmpGet
import MySQLdb as mdb
import threading
import Queue
import socket
import telnetlib
import re



in_queue = Queue.Queue()



class GenCommand():
    def __init__(self,vendor,username,password):
        self.vendor = vendor
        self.username = username
        self.password = password
        #self.enablepassword = enablepassword


    def command(self):

        if self.vendor == 'cisco':
            #execfinish = '>'
            configfinish = '#'
            #enable = 'enable'
            ready_command = 'terminal length 0'
            excute_command = 'show running-config'


        if self.vendor == 'h3c':
            #execfinish = '>'
            configfinish = '>'
            #enable = 'system-view'
            ready_command = 'screen-length disable'
            excute_command = 'display current-config'





        command = {
                   1 : ['Username:',self.username,'Get the prompt of username,ready to enter username'],
                   2 : ['Password:',self.password,'Ready to enter the password'],
                   #3 : [ execfinish, enable,'Have entered the host '],
                   #4 : ['Password:', self.enablepassword, 'Ready to enter the privilege password'],
                   3 : [configfinish , ready_command ,'Have entered the enable mode of host '],
                   #6 : [configfinish , excute_command ,'Excute show running-config'],

                    }



        #print 'In the class , the command is ', command
        return command,configfinish,excute_command








class Backup():

    def __init__(self,ip,port):

        self.ip = ip
        self.port = port


    '''
    To get the time when write memory occurs.
    '''
    def getTime(self):
        refer_time = time.gmtime()
        savetime = time.strftime("%Y%m%d%H%M%S", refer_time)
        filename = time.strftime("%Y-%m-%d-%H-%M-%S", refer_time)
        return savetime,filename


    '''
    To verify if the port is open or not.
    '''
    def IsOpen(self):
        s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        #print ip,port
        try:
            s.connect((self.ip,int(self.port)))
            s.shutdown(2)
            #print '%s %d is open' % port
            return True
        except:
            print '%s %d is closed' % (self.ip,self.port)
            return False


    '''
    To telnet the vendor with command
    '''
    def TelnetConfig(self,vendor,configurl):
        Host = self.ip
        Port = self.port
        vendor = vendor.lower()
        try:


            #logging_name = self.ip + '-' +  time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()) + '.txt'

            logging_file = '/var/opt/src/LogFile/' +  configurl

            #logging_path = './LogFile/' + logging_name

            logfile = open(logging_file,'w')
        except:
            print "open file error"
            return False


        gencommand = GenCommand(vendor,'NMSBackup','NMSBackup')

        command ,  configfinish , excute_command = gencommand.command()

        #print 'Command is' , command
        #print 'Vendor is ' ,vendor
        #print 'excute_commad is ',excute_command
        tn = telnetlib.Telnet(Host,Port,2)
        tn.write('\n')



        '''if we can find the string in the read_until returns ,then tn.write something ,or close the host and return false
        To enter command in order to enter the privilege mode and prepare for the show run
        '''

        for (dict_key,dict_value) in command.items():
            if re.findall(dict_value[0],tn.read_until(dict_value[0],timeout=3)):
                #print 'Ready to enter the command' ,dict_value
                tn.write(dict_value[1] + '\n')
                print dict_value[2] , self.ip

            else:
                tn.close()
                print 'Error occurs under the prompt ', dict_key
                return False


        #logging the show run results
        try:
            pre_log =  tn.read_until(configfinish , timeout=20)
            terminal = pre_log.splitlines()[-1].strip()
            print 'terminal is ',terminal
            if terminal:
                tn.write(excute_command + '\n')
                log = tn.read_until(terminal,timeout=20)
                logfile.write(log)
                logfile.close()
                tn.close()
            else:
                print 'terminal is none'
                return False





        except:
            print "Config error"
            return False


        finally:
        #configfile.close()
            logfile.close()
            tn.close()

            print "%s has been Configed" % self.ip
            return log




class ConSql:
        def __init__(self,dbip,user,password,dbname):
            self.dbip = dbip
            self.user = user
            self.password = password
            self.dbname = dbname



        def get_data(self,ipaddr):
            con = None
            try:
                con = mdb.connect(self.dbip,self.user,self.password,self.dbname)
                cur = con.cursor()
                cur_result = cur.execute("select device_sysname,device_vendor from cmb_device where device_ip =%s", (ipaddr,))
                #cur_result = cur.execute("select device_sysname,device_vendor from cmb_device where device_ip ='10.50.255.3'")

                if cur_result:
                    print 'Getting data. Have found the existed node'
                    result = cur.fetchone()
                    sysname =  str(result[0])
                    vendor =  str(result[1])
                    print 'sysname and vendor is', (sysname,vendor)
                    cur.close()
                else:
                    print 'The node is not in the device list,please add the node into the device list at first'
                    return False

                if(vendor):
                    return sysname , vendor
                else:
                    return False

            finally:
                if con:
                    con.close()



        def put_data(self,ipaddr,configurl,savetime,content):
            con = None
            try:
                con = mdb.connect(self.dbip,self.user,self.password,self.dbname)
                cur = con.cursor()

                if cur.execute("select id from cmb_device where device_ip = %s",(ipaddr,)):
                    print 'Have found the existed node'
                    device_id =  str(cur.fetchone()[0])
                    print 'device id is',device_id
                    cur.executemany("insert into cmb_configbak (config_url,device_id,config_time,config_content) values (%s,%s,%s,%s)", [(configurl,device_id,savetime,content),])
                    #print 'method is',method
                    con.commit()
                    print 'Have inserted the config into database'
                    cur.close()
                else:
                    print 'The node is not in the device list,please add the node into the device list at first'

            finally:
                if con:
                    con.close()



def cbFun(transportDispatcher, transportDomain, transportAddress, wholeMsg):

    while wholeMsg:
        msgVer = int(api.decodeMessageVersion(wholeMsg))
        if msgVer in api.protoModules:
            pMod = api.protoModules[msgVer]
        else:
            print('Unsupported SNMP version %s' % msgVer)
            return
        reqMsg, wholeMsg = decoder.decode(
            wholeMsg, asn1Spec=pMod.Message(),
            )
        print('Notification message from %s:%s: ' % (
            transportDomain, transportAddress
            )
        )
        reqPDU = pMod.apiMessage.getPDU(reqMsg)
        if reqPDU.isSameTypeWith(pMod.TrapPDU()):
            if msgVer == api.protoVersion1:
                print('Enterprise: %s' % (
                    pMod.apiTrapPDU.getEnterprise(reqPDU).prettyPrint()
                    )
                )
                print('Agent Address: %s' % (
                    pMod.apiTrapPDU.getAgentAddr(reqPDU).prettyPrint()
                    )
                )
                print('Generic Trap: %s' % (
                    pMod.apiTrapPDU.getGenericTrap(reqPDU).prettyPrint()
                    )
                )
                print('Specific Trap: %s' % (
                    pMod.apiTrapPDU.getSpecificTrap(reqPDU).prettyPrint()
                    )
                )
                print('Uptime: %s' % (
                    pMod.apiTrapPDU.getTimeStamp(reqPDU).prettyPrint()
                    )
                )
                varBinds = pMod.apiTrapPDU.getVarBindList(reqPDU)
            else:
                varBinds = pMod.apiPDU.getVarBindList(reqPDU)
            print('Var-binds:')

            inter=''
            record = False
            for oid,val in varBinds:
                valout = val.prettyPrint()
                print('valout:',valout)
                inter = inter + str(valout.split('=')[-1].strip('\n'))
                #print('inter:',inter)
                #print('%s = %s' % (oid.prettyPrint(), val.prettyPrint()))

            if inter.endswith('134'):
                print ('Cisco Writen')
                record = True
            if inter.endswith('124'):
                print ('H3C Writen')
                record = True
            if record:
                backup = Backup(transportAddress[0],23)
                savetime , filename = backup.getTime()
                #configurl = hostname + '-' + filename + '.txt'
                if(backup.IsOpen()):

                    dosql = ConSql('127.0.0.1','root','cmbdb@0429','cmbsite')
                    get_data_result = dosql.get_data(transportAddress[0])
                    if get_data_result:
                        sysname , vendor = get_data_result

                        configurl = sysname + '-' + filename + '.txt'

                        content = str(backup.TelnetConfig(vendor,configurl))
                        if content and content != 'False':
                            dosql.put_data(transportAddress[0],configurl,savetime,content)
                            print 'Have inserted data successfully.'

                    else:
                        print 'Config failed'
                else:
                    print 'telnet port is closed'

    return wholeMsg

'''

def ScheduleConfig():

        con=None
        #print 'test'

        try:
            con=mdb.connect('127.0.0.1','root','','cmb')

            with con:
                cur=con.cursor()
                cur.execute("select ipaddr,hostname,version from nodes")
                nodes = cur.fetchall()
                #nodeips = nodes[0][0]
                #cur.execute("select hostname from nodes")
                #sql_host = nodes[0][1]

            for node in nodes:
               # nodeip = nodes[0][0]
               # sql_host = nodes[0][1]
                #print ('nodeip is %s ,sql_host is %s' % (nodeip,sql_host))
                #print 'Put the node %s into the queue' % node
                in_queue.put(node)

            for i in range(5):
                t = ScheduleThread(in_queue)
                t.setDaemon(True)
                t.start()
                time.sleep(5)

            in_queue.join()


        finally:
            if con:
                con.close()




def Schedule():
    while True:
        ScheduleConfig()
        time.sleep(60000000)

class ScheduleThread(threading.Thread):
    """Threaded telnet test"""
    def __init__(self, in_queue):
        threading.Thread.__init__(self)
        self.in_queue = in_queue
        #self.sql_host = sql_host


    def run(self):
        while True:
            #grabs host from queue
            list = self.in_queue.get()
            ip = list[0]
            sql_host = list[1]
            sql_version = list[2]
            #print 'ip is ',ip
            #print 'sql_host is ',sql_host
            savetime,filename,hostname,version = getContent(ip,gethostname=True,getversion=True)
            filename =filename + '-Auto'
            version = str(version).split('\n')[0]
            #print 'version is ',version


            if hostname!= None and hostname == sql_host and version == sql_version:
                #snmpset = NetSnmpSet(ip).snmpset(str(hostname),filename)

                configurl = hostname + '/' + filename

                if(IsOpen(ip,23)):
                    if TelnetConfig(ip,23,configurl,'running'):
                        doSql('127.0.0.1','root','','cmb',hostname,ip,version,configurl,savetime,1)
                    else:
                        print 'Config failed'
                else:
                    print 'telnet port is closed'
                #snmpget = NetSnmpGet().netsnmpget()

            else:
                print 'cancel'

            self.in_queue.task_done()


'''

transportDispatcher = AsynsockDispatcher()


transportDispatcher.registerRecvCbFun(cbFun)


# UDP/IPv4
transportDispatcher.registerTransport(
    udp.domainName, udp.UdpSocketTransport().openServerMode(('192.168.7.11', 162))
)

transportDispatcher.jobStarted(1)


#t=threading.Timer(5000000,Schedule)
#t.start()

try:
    # Dispatcher will never finish as job#1 never reaches zero
    transportDispatcher.runDispatcher()





except:
    transportDispatcher.closeDispatcher()
    raise
