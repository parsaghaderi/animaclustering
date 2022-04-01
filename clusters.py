import random
import threading
import cbor
import subprocess as sp
from time import sleep

from new_test import find_heavier

# import grasp
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

############
# keep running
############
def gremlin():
    while True:
        sleep(1)
threading.Thread(target=gremlin, args=[]).start()

##########
# MY_ULA str
# NEIGHBOR_ULA str
##########
MY_ULA, NEIGHBOR_ULA = get_neighbors() 
##########
# NEIGHBOR_INFO dict locator:json
##########
NEIGHBOR_INFO = {}
##########
# ?
##########
NEIGHBOR_UPDATE = {} 
##########
# node_info['weight'] is run once, that's why we don't need a tmp variable to store node's weight
##########
node_info = {'ula':str(acp._get_my_address()), 'weight':get_node_value(), 'cluster_head':False, 'cluster_set':[], 'neighbors':[]} 
obj, err = OBJ_REG('node', cbor.dumps(node_info), True, False, 10, asa)
tag_lock = True
tagged   = TAG_OBJ(obj, asa)

##########
# @param _tagged, a tagged objective to listen for
##########
def listen(_tagged):
    while True:
        
        err, handle, answer = graspi.listen_negotiate(_tagged.source, _tagged.objective)
        if not err:
            #mprint("incoming request")
            threading.Thread(target=listener_handler, args=[_tagged, handle, answer]).start()
        else:
            mprint(graspi.etext[err])
threading.Thread(target=listen, args=[tagged]).start()
###########
# @param _tagged tagged objective listening for
# @param _handle handler for the incoming request
# @param _answer offered answer from neg peer
###########
def listener_handler(_tagged, _handle, _answer):
    global tag_lock
    tmp_answer = cbor.loads(_answer.value)
    mprint("req_neg initial value : peer offered {}".format(tmp_answer))#√
    
    mprint("sent from peer {}".format(tmp_answer))
    #TODO get info from the answer
    #we already know the dict of neighbor_info has been created!
    ###########
    while len(NEIGHBOR_INFO)!=len(NEIGHBOR_ULA):
        pass

    for item in NEIGHBOR_INFO:
        if str(item.locator) == tmp_answer['ula']:
            NEIGHBOR_INFO[item] = tmp_answer
    ############
    while not tag_lock:
        pass
    tag_lock = False
    _answer.value = _tagged.objective.value #TODO can be optimized by using the info in request (answer)
    tag_lock = True
    _r = graspi.negotiate_step(_tagged.source, _handle, _answer, 10000)
    if _old_API:
        err, temp, answer = _r
        reason = answer
    else:
        err, temp, answer, reason = _r
    if (not err) and (temp == None):
        pass
        
    else:
        mprint("neg with peer interrupted with error code {}".format(graspi.etext[err]))
        pass

def discover(_tagged):
    global NEIGHBOR_INFO
    attempt = 3
    while attempt != 0:
        _, ll = graspi.discover(_tagged.source,_tagged.objective, 10000, flush=True, minimum_TTL=50000)
        mprint(len(ll))
        attempt-=1
    for item in ll:
        NEIGHBOR_INFO[item] = 0
threading.Thread(target=discover, args=[tagged]).start()

INITIAL_NEG = False

############
# run neg for initial step of exchanging information w/ neighbors
############
def run_neg(_tagged, _locators):
    global INITIAL_NEG
    while len(NEIGHBOR_INFO)!=len(NEIGHBOR_ULA):
        pass
    for item in _locators:
        threading.Thread(target=neg, args=[_tagged, item, 1]).start()
    while list(NEIGHBOR_INFO.values()).__contains__(0):
        pass
    INITIAL_NEG = True

threading.Thread(target=run_neg, args=[tagged, NEIGHBOR_INFO.keys()]).start()


############
# @param _tagged tagged objective for negotiating over
# @param ll locator of the peer
# @param _attempt number of attempts for negotiating 
############
def neg(_tagged, ll, _attempt = 3):
    global NEIGHBOR_INFO

    if _attempt!=3:
        mprint("start negotiation o kire khar {}".format(ll.locator))
    else:
        mprint("start negotiating with {}".format(ll.locator))
    attempt = _attempt
    while attempt!=0:
        if _old_API:
            err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, ll, None) #TODO
            reason = answer
        else:
            err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, ll, None)
        if not err:
            NEIGHBOR_INFO[ll] = cbor.loads(answer.value)#√
            mprint("neg_step value : peer {} offered {}".format(str(ll.locator), NEIGHBOR_INFO[ll]))#√
            if NEIGHBOR_INFO[ll]['cluster_head'] == str(acp._get_my_address()): #√
                if not node_info['cluster_set'].__contains__(str(ll.locator)):
                    node_info['cluster_set'].append(str(ll.locator))
                while not tag_lock:
                    pass
                tag_lock = False
                _tagged.objective.value = cbor.dumps(node_info)
                tag_lock = True
                NEIGHBOR_UPDATE[ll.locator] = True
            _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
        else:
            mprint("neg failed + {}".format(graspi.etext[_err]))
            _err = graspi.end_negotiate(_tagged.source, handle, False, "value not received")
        sleep(3)
        attempt-=1
        


# HEAVIER = {}
# LIGHTER = {}
# HEAVIEST = None

# def sort_weight():
#     global NEIGHBOR_INFO, HEAVIER, LIGHTER, HEAVIEST
#     my_weight = node_info['weight']
#     max_weight = my_weight
#     heavy = {} #TODO room for optimization
#     light = {} #TODO room for optimization
#     for item in NEIGHBOR_INFO:
#         if NEIGHBOR_INFO[item]['weight']> my_weight:
#             HEAVIER[item] = ['weight']
#         else:
#             LIGHTER[item] = ['weight']

#         if NEIGHBOR_INFO[item]['weight']> max_weight:
#             HEAVIEST = item #locator #TODO subject to change if it joins another cluster

# #########
# # @param _heaviest takes the current heaviest(locator), return next one in line
# # @return locator of the 2nd heaviest node
# #########
# def find_next_heaviest(_heaviest):
#     global HEAVIER, HEAVIEST
#     tmp_max = 0
#     tmp_heaviest = None
#     for item in HEAVIER:
#         if item!= HEAVIEST and HEAVIER[item]> tmp_max and HEAVIER[_heaviest] > HEAVIER[item]:
#             tmp_max = HEAVIER[item]
#             tmp_heaviest = item
#     return tmp_heaviest

# ###########
# # init process
# ###########

# def init():
#     global INITIAL_NEG, HEAVIEST
#     while not INITIAL_NEG:
#         pass
#     sort_weight()
#     if HEAVIEST == None:
#         mprint("I'm clusterhead")
#         mprint(node_info['weight'])
#         mprint(list(NEIGHBOR_INFO.values))

#     else:
#         mprint("I want to join {}".format(HEAVIEST.locator))
#         mprint(node_info['weight'])
#         mprint(list(NEIGHBOR_INFO.values))

# threading.Thread(target=init, args=[]).start()