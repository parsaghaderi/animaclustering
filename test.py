from base64 import decode
import os
import random
import threading
import cbor
import subprocess as sp
from time import sleep
# import grasp
try:
    import graspi
    _old_API = False
except:
    import grasp as graspi
    _old_API = True
import acp
def grasp_run():
    while True:
        grasp._initialise_grasp()
        while True:
            sleep(5)
threading.Thread(target=grasp_run, args = [])

def get_neighbors():
    f = open('/etc/TD_neighbor/locators')
    l = f.readlines()
    l = [item.rstrip('\n') for item in l]
    return l[0], l[1:]
MY_ULA, NEIGHBOR_ULA = get_neighbors()
NEIGHBOR_INFO = {}

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
        
def TAG_OBJ(obj, ASA):
    return graspi.tagged_objective(obj, ASA)

# NEIGHBOR Discovery - Start
asa, err = ASA_REG('neg1')
obj, err = OBJ_REG('node', cbor.dumps(get_node_value()), True, False, 10, asa)

tagged   = TAG_OBJ(obj, asa)

def discovery_listener(_tagged):
    while True:
        err, handle, answer = graspi.listen_negotiate(_tagged.source, _tagged.objective)
        if not err:
            threading.Thread(target = neighbor_discovery_listener_handler, args = [_tagged, handle, answer]).start()
        else:
            mprint(graspi.etext[err])

def neighbor_discovery_listener_handler(_tagged, handle, answer):
    answer.value = cbor.loads(answer.value)
    answer.value = _tagged.objective.value
    _r = graspi.negotiate_step(_tagged.source, handle, answer, 10000)
    if _old_API:
        err, temp, answer = _r
        reason = answer
    else:
        err, temp, answer, reason = _r
    if (not err) and (temp == None):
        pass
    else:
        mprint(graspi.etext[err])

def request_neg_neighbor_discovery(_tagged, ll):
    if _old_API:
        err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, ll, None) #TODO
        reason = answer
    else:
        err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, ll, None)

    if not err:
        mprint("peer {} offered {}".format(ll.locator, cbor.loads( answer.value)))
        NEIGHBOR_INFO[ll] = cbor.loads(answer.value)
        #TODO use the value here
        _err = graspi.end_negotiate(_tagged.source, handle, True, "neg finished")
        if not _err:
            pass
        else:
            mprint("error in ending negotiation {} with {}".format(graspi.etext[_err], ll.locator))
    else:
        mprint("can't make neg request {} to {}".format(graspi.etext[err], ll.locator))

def send_request(_tagged):
    for item in NEIGHBOR_INFO:
        threading.Thread(target=request_neg_neighbor_discovery, args=[_tagged, item]).start()
    while len(NEIGHBOR_ULA) != len(NEIGHBOR_INFO):
        mprint("waiting for weights from neighbors - {}".format(len(NEIGHBOR_INFO)))
        sleep(1)
    
def neighbor_discovery(_tagged):
    neighbors = set()
    while True:
        err, ll = graspi.discover(_tagged.source, _tagged.objective, 10000, flush=True)
        if (not err) and len(ll) != 0:
            for item in ll:
                mprint("node {} has objective {}".format(item.locator, _tagged.objective.name))
                if str(item.locator) in NEIGHBOR_ULA:
                    neighbors.add(item.locator)
                    add = True
                    for i in NEIGHBOR_INFO.keys():
                        if i.locator == item.locator:
                            add = False
                    if add:
                        NEIGHBOR_INFO[item] = 0
            if len(neighbors) == len(NEIGHBOR_ULA):
                mprint("found all neighbors \n {}".format(neighbors))
                threading.Thread(target=send_request, args=[_tagged]).start()
                break
        else:
            mprint(graspi.etext[err])
        sleep(1)

threading.Thread(target=discovery_listener, args = [tagged]).start()
threading.Thread(target = neighbor_discovery, args=[tagged]).start()

#neighbor discovery done - locators and weight of neighbors received
# NEIGHBOR Discovery - Finished

