#!/usr/bin/python

import subprocess
import os
from socket import gethostname

from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.cli import CLI
from mininet.link import Intf, Link, TCLink, TCIntf
from mininet.log import setLogLevel, info
from mininet.util import waitListening

host = int(gethostname().split('.')[0][4:])
TDF = 20.0
CIRCUIT_LINK = 80000  # Mbps
PACKET_LINK = 10000  # Mbps
NUM_RACKS = 8
HOSTS_PER_RACK = 8

def myNetwork():
    net = Mininet(topo=None, build=False)

    info('*** Adding controller\n')
    net.addController(name='c0')

    info('*** Add switches\n')
    s1 = net.addSwitch('s1')
    s1_eth2 = TCIntf('eth2', node=s1, bw=CIRCUIT_LINK / TDF)
    s2 = net.addSwitch('s2')
    s1_eth3 = Intf('eth3', node=s2)

    info('*** Add hosts and links\n')
    hosts = []
    for i in xrange(HOSTS_PER_RACK):
        j = (host+1, i+1)
        hosts.append(net.addHost('h%d%d' % j, ip='10.10.1.%d%d/24' % j, cls=CPULimitedHost,
                                 sched='cfs', period_us=100000,
                                 tdf=TDF))
        hosts[-1].setCPUFrac(1.0 / TDF)
        
        l = TCLink(hosts[i], s1, intfName1='h%d%d-eth1' % j, bw=PACKET_LINK / TDF)
        l.intf1.setMAC('AA:AA:AA:AA:AA:%d%d' % j)
        l = Link(hosts[i], s2, intfName1='h%d%d-eth2' % j)
        l.intf1.setIP('10.10.2.%d%d/24' % j)
    
    info('*** Starting network\n')
    net.start()
    info('*** done that\n')
    
    for h in hosts:
        h.cmd('ping router -c1 -W1')
        for i in xrange(NUM_RACKS):
            for j in xrange(HOSTS_PER_RACK):
                h.cmd("arp -s 10.10.1.%d%d `arp | grep router | tr -s ' ' | cut -d' ' -f3`" % (i+1, j+1))

    for h in hosts:
        h.cmd('/usr/sbin/sshd -D &')

    CLI(net)
    net.stop()

if __name__ == '__main__':
    subprocess.call([os.path.expanduser('~/sdrt/cloudlab/tune.sh')])
    setLogLevel('info')    
    myNetwork()