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

asa, err = ASA_REG('node_neg')
asa2, err = ASA_REG('cluster_neg')

##########
# MY_ULA str
# NEIGHBOR_ULA list[str]
##########
MY_ULA, NEIGHBOR_ULA = get_neighbors() 


##########
# NEIGHBOR_INFO dict locator:json
##########
NEIGHBOR_INFO = {}

##########
# dict to map str(locator) -> locator; then can be used to access neighbor_info
##########
NEIGHBOR_LOCATOR_STR = {}

##########
# ?
##########
NEIGHBOR_UPDATE = {} 

##########
# locator of heavier nodes
##########
HEAVIER = {}
##########
# locator of lighter nodes
##########
LIGHTER = {}
##########
# locator of heaviest node
##########
HEAVIEST = None
########Flags#######
CLUSTER_HEAD = False
INITIAL_NEG = False
CLUSTERING_DONE = False
SYNCH = False
TO_JOIN = None

##########CLUSTER INFO#######
CLUSTERS_INFO = {}
CLUSTER_INFO_KEYS = []
#######topology of the network#######
TP_MAP = {}
MAP_SEM = threading.Semaphore()

##########
# node_info['weight'] is run once, that's why we don't need a tmp variable to store node's weight
# status 1:not decided, 2:cluster-head, 3:want to join, 4:joined 5:changed (!)
##########
node_info = {'ula':str(acp._get_my_address()), 'weight':get_node_value(),
             'cluster_head':False, 'cluster_set':[], 'neighbors':NEIGHBOR_ULA, 
             'status': 1} 
obj, err = OBJ_REG('node', cbor.dumps(node_info), True, False, 10, asa)
# tag_lock = True
tagged   = TAG_OBJ(obj, asa)
tagged_sem = threading.Semaphore()

####step 1 - neighbor discovery####

def listen(_tagged):
    while True:
        err, handle, answer = graspi.listen_negotiate(_tagged.source, 
                                                      _tagged.objective)       
        if not err:
            mprint("\033[1;32;1m incoming request \033[0m")
            if _tagged.objective.name == "node": #intended for neighbor disc/neg
                threading.Thread(target=listen_hander, args=[_tagged,handle,answer]).start()
            elif _tagged.objective.name == "cluster_head": #intended for clusterhead disc/neg
                threading.Thread(target=cluster_listen_handler, args=[_tagged, handle, answer]).start()
            else:
                pass
        else:
            mprint("\033[1;31;1m in listen error {} \033[0m" .format(graspi.etext[err]))

listen_1 = threading.Thread(target=listen, args=[tagged]) #TODO change the name
listen_1.start()

def discover(_tagged, _attempts = 3):
    global NEIGHBOR_INFO #x
    attempt = _attempts
    while attempt != 0:
        _, ll = graspi.discover(_tagged.source,_tagged.objective, 10000, flush=True, minimum_TTL=50000)
        mprint(len(ll))
        attempt-=1
    if _tagged.objective.name == 'node':
        for item in ll:
            NEIGHBOR_INFO[item] = 0
            NEIGHBOR_LOCATOR_STR[str(item.locator)] = item
        #threading.Thread(target=run_neg, args=[tagged, NEIGHBOR_INFO.keys(), _attempt]).start()
        mprint(NEIGHBOR_LOCATOR_STR)
    elif _tagged.objective.name == 'cluster_head':
        for item in ll:
            if str(item.locator) != MY_ULA:
                CLUSTERS_INFO[str(item.locator)] = 0
                CLUSTER_INFO_KEYS.append(item)
                mprint("cluster head found at {}".format(str(item.locator)))
        #threading.Thread(target=run_clustering_neg, args=[_tagged, CLUSTER_INFO_KEYS, 1]).start()
    else:
        mprint("$$$$$$$\ndumping\n$$$$$$$$$")
        graspi.dump_all()
        for item in ll:
            mprint("cluster heads found at {}".format(str(item.locator)))

discovery_1 = threading.Thread(target=discover, args=[tagged, 1])
discovery_1.start()