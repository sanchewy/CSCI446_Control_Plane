import queue
import threading
import re
import ast

## wrapper class for a queue of packets
class Interface:
    ## @param maxsize - the maximum size of the queue storing packets
    def __init__(self, maxsize=0):
        self.in_queue = queue.Queue(maxsize)
        self.out_queue = queue.Queue(maxsize)

    ##get packet from the queue interface
    # @param in_or_out - use 'in' or 'out' interface
    def get(self, in_or_out):
        try:
            if in_or_out == 'in':
                pkt_S = self.in_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the IN queue')
                return pkt_S
            else:
                pkt_S = self.out_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the OUT queue')
                return pkt_S
        except queue.Empty:
            return None

    ##put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param in_or_out - use 'in' or 'out' interface
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, in_or_out, block=False):
        if in_or_out == 'out':
            # print('putting packet in the OUT queue')
            self.out_queue.put(pkt, block)
        else:
            # print('putting packet in the IN queue')
            self.in_queue.put(pkt, block)


## Implements a network layer packet.
class NetworkPacket:
    ## packet encoding lengths
    dst_S_length = 5
    prot_S_length = 1

    ##@param dst: address of the destination host
    # @param data_S: packet payload
    # @param prot_S: upper layer protocol for the packet (data, or control)
    def __init__(self, dst, prot_S, data_S):
        self.dst = dst
        self.data_S = data_S
        self.prot_S = prot_S

    ## called when printing the object
    def __str__(self):
        return self.to_byte_S()

    ## convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.dst).zfill(self.dst_S_length)
        if self.prot_S == 'data':
            byte_S += '1'
        elif self.prot_S == 'control':
            byte_S += '2'
        else:
            raise('%s: unknown prot_S option: %s' %(self, self.prot_S))
        byte_S += self.data_S
        return byte_S

    ## extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        dst = byte_S[0 : NetworkPacket.dst_S_length].strip('0')
        prot_S = byte_S[NetworkPacket.dst_S_length : NetworkPacket.dst_S_length + NetworkPacket.prot_S_length]
        if prot_S == '1':
            prot_S = 'data'
        elif prot_S == '2':
            prot_S = 'control'
        else:
            raise('%s: unknown prot_S field: %s' %(self, prot_S))
        data_S = byte_S[NetworkPacket.dst_S_length + NetworkPacket.prot_S_length : ]
        return self(dst, prot_S, data_S)




## Implements a network host for receiving and transmitting data
class Host:

    ##@param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.intf_L = [Interface()]
        self.stop = False #for thread termination

    ## called when printing the object
    def __str__(self):
        return self.addr

    ## create a packet and enqueue for transmission
    # @param dst: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, dst, data_S):
        p = NetworkPacket(dst, 'data', data_S)
        print('%s: sending packet "%s"' % (self, p))
        self.intf_L[0].put(p.to_byte_S(), 'out') #send packets always enqueued successfully

    ## receive packet from the network layer
    def udt_receive(self):
        pkt_S = self.intf_L[0].get('in')
        if pkt_S is not None:
            print('%s: received packet "%s"' % (self, pkt_S))

    ## thread target for the host to keep receiving data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            #receive data arriving to the in interface
            self.udt_receive()
            #terminate
            if(self.stop):
                print (threading.currentThread().getName() + ': Ending')
                return



