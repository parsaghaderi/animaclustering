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


LOCATOR_STR   = {} #map str(LOCATOR.locator) to LOCATOR.locator
NEIGHBOR_INFO = {} #key: locator object, value: node_info
# NEIGHBORS_ULA = set() #str(neighbor.ll) locator of neighbors #removed, result=neighbor_info.keys()

node_info = {'ula':str(acp._get_my_address()), 'weight':get_node_value(),
             'cluster_head':False, 'cluster_set':[], 'neighbors':list(LOCATOR_STR.keys()), 
             'status': 1} 

asa, err     = ASA_REG("brski")

obj, err     = OBJ_REG("node", cbor.dumps(node_info), True,
                    False, 10, asa)

tagged       = TAG_OBJ(obj, asa)

brski, err   = OBJ_REG("brski", None, True,
                    False, 10, asa)

tagged_brski = TAG_OBJ(brski, asa)

def listen(_tagged):
    while True:
        err, handle, answer = graspi.listen_negotiate(_tagged.source, _tagged.objective)
        if not err:
            pass
        else:
            mprint("\033[1;31;1m ERROR IN LISTEN - OBJ {} : {} \033[0m"
                    .format(_tagged.objective.name,graspi.etext[err]))           

threading.Thread(target=listen, args=[tagged]).start()
if sys.argv[1] == "server":
    threading.Thread(target=listen, args=[tagged_brski]).start()


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
        else:
            mprint("\033[1;32;1m brski server found with locator address {}\033[0m".format(ll[0]))

threading.Thread(target=discover_neighbor, args=[tagged]).start()
if sys.argv[1] == "client":
    threading.Thread(target=discover_neighbor, args=[tagged_brski]).start()


def neg(_tagged):
    pass