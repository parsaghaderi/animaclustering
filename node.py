from time import sleep
from cluster import *
import random
import threading
# HEAD = False
NODE_ID, NEIGHBORS = readmap(MAP_PATH)
#TODO check readmap - remove cast
# NODE_ID = str(NODE_ID)
# NEIGHBORS = [str(tmp) for tmp in NEIGHBORS]
CLUSTER = False
CLUSTER_SET = []

'''
each time node receives an weight from neighbors
the update will be saved in this dict.
the values in dict are initialized to False.
'''

RCV_NEIGHBORS = dict((RCV_NEIGHBORS,0) for RCV_NEIGHBORS in NEIGHBORS)
RCV_CH = []
'''
received roles are stored here
* join(u, v) node u joins v
* join (v, v) node v is the cluster head  = ch(v)
'''
RCV_ROLES = dict((tmp+"_role",False) for tmp in NEIGHBORS)

# '''
# registering ASA named cluster
# '''
err, cluster = ASA_REG("cluster")


def get_node_value():
    rand = random.random()
    num_neighbors = len(NEIGHBORS)
    return num_neighbors*rand

WEIGHT = get_node_value()
'''
registering objective called node
the value of this objective is weight of the node.
it's only for sync. 
@param name = node ; same in all nodes
@param neg = False
@param synch = True
@param value = random number + number of neighbors
@param asa
@param loop-count 
'''
node, err = OBJ_REG(NODE_ID, WEIGHT, False, True, 10, cluster)
tagged = TAG_OBJ(node, cluster)

node_role,err = OBJ_REG(NODE_ID+"_role", 0, False, True, 10, cluster)
role_tagged = TAG_OBJ(node_role, cluster)
'''
flooding weight
stops when info from all neighbors is received
'''
# class flooder(threading.Thread):
#     def __init__(self, tagged):
#         threading.Thread.__init__(self)
#         self.tagged = tagged
    
#     def run(self):
#         while True:
#             err = graspi.flood(self.tagged.source, 59000, [graspi.tagged_objective(self.tagged.objective, None)])
#             sleep(5)
#         return err
# node_info_flooder = flooder(tagged)
# node_info_flooder.start()

def flooder(tagged, asa):
    while True:
        err = graspi.flood(asa, 59000, [graspi.tagged_objective(tagged.objective, None)])
        if not err:
            mprint("flooding objective {}".format(tagged.objective.name))
        else:
            mprint("can't flood because {}".format(graspi.etext[err]))
        sleep(1)

flooding_thread = threading.Thread(target=flooder, args=[tagged, cluster])
flooding_thread.start()
#TODO stop

def role_flooder(tagged, asa):
    while tagged.objective.value == 0:
        mprint("waiting to decide role")
        sleep(3)
    while True:
        err = graspi.flood(asa, 59000, [graspi.tagged_objective(tagged.objective, None)])
        if not err:
            mprint("flooding objective {}'s role".format(tagged.objective.name))
        else:
            mprint("can't flood because {}".format(graspi.etext[err]))
        sleep(1)

role_thread = threading.Thread(target=role_flooder, args=[role_tagged, cluster])
role_thread.start()
#TODO stop

neighbor_weight = dict((tmp,None) for tmp in NEIGHBORS)
for key in NEIGHBORS:
    mprint(key)
    tmp, err = OBJ_REG(key, None, False, True, 10, cluster)
    neighbor_weight[key] = TAG_OBJ(tmp, cluster)
    
    
'''
listen to neighbor weight
create a thread for each neighbor
'''
#TODO add number of tries
# #TODO add loop count
# #it stops by itself.