## Implements a multi-interface router
class Router:

    ##@param name: friendly router name for debugging
    # @param cost_D: cost table to neighbors {neighbor: {interface: cost}}
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, cost_D, max_queue_size):
        self.stop = False #for thread termination
        self.name = name
        #create a list of interfaces
        self.intf_L = [Interface(max_queue_size) for _ in range(len(cost_D))]
        #save neighbors and interfeces on which we connect to them
        self.cost_D = cost_D    # {neighbor: {interface: cost}}
        self.cost_D.update({self.name:{0:0}})
        #TODO: set up the routing table for connected hosts
        self.rt_tbl_D = {}      # {destination: {router: cost}}
        for key, value in cost_D.items():
            # print("Key"+key)
            for key1, value1 in cost_D[key].items():
                self.rt_tbl_D.update({key:{self.name:value1}})

        print('%s: Initialized routing table' % self)
        self.print_routes()


    ## called when printing the object
    def __str__(self):
        return self.name


    ## look through the content of incoming interfaces and
    # process data and control packets
    def process_queues(self):
        for i in range(len(self.intf_L)):
            pkt_S = None
            #get packet from interface i
            pkt_S = self.intf_L[i].get('in')
            #if packet exists make a forwarding decision
            if pkt_S is not None:
                p = NetworkPacket.from_byte_S(pkt_S) #parse a packet out
                if p.prot_S == 'data':
                    self.forward_packet(p,i)
                elif p.prot_S == 'control':
                    self.update_routes(p, i)
                else:
                    raise Exception('%s: Unknown packet type in packet %s' % (self, p))


    ## forward the packet according to the routing table
    #  @param p Packet to forward
    #  @param i Incoming interface number for packet p
    def forward_packet(self, p, i):
        try:
            # TODO: Here you will need to implement a lookup into the
            # forwarding table to find the appropriate outgoing interface
            # for now we assume the outgoing interface is 1
            self.intf_L[1].put(p.to_byte_S(), 'out', True)
            print('%s: forwarding packet "%s" from interface %d to %d' % \
                (self, p, i, 1))
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass


    ## send out route update
    # @param i Interface number on which to send out a routing update
    def send_routes(self, i):
        # TODO: Send out a routing table update
        #create a routing table update packet
        rm = RouteMessage(self.name, self.rt_tbl_D)
        payload = rm.to_byte_S()
        p = NetworkPacket(0, 'control', payload)
        try:
            print('%s: sending routing update "%s" from interface %d' % (self, p, i))
            self.intf_L[i].put(p.to_byte_S(), 'out', True)
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass


    ## forward the packet according to the routing table
    #  @param p Packet containing routing information
    def update_routes(self, p, i):
        change_flag = False
        packet = RouteMessage.from_byte_S(NetworkPacket.to_byte_S(p)[NetworkPacket.dst_S_length+NetworkPacket.prot_S_length:])
        # print("Packet before: "+str(NetworkPacket.to_byte_S(p)))
        print('%s: Received routing update %s from interface %d' % (self, packet, i))
        sender_address = packet[0]
        # print("INTERFACE COST %d, %s= %d" % (i,sender_address,self.cost_D[sender_address][i]))
        routes = packet[1]
        # print(type(routes),routes)
        # for key, value in routes.items():
        #     print(key, value)
        # print("sender address: "+str(sender_address))
        # print("self.rt: "+str(self.rt_tbl_D))
        neighbor_path = None
        first_route = None
        if sender_address in self.rt_tbl_D.keys():
            for intf in self.rt_tbl_D[sender_address].keys():
                neighbor_path = {sender_address:{intf:self.rt_tbl_D[sender_address][intf]}}
       # neighbor_path = list(self.rt_tbl_D[x] for x in self.rt_tbl_D if sender_address in self.rt_tbl_D.keys() and self.rt_tbl_D[sender_address] != [])
        if self.name in routes.keys():
            for intf in routes[self.name].keys():
                first_route = {self.name:{intf:routes[self.name][intf]}}
        # print("First Route:"+str(first_route)+" neighbor_path: "+str(neighbor_path))
        for route in routes.items():
            for key, value in route[1].items():
                route = [route[0],key,value]
                existing_route = None
            if route[0] in self.rt_tbl_D.keys():
                existing_route = self.rt_tbl_D[route[0]]
            # print("EXISTING ROUTE: "+str(existing_route))
            # print("Route"+str(route))
            if existing_route is None:
                self.rt_tbl_D.update({route[0]:{sender_address:self.cost_D[sender_address][i]+int(route[2])}})
                change_flag = True
            elif int(self.cost_D[sender_address][i]+int(route[2])) < int(next (iter (existing_route.values()))):
                self.rt_tbl_D.update({route[0]:{sender_address:int(next (iter (existing_route.values())))}})
                change_flag = True
            else:
                pass
        if change_flag:
            interface_list = set()
            for k,d in self.cost_D.items():
                for intf, value in d.items():
                    interface_list.add(intf)
            # print("INTERFACE LIST"+str(interface_list))
            for intf in interface_list:
                self.send_routes(int(intf))

    ## Print routing table
    def print_routes(self):
        print('%s: routing table' % self)
        #TODO: print the routes as a two dimensional table for easy inspection
        # Currently the function just prints the route table as a dictionary
        columns = list()
        for key, value in self.rt_tbl_D.items():
            columns.insert(len(columns), key)
        print("|======", end="")
        for i in range(len(columns)):
            print("|======", end="")
        print("|")
        dest = "| "+self.name+"   |"
        for i in columns:
            dest += " "+(str(i))+"   |"
        print(dest)
        print("|======", end="")
        for i in range(len(columns)):
            print("|======", end="")
        print("|")
        src = ""
        row_keys = set()
        for i in set(self.rt_tbl_D.keys()):
            row_keys.update(self.rt_tbl_D[i].keys())
        for i in row_keys:
            src += "| "+str(i)+"   |"
            for j in columns:
                key1 = self.rt_tbl_D.get(j)
                if key1 is not None and i in key1.keys():
                    key2 = key1.get(i)
                    if key2 is not None:
                        src += " "+str(key2)+"    |"
                    else:
                        src += " ~    |"
                else:
                    src += " ~    |"
            print(src)
            src = ""
        print("|======", end="")
        for i in range(len(columns)):
            print("|======", end="")
        print("|")
        print(self.rt_tbl_D)
        print()


    ## thread target for the host to keep forwarding data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            self.process_queues()
            if self.stop:
                print (threading.currentThread().getName() + ': Ending')
                return

class RouteMessage:
    ## packet encoding lengths
    name_length = 5

    ##@param dst_addr: address of the destination host
    # @param data_S: the routing table from the router
    # @param prot_S: upper layer protocol for the packet (data, or control)
    def __init__(self, name, data_S):
        self.name = name
        self.data_S = data_S

    def __str__(self):
        return self.to_byte_S()

    def to_byte_S(self):
        byte_S = str(self.name).zfill(self.name_length)
        columns = list()
        rows = list()
        for key, value in self.data_S.items():
            columns.insert(len(columns), key)
            for key2 in self.data_S[key]:
                rows.insert(len(rows), key2)
        routes = list()
        for i in range(len(columns)):
                dictionary = self.data_S[columns[i]][rows[i]]
                routes.append((columns[i],rows[i],dictionary))
        byte_S += str(routes)
        byte_S.replace("\'", "")
        # print("RouteMessage: "+byte_S)
        return byte_S

    @classmethod
    def from_byte_S(self, byte_S):
        name = byte_S[0 : RouteMessage.name_length].strip('0')
        data_S = byte_S[RouteMessage.name_length : ]
        data_S = re.findall(r"\(([^)]+)\)", data_S)
        new_dict = dict()
        for route in data_S:
            divide = [x.strip(' ()\'') for x in route.split(",")]
            new_dict[divide[0]]=({divide[1]: divide[2]})
        # print("Name:"+str(name)+" New Dict: "+str(new_dict))
        # print("TYPE BEFORE"+str(type(new_dict)))
        return name, new_dict
