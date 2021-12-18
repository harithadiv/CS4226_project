'''
Please add your name: Divakaran Haritha
Please add your matric number: A0187915N
'''

import sys
import os
import datetime
from sets import Set

from pox.core import core

import pox.openflow.libopenflow_01 as of
import pox.openflow.discovery
import pox.openflow.spanning_forest

from pox.lib.revent import *
from pox.lib.util import dpid_to_str
from pox.lib.addresses import IPAddr, EthAddr

log = core.getLogger()

class Controller(EventMixin):
    def __init__(self):
        self.listenTo(core.openflow)
        core.openflow_discovery.addListeners(self)
        self.port_map = {}
        self.policy = []
        self.premium = []
    # You can write other functions as you need.
        
    def _handle_PacketIn (self, event):    
    	# install entries to the route table
        def install_enqueue(event, packet, outport, q_id):
            msg = of.ofp_flow_mod()
            msg.match = of.ofp_match.from_packet(packet, port)
            #qos priority lower than firewall priority
            msg.priority = 5
            msg.actions.append(of.ofp_action_enqueue(port = outport, queue_id = q_id))
            msg.data = event.ofp
            msg.idle_timeout = 30
            msg.hard_timeout = 30
            event.connection.send(msg)

        def fill_table():
            if dpid not in self.port_map:
                self.port_map[dpid] = {}

            if source_mac not in self.port_map[dpid]:
                self.port_map[dpid][source_mac] = (port, datetime.datetime.now())

        def unfill_table():
            #time_logic = self.port_map[dpid][dest_mac][1] + datetime.timedelta(seconds=30) <= datetime.datetime.now()
            
            #if expired then remove destination mac to port entry
            if dest_mac in self.port_map[dpid] and self.port_map[dpid][dest_mac][1] + datetime.timedelta(seconds=30) <= datetime.datetime.now():
                self.port_map[dpid].pop(dest_mac)
        

    	# Check the packet and decide how to route the packet
        def forward(message = None):
            
            if dest_mac not in self.port_map[dpid]: 
                flood()
            else:
                if source_ip in self.premium:
                    q_id = 1
                else:
                    q_id = 0

                install_enqueue(event, packet, self.port_map[dpid][dest_mac][0], q_id)
                

        # When it knows nothing about the destination, flood but don't install the rule
        def flood (message = None):
            # define your message here
            msg = of.ofp_packet_out()
            msg.data = event.ofp
            msg.in_port = port
            # ofp_action_output: forwarding packets out of a physical or virtual port
            # OFP
            # P_FLOOD: output all openflow ports expect the input port and those with 
            #    flooding disabled via the OFPPC_NO_FLOOD port config bit
            msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
            event.connection.send(msg)


        packet = event.parsed
        #mac address of source, dest hosts  
        source_mac = packet.src
        dest_mac = packet.dst
        port = event.port
        dpid = event.dpid
        source_ip  = None
        dest_ip = None

        if packet.type == packet.IP_TYPE:
            #ip address of source, dest hosts
            source_ip = packet.payload.srcip
            dest_ip = packet.payload.dstip

        fill_table()
        forward()
        unfill_table()


    def _handle_ConnectionUp(self, event):
        dpid = dpid_to_str(event.dpid)
        log.debug("Switch %s has come up.", dpid)
        
        # Send the firewall policies to the switch
        def sendFirewallPolicy(connection, policy):
            # define your message here
            msg = of.ofp_flow_mod()
            if len(policy) == 2:
                msg.match.nw_dst = IPAddr(policy[0])
                msg.match.tp_dst = int(policy[1])
            else:
                msg.match.nw_src = IPAddr(policy[0])
                msg.match.nw_dst = IPAddr(policy[1])
                msg.match.tp_dst = int(policy[2])
            
            #higher priority than qos
            msg.priority = 10
            #for TCP protocol
            msg.match.nw_proto = 6

            #for IP packets 
            msg.match.dl_type = 0x800
            
            # OFPP_NONE: outputting to nowhere if it matches the port number 
            msg.actions.append(of.ofp_action_output(port = of.OFPP_NONE))

            event.connection.send(msg)

        for i in self.policy:
            sendFirewallPolicy(event.connection, i)
            


        def policies(file):
            with open(file) as fd:
                N, M = fd.readline().split()
                for i in range(int(N)):
                    self.policy.append(fd.readline().split(","))

                for i in range(int(M)):
                    self.premium.append(fd.readline())

        policies("policy.in")
        for pol in self.policy:
            sendFirewallPolicy(event.connection, pol)


def launch():
    # Run discovery and spanning tree modules
    pox.openflow.discovery.launch()
    pox.openflow.spanning_forest.launch()

    # Starting the controller module
    core.registerNew(Controller)