def listener(tagged, asa):
    while True:
        mprint("listening for objective {}".format(tagged.objective.name))
        err, result = graspi.synchronize(
                        asa, 
                        tagged.objective,
                        None, 
                        5000)
        if not err:
            mprint("neighbor {} weight received".format(tagged.objective.name))
            RCV_NEIGHBORS[tagged.objective.name] = result.value
            mprint("&&&&&&&&&&&&&&&&&\nfrom {} value {}\n&&&&&&&&&&&&&&&&&\n".format(tagged.objective.name, RCV_NEIGHBORS[tagged.objective.name]))
            mprint(RCV_NEIGHBORS)
            exit()
            #TODO check if this works
        else:

            mprint("can't get weight from {}".format(
                                    graspi.etext[err]))
            sleep(5)
'''
create threads for all neighbors
'''
threads= dict((tmp,None) for tmp in NEIGHBORS)


for key in threads:
    threads[key] = threading.Thread(target=listener, args = [neighbor_weight[key], cluster])

for i in threads:
    threads[i].start()

def role_listener(tagged, asa):
    while True:#TODO change the condition
        mprint("listening to role of node {}".format(tagged.objective.name))
        err, result = graspi.synchronize(
                        asa, 
                        tagged.objective,
                        None, 
                        5000)
        if not err:
            mprint("neighbor {} role received".format(tagged.objective.name))
            RCV_ROLES[tagged.objective.name] = result.value
            mprint("&&&&&&&&&&&&&&&&&\nfrom {} role is {}\n&&&&&&&&&&&&&&&&&\n".format(tagged.objective.name, RCV_ROLES[tagged.objective.name]))
            mprint(RCV_ROLES)
            exit()
            #TODO check if this works
        else:

            mprint("can't get role from {}".format(
                                    graspi.etext[err]))
            sleep(5)


neighbor_role = dict((tmp,None) for tmp in NEIGHBORS)
for key in NEIGHBORS:
    mprint(key)
    tmp, err = OBJ_REG(key+"_role", None, False, True, 10, cluster)
    neighbor_role[key] = TAG_OBJ(tmp, cluster)
    
role_threads_listener = dict((tmp,None) for tmp in NEIGHBORS)
for key in role_threads_listener:
    role_threads_listener[key] = threading.Thread(target=role_listener, args = [neighbor_role[key], cluster])

for i in role_threads_listener:
    role_threads_listener[i].start()



'''
Update messages can be:
    * join(u, v) where u is the neighbor ID and v is the node they're joining
    * head(v) where v is the neighbor and announces itself as clusterhead
'''

'''
init phase
'''
def init():
    while 0 in RCV_NEIGHBORS.values():
        mprint("haven't received all weights ")
        sleep(1)
    if WEIGHT > RCV_NEIGHBORS[max(RCV_NEIGHBORS, key = RCV_NEIGHBORS.get)]:
        CLUSTER = NODE_ID
        CLUSTER_SET.append(NODE_ID)
        mprint("&&&&&&&&&&&&&&&&&&\nI'm head\n&&&&&&&&&&&&&&&&&&\n")
        node_role.value = NODE_ID
        exit()
        #broadcast CH
    #else: wait for join

init_thread = threading.Thread(target=init, args=[])
init_thread.start()

'''
decides for ch

a_subset = {key: value for key, value in a_dictionary.items() if value > 2}

'''
def check_CH():
    greater = {key for key, value in RCV_NEIGHBORS.items() if value > WEIGHT}
    
    for item in greater:
        if RCV_ROLES != False:
            rcvd_ch(greater)
        else:
            #wait
            pass

def rcvd_ch(nodes):
    max = 0
    for item in nodes: #neighbor with max weight who sent ch or join
                        #rcv_roles[item] == item -> item has sent ch
        if RCV_NEIGHBORS[item] > max and RCV_ROLES[item] == item:
            max = item
    CLUSTER = max
    #TODO join max

    #neighbors with greater weight check and see if have recevied messages from them or not

def rcv_join(node):
    if node == NODE_ID: #cluster head joined another cluster
        CLUSTER_SET.append(node)
        #TODO terminate
    elif node == CLUSTER:
        greater = {key for key, value in RCV_NEIGHBORS.items() if value > WEIGHT}
        if len(greater) != 0:
           pass 

    

#TODO broadcast role as CH

# # def send_role():
# #     while True:
# #         err = 

# #TODO use enum
# #if ndoe_ID and id are same, then it's ch(node_ID)
# #ow its joining id
# def set_role(id):
#     if id == NODE_ID:
#         return [NODE_ID, NODE_ID]
#     else:
#         return [NODE_ID, id]
    
# def send_role(id):
#     role.objective.value = set_role(id)
#     while True:
#         err = graspi.flood(role.source, 59000, [graspi.tagged_objective(role.objective, None)])
#         sleep(5)
# send_ch_thread = threading.Thread(target=send_role, args = [NODE_ID])


# def init():
#     if WEIGHT > max(RCV_NEIGHBORS, key=RCV_NEIGHBORS.get):
#         HEAD = True
#         CLUSTER = NODE_ID
#         CLUSTER_SET.append(NODE_ID)
#         role.value = set_role(NODE_ID) #node is its own clusterhead

#         #TODO send CH(node_ID) or join(node_ID, node_ID)
#         send_ch_thread().start
#     else:
#         #run join(node_ID, neighbor_ID)
#         pass
# #TODO now it's like {1:[1, 2], 2[2, 2]} will be changed to {1:2, 2:2}
# def decide():
#     ch_list = []
#     for i in RCV_ROLES:
#         if RCV_ROLES[i][0] == RCV_ROLES[i][1]:
#             ch_list.append[i]
    
#     to_join = None
#     if len(ch_list)> 1:
#         for i in RCV_NEIGHBORS:
#             if RCV_NEIGHBORS[i] == max(RCV_NEIGHBORS, key=RCV_NEIGHBORS.get):
#                 to_join = i
#     #send join




# def join():
#     max_weight = max(RCV_NEIGHBORS, key=RCV_NEIGHBORS.get)
#     max_neighbor = None
#     for i in RCV_NEIGHBORS:
#         if RCV_NEIGHBORS[i] == max_weight:
#             max_neighbor = i
#         else:
#             max_neighbor = NODE_ID
    
#     #TODO flood join(node_ID, max_neighbor)



# testobj = OBJ_REG(NODE_ID, get_node_value(), False, True, 10, cluster)

# def changetestvalue(obj):
#     while True:
#         sleep(10)
#         obj.value +=1

# tagged = TAG_OBJ(testobj, cluster)

# class flooder(threading.Thread):
#     def __init__(self, obj):
#         threading.Thread.__init__(self)
#         self.obj = obj
#     def run(self):
#         while True:
#             err = graspi.flood(self.obj.source, 59000, [graspi.tagged_objective(self.obj.objective, None)])
#             time.sleep(3)

# threading.Thread(target=changetestvalue, args=[]).start()
# flooder(tagged).start()


# ###############################################


# from cluster import *
# from time import sleep

# def flooder(tagged, asa):
#     while True:
#         mprint("flooding objective {}".format(tagged.objective.name))
#         err = graspi.flood(
#             asa, 59000,  [graspi.tagged_objective(tagged.objective, None)]
#         )
#         sleep(1)

# def listener(tagged, asa):
#     while True:
#         mprint("synchronizing obj {}".format(tagged.objective.name))
#         err, result = graspi.synchronize(
#             asa, tagged.objective, None, 5000
#         )
#         if not err:
#             mprint("value of obj {} is being synchronized".format(tagged.objective.name))
#             mprint("peer offered {}".format(result.value))
#             exit()
#         else:
#             mprint("there is an error, {}".format(graspi.etext[err]))

# NODE, NEIGHBORS = readmap(MAP_PATH)


# err, asa = ASA_REG('asa')
# obj, err = OBJ_REG("1", 10, False, True, 10, asa)
# tagged = TAG_OBJ(obj, asa)

# obj2, err = OBJ_REG("2", None, False, True, 10, asa)
# tagged2 = TAG_OBJ(obj2, asa)


# a = threading.Thread(target=flooder, args=[tagged, asa])
# b = threading.Thread(target = listener, args=[tagged2, asa])
# b.start()
