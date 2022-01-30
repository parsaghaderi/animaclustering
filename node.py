from time import sleep
import webbrowser
from cluster import *
import random
import threading
# HEAD = False
NODE_ID, NEIGHBORS = readmap(MAP_PATH)
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

            mprint("can't get role, {}".format(
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




def decide():
    mprint("deciding for node's role")
    greater_weight = [key for key,value in RCV_NEIGHBORS.items() if value > WEIGHT]
    tmp  = {key:RCV_ROLES[key+"_role"] for key in greater_weight}
    mprint("!!!!!!!!!!!!!\n{}\n!!!!!!!!!!!!!!".format(tmp))
    while False in {key:RCV_ROLES[key+"_role"] for key in greater_weight}.values():
        mprint("waiting")
        sleep(1)
    
    mprint("for nodes with greater weight, roles have been received")
    mprint("$$$$$$$$$$$$$$$$\n{}\n$$$$$$$$$$$$$$$$".format(RCV_ROLES))
    greater_dict = {key: RCV_ROLES[key+"_role"] for key in greater_weight}
    mprint("weights {}\nroles {}\n".format({key: RCV_NEIGHBORS[key] for key in greater_weight}, greater_dict))
    max = 0
    print()
    for item in greater_dict.keys():
        if RCV_ROLES[item+"_role"] == item and RCV_NEIGHBORS[item] > max:
            max = item
    mprint("@@@@@@@@@@@@@@\njoining {} with weight {}\n@@@@@@@@@@@@@@\n".format(max, RCV_NEIGHBORS[max]))
    
    if max != 0:
        CLUSTER = max
        node_role.value = max
        role_tagged.objective.value = max #TODO have to delete it, I guess

decision = threading.Thread(target = decide, args=[])

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
    else:
        decision.start()
        exit()

init_thread = threading.Thread(target=init, args=[])
init_thread.start()

'''
decides for ch

a_subset = {key: value for key, value in a_dictionary.items() if value > 2}

'''


    
    

def rcv_role(node, role):
    pass






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

def check_ch_join():
    while True:
        while CLUSTER == NODE_ID:
            #wait
            sleep(1)
        else:
            if RCV_ROLES[CLUSTER+"_role"] != CLUSTER:
                greater_weight = [key for key,value in RCV_NEIGHBORS.items() if value > WEIGHT 
                                                                            and key != CLUSTER]
                greater_dict = {key: RCV_ROLES[key+"_role"] for key in greater_weight}

                max = 0
                for item in greater_dict.keys():
                    if RCV_ROLES[item+"_role"] == item and RCV_NEIGHBORS[item] > max:
                        max = item
                if max != 0:
                    CLUSTER = item
                    node_role.value = max
                    role_tagged.objective.value = max #TODO remove this I guess
                else:
                    CLUSTER = NODE_ID
                    node_role = NODE_ID
                    role_tagged.objective.value = NODE_ID
        sleep(1)

rcv_join = threading.Thread(target = check_ch_join, args=[])
rcv_join.start()
