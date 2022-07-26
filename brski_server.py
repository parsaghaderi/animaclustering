import random
import threading
import cbor
import subprocess as sp
from time import sleep

try:
    import graspi
    _old_API = False    
except:
    import grasp as graspi
    _old_API = True
import acp
import networkx as nx
import sys
#########################
# utility function for setting the value of
# each node randomly. 
#########################
def get_node_value():
    return random.random()
    
#########################
# utility print function
#########################
def mprint(msg):
    print("\n#######################")
    print(msg)
    print("#######################\n")

##############
# geting the locators as strings
##############
def get_neighbors():
    f = open('/etc/TD_neighbor/locators')
    l = f.readlines()
    l = [item.rstrip('\n') for item in l]
    return l[0], l[1:]

#########################
#Registering ASA 
#########################
def ASA_REG(name):
    mprint("registering asa and objective")
    err, asa_handle = graspi.register_asa(name)
    if not err:
        mprint("ASA registered successfully")
        return asa_handle, err
    else:
        mprint("Cannot register ASA:\n\t" + graspi.etext[err])
        mprint("exiting now.")


#########################
#Registering objectives
#########################
def OBJ_REG(name, value, neg, synch, loop_count, ASA):
    obj = graspi.objective(name)
    obj.value = value
    obj.neg = neg
    obj.synch = synch
    obj.loop_count = loop_count
    err = graspi.register_obj(ASA, obj)
    if not err:
        mprint("Objective registered successfully")
    else:
        mprint("Cannot register Objective:\n\t"+ graspi.etext[err])
        mprint("exiting now.")
    return obj, err

###########
# mapping each objective to an ASA
###########
def TAG_OBJ(obj, ASA):
    return graspi.tagged_objective(obj, ASA)

BRSKI_locator = 10
LOCATOR_STR   = {} #map str(LOCATOR.locator) to LOCATOR.locator
NEIGHBOR_INFO = {} #key: locator object, value: node_info
# NEIGHBORS_ULA = set() #str(neighbor.ll) locator of neighbors #removed, result=neighbor_info.keys()
UPDATES = {} #keep track of which nodes have been updated
node_info = {'ula':str(acp._get_my_address()), 'weight':get_node_value(),
             'cluster_head':False, 'cluster_set':[], 'neighbors':list(LOCATOR_STR.keys()), 
             'status': 1} 

asa, err     = ASA_REG("brski")

node, err     = OBJ_REG("node", cbor.dumps(node_info), True,
                    False, 10, asa)
tagged_sem = threading.Semaphore()
tagged       = TAG_OBJ(node, asa)



server, err = OBJ_REG("server", None, True, False, 10, asa)
tagged_server = TAG_OBJ(server, asa)

# brski, err   = OBJ_REG("brski", None, True,
#                     False, 10, asa)

# tagged_brski = TAG_OBJ(brski, asa)

#on all nodes
def listen(_tagged):
    while True:
        err, handle, answer = graspi.listen_negotiate(_tagged.source, _tagged.objective)
        if not err:
            if _tagged.objective.name == "node":
                threading.Thread(target=listen_node_handler, args=[_tagged, handle, answer]).start()
            elif _tagged.objective.name == "server":
                pass
        else:
            mprint("\033[1;31;1m ERROR IN LISTEN - OBJ {} : {} \033[0m"
                    .format(_tagged.objective.name,graspi.etext[err]))           

#on brski
def listen_node_handler(_tagged, _handle, _answer):
    tmp_answer = cbor.loads(_answer)
    mprint("req_neg initial value : peer offered {}".format(tmp_answer))#√
    for item in NEIGHBOR_INFO:#TODO can do better
        if str(item.locator) == tmp_answer['ula']:
            NEIGHBOR_INFO[item] = tmp_answer
    #can send nothing and eng neg
    _err = graspi.end_negotiate(_tagged.source, _handle, True, reason="value received")
    if _err:
        mprint("\033[1;31;1m in listen_node_handler error happened {} \033[0m".format(graspi.etext[_err]))

def discover_neighbor(_tagged, _attempts = 3):
    attempt = _attempts
    while attempt!=0:
        _, ll = graspi.discover(_tagged.source,_tagged.objective, 10000, flush=True, minimum_TTL=1)
        if len(ll) != 0:
            attempt -= 1
    if _tagged.objective.name == "node":
        for item in ll:
            if not LOCATOR_STR.__contains__(str(item.locator)):
                LOCATOR_STR[str(item.locator)] = item.locator
                NEIGHBOR_INFO[item.locator] = []
                mprint("\033[1;32;1m new neighbor found {}\033[0m".format(str(item.locator)))

#on client
def listen_brski_update(_tagged, _handle, _answer):
    tmp_answer = cbor.loads(_answer.value)
    ROLE = tmp_answer['role'] #cluster_head or ordinary node
    CLUSTER_HEAD = tmp_answer['cluster'] #str, look at the str->locator dict 
    if tmp_answer['role'] == "ch":#cluster_head or ordinary node
        CLUSTER_SET = tmp_answer['cluster_set']
    _err = graspi.end_negotiate(_tagged.source, _handle, True, reason="value received")
    if _err:
        mprint("\033[1;31;1m in listen_node_handler error happened {} \033[0m".format(graspi.etext[_err]))

# def listen for updates to make changes and send to cluster head! clusterhead might change


threading.Thread(target=listen, args=[tagged]).start()
threading.Thread(target=discover_neighbor, args=[tagged]).start()
threading.Thread(target=listen, args=[tagged_server]).start()
