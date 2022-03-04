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
        graspi._initialise_grasp()
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


asa, err = ASA_REG('testing')
obj, err = OBJ_REG('obj', None, True, False, 10, asa)
tagged   = TAG_OBJ(obj, asa)

def listen(_tagged):
    while True:
        err, handle, answer = graspi.listen_negotiate(_tagged.source, _tagged.objective)
        if not err:
            threading.Thread(target=listener_handler, args=[_tagged, handle, answer]).start()
        else:
            mprint(graspi.etext[err])

def listener_handler(_tagged, _handle, _answer):
    mprint("peer offered {}".format(cbor.loads(_answer.value)))
    _answer.value = cbor.dumps(_tagged.objective.value)
    _r = graspi.negotiate_step(_tagged.source, _handle, _answer, 10000)
    if _old_API:
        err, temp, answer = _r
        reason = answer
    else:
        err, temp, answer, reason = _r
    if (not err) and (temp == None):
        mprint("peer ended neg with reason {}".format(reason))
    else:
        mprint("neg with peer interrupted with error code {}".format(graspi.etext[err]))


def discover(_tagged):
        _, ll = graspi.discover(_tagged.source,_tagged.objective, 10000, flush=False)
        if len(ll) != 0:
            mprint("asking {}".format(ll[0].locator))
            threading.Thread(target=neg, args=[_tagged, ll[0]]).start()

def neg(_tagged, ll):
    if _old_API:
        err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, ll, None) #TODO
        reason = answer
    else:
        err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, ll, None)
    if not err:
        mprint("peer offered {}".format(cbor.loads(answer.value)))
        _err = graspi.end_negotiate(_tagged.source, handle, True, "value received")
    else:
        mprint("neg failed")
        _err = graspi.end_negotiate(_tagged.source, handle, False, "value not received")
        

if sp.getoutput('hostname') == 'Dijkstra':
    tagged.objective.value = cbor.dumps(10)
    threading.Thread(target=listen, args=[tagged]).start()
if sp.getoutput('hostname') == 'Gingko':
    tagged.objective.value = cbor.dumps(20)
    threading.Thread(target=discover, args=[tagged]).start()
