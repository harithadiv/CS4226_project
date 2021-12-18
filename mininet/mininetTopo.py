'''
Please add your name: Divakaran Haritha
Please add your matric number: A0187915N
'''

import os
import sys
import atexit
from mininet.net import Mininet
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.topo import Topo
from mininet.link import Link
from mininet.node import RemoteController

net = None

class TreeTopo(Topo):

    def __init__(self):
        Topo.__init__(self)   
        self.linkMap = {}     
	
    def readInput(self, inputfile):
        with open(inputfile) as fd:
            first_line = fd.readline()
            N, M, L = first_line.split()
            print("N , M, L", N, M, L)
            
            for i in range(1, int(N)+1):
                self.addHost('h%d' %i)

            for i in range(1, int(M)+1):
                sconfig = {'dpid': "%016x" %i}
                self.addSwitch('s%d' %i, **sconfig)

            for i in range(int(L)):
                line = fd.readline()
                h1, h2, bw = line.split(",")
                self.addLink(h1, h2)
                if h1 not in self.linkMap:
                    self.linkMap[h1] = {}
                if h2 not in self.linkMap:
                    self.linkMap[h2] = {}
                self.linkMap[h1][h2] = int(bw)
                self.linkMap[h2][h1] = int(bw)
                print("Added: ", h1, h2)
                print("Added: ", h2, h1)

def createQosQ(net, topo):
    for link in topo.links(True, False, True):
        for switch in topo.switches():
            linkinfo = link[2]
            port = None
            if linkinfo["node1"] == switch:
                port = linkinfo["port1"]
            elif linkinfo["node2"] == switch:
                port = linkinfo["port2"]

            if port is not None:
                intf_name = "%s-eth%s" %(switch, port)

                bw = topo.linkMap[linkinfo["node1"]][linkinfo["node2"]]
                bandwidth = bw * 1000000
                print("PARAMS:", intf_name, bandwidth, bandwidth*0.5, bandwidth*0.8)
            
                os.system('sudo ovs-vsctl -- set Port %s qos=@newqos \
                        -- --id=@newqos create QoS type=linux-htb other-config:max-rate=%d queues=0=@q0,1=@q1 \
                        -- --id=@q0 create queue other-config:max-rate=%d \
                        -- --id=@q1 create queue other-config:min-rate=%d' %(intf_name, bandwidth, bandwidth*0.5, bandwidth*0.8))



def startNetwork():
	info('** Creating the tree network\n')
	topo = TreeTopo()
	topo.readInput("topology.in")

	global net
	net = Mininet(topo=topo, link = Link,
					controller=lambda name: RemoteController(name, ip='192.168.56.102'),
					listenPort=6633, autoSetMacs=True)
		

	info('** Starting the network\n')
	net.start()
	net.waitConnected()

	createQosQ(net, topo)

	info('** Running CLI\n')
	CLI(net)

def stopNetwork():
    if net is not None:
        net.stop()
        # Remove QoS and Queues
        os.system('sudo ovs-vsctl --all destroy Qos')
        os.system('sudo ovs-vsctl --all destroy Queue')


if __name__ == '__main__':
    # Force cleanup on exit by registering a cleanup function
    atexit.register(stopNetwork)

    # Tell mininet to print useful information
    setLogLevel('info')
    startNetwork()