#NEIGHBOR ROLE - Start
CLUSTER_HEAD = False
CLUSTER_SET = {acp._get_my_address():[]}
HEAVIER_NODES = []
cluster, err = OBJ_REG('cluster_info', None, True, False, 10, asa)
tagged_cluster = TAG_OBJ(cluster, asa)

def set_heavier():
    while len(NEIGHBOR_ULA) != len(NEIGHBOR_INFO):
        sleep(0.5)
    my_weight = cbor.loads(tagged.objective.value)
    for item in NEIGHBOR_INFO:
        if NEIGHBOR_INFO[item] > my_weight:
            HEAVIER_NODES.append(item)
    mprint("heavier nodes {}".format(HEAVIER_NODES))
    threading.Thread(target=start_role_request, args=[]).start()  

threading.Thread(target=set_heavier, args= []).start()

def init():
    global CLUSTER_HEAD
    while len(NEIGHBOR_ULA) != len(NEIGHBOR_INFO):
        sleep(0.5)
    max_key = max(NEIGHBOR_INFO, key=NEIGHBOR_INFO.get)
    if NEIGHBOR_INFO[max_key] < cbor.loads(tagged.objective.value):
        CLUSTER_HEAD = True
        mprint("I'm cluster head")
    else:
        CLUSTER_HEAD = str(max_key.locator)
        mprint("joining {}".format(max_key.locator))
        
        #broadcast role as cluster head
threading.Thread(target = init, args = []).start()

def role_listener(_tagged):
    mprint("listening for incoming request for my role")
    while True:
        err, handle, answer = graspi.listen_negotiate(_tagged.source, _tagged.objective)
        if not err:
            threading.Thread(target = role_listener_handler, args = [_tagged, handle, answer]).start()
        else:
            mprint(graspi.etext[err])
        sleep(1)
threading.Thread(target=role_listener, args=[tagged_cluster]).start()

def role_listener_handler(_tagged, _handle, _answer):
    mprint("a node requested my role")
    _answer.value = cbor.dumps(CLUSTER_HEAD)
    _r = graspi.negotiate_step(_tagged.source, _handle, _answer, 10000)
    if _old_API:
        err, temp, answer = _r
        reason = answer
    else:
        err, temp, answer, reason = _r
    if (not err) and (temp == None):
        pass
    else:
        mprint(graspi.etext[err])


def request_neg_neighbor_role(_tagged, ll):
    mprint("asking {} for its role".format(ll.locator))
    if _old_API:
        err, handle, answer = graspi.req_negotiate(_tagged.source,
                                                   _tagged.objective,
                                                   ll, None)
        reason = answer
    else:
        err, handle, answer, reason = graspi.request_negotiate(_tagged.source,
                                                   _tagged.objective,
                                                   ll, None)
    # if cbor.loads(answer.value) == True:
    #     #TODO add to list of roles
    #     mprint("node {} is ch".format(ll.locator))
    # else:
    #     answer.value = cbor.loads(answer.value) #TODO cbor.loads(answer.value).locator
    #     mprint("node {} joined {}".format(ll.locator, answer.value.locator))
    #     pass
    mprint("****\nvalue {} recieved\n****".format(type(answer.value)))
    _err = graspi.end_negotiate(_tagged.source,handle, True, "neg finished")
    if not _err:
        mprint("neg for role finished with node {} with value".format(ll.locator, cbor.loads(answer.value)))
    else:
        mprint("neg over role with {} disrupted {}".format(ll.locator,graspi.etext[_err]))

def start_role_request():
    for item in HEAVIER_NODES:
        mprint("requestion {}'s role".format(item.locator))
        threading.Thread(target=request_neg_neighbor_role, 
                         args=[tagged_cluster, item]).start()
        sleep(0.5)

def on_ch_recieve():
    while len(NEIGHBOR_INFO) != len(NEIGHBOR_ULA):
        sleep(0.5)
    

#NEIGHBOR ROLE - finished