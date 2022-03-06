from audioop import reverse
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
asa, err = ASA_REG('node_neg')
def gremlin():
    while True:
        sleep(1)
threading.Thread(target=gremlin, args=[]).start()

node_info = {'weight':get_node_value(), 'cluster_head':False, 'cluster_set':[]}
obj, err = OBJ_REG('node', cbor.dumps(node_info), True, False, 10, asa)
tagged   = TAG_OBJ(obj, asa)

def listen(_tagged):
    while True:
        err, handle, answer = graspi.listen_negotiate(_tagged.source, _tagged.objective)
        if not err:
            #mprint("incoming request")
            threading.Thread(target=listener_handler, args=[_tagged, handle, answer]).start()
        else:
            mprint(graspi.etext[err])

def listener_handler(_tagged, _handle, _answer):
    #mprint("req_neg initial value : peer offered {}".format(cbor.loads(_answer.value)))
    _answer.value = _tagged.objective.value
    _r = graspi.negotiate_step(_tagged.source, _handle, _answer, 10000)
    if _old_API:
        err, temp, answer = _r
        reason = answer
    else:
        err, temp, answer, reason = _r
    if (not err) and (temp == None):
        #mprint("peer ended neg with reason {}".format(reason))
        pass
    else:
        #mprint("neg with peer interrupted with error code {}".format(graspi.etext[err]))
        pass

def discover(_tagged):
    attempt = 3
    while attempt != 0:
        _, ll = graspi.discover(_tagged.source,_tagged.objective, 10000, flush=True, minimum_TTL=50000)
        mprint(len(ll))
        attempt-=1
    for item in ll:
        #mprint("asking {}".format(item.locator))
        threading.Thread(target=neg, args=[_tagged, item]).start()
        # threading.Thread(target=req_role_update, args=[_tagged, item]).start()


       

def neg(_tagged, ll):
    while True:
        NEIGHBOR_INFO[ll.locator] = 0
        if _old_API:
            err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, ll, None) #TODO
            reason = answer
        else:
            err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, ll, None)
        if not err:

            NEIGHBOR_INFO[ll.locator] = cbor.loads(answer.value)
            # mprint("neg_step value : peer {} offered {}".format(ll.locator, NEIGHBOR_INFO[ll.locator]))
            if NEIGHBOR_INFO[ll.locator]['cluster_head'] == str(acp._get_my_address()):
                node_info['cluster_set'].append(str(ll.locator))
                obj.objective.value = cbor.dumps(node_info)
            _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
        else:
            mprint("neg failed")
            _err = graspi.end_negotiate(_tagged.source, handle, False, "value not received")
        sleep(3)
threading.Thread(target=listen, args=[tagged]).start()
threading.Thread(target=discover, args=[tagged]).start()



HEAVIER = []
HEAVIEST = False
# cluster_obj, err = OBJ_REG('clustering', cbor.dumps({CLUSTER_HEAD:CLUSTER_SET}))
# tagged_clustering = TAG_OBJ(cluster_obj, asa)
def find_heavier():
    global HEAVIEST,HEAVIER
    tmp = {}
    max_weight = cbor.loads(obj.value)['weight']
    max_key = False
    for item in NEIGHBOR_INFO:
        if NEIGHBOR_INFO[item]['weight'] > cbor.loads(obj.value)['weight']:
            # HEAVIER.append(item)
            tmp[item] = NEIGHBOR_INFO[item]['weight']
            if  NEIGHBOR_INFO[item]['weight'] > max_weight:
                max_weight = NEIGHBOR_INFO[item]['weight']
                max_key = item
    HEAVIEST = max_key
    tmp_sorted = dict(sorted(tmp.items(), key=lambda item: item[1], reverse = True))
    for item in tmp_sorted.keys():
        HEAVIER.append(item)
def init():
    while len(NEIGHBOR_INFO) != len(NEIGHBOR_ULA):
        sleep(2)
    find_heavier()
    if HEAVIEST != False:
        mprint("want to join {}".format(str(HEAVIEST)))
    else:
        mprint("I'm cluster head")
        node_info['cluster_head'] = True
        node_info['cluster_set'] = [str(acp._get_my_address())]
        tagged.objective.value = cbor.dumps(node_info)
    sleep(10)
    threading.Thread(target=on_update_rcv, args=[]).start()

threading.Thread(target=init, args=[]).start()

def on_update_rcv():
    global NEIGHBOR_INFO
    joined = False
    if not node_info['cluster_head']:
        for item in HEAVIER:
            # mprint("{}".format(NEIGHBOR_INFO[item]))
            # if node_info['cluster_head'] == str(item) and NEIGHBOR_INFO[item]['cluster_head'] != True:
            #     mprint("cluster head joined another cluster {}, should start looking for a new cluster head".format(NEIGHBOR_INFO[item]['cluster_head']))
            if NEIGHBOR_INFO[item]['cluster_head'] == True:
                mprint("joining {}".format(item))
                joined = True
                node_info['cluster_head'] = str(item)
                node_info['cluster_set'] = []
                tagged.objective.value = cbor.dumps(node_info)
                break
            
        if not joined:
            mprint("I'm cluster head")
            node_info['cluster_head'] = True
            node_info['cluster_set'] = [str(acp._get_my_address())]
            tagged.objective.value = cbor.dumps(node_info)
