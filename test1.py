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
from subprocess import Popen, PIPE




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
        pass
threading.Thread(target=gremlin, args=[]).start()

obj, err = OBJ_REG('node', cbor.dumps(get_node_value()), True, False, 10, asa)
tagged   = TAG_OBJ(obj, asa)

def listen(_tagged):
    while True:
        err, handle, answer = graspi.listen_negotiate(_tagged.source, _tagged.objective)
        if not err:
            mprint("incoming request")
            # threading.Thread(target=listener_handler, args=[_tagged, handle, answer]).start()
        else:
            mprint(graspi.etext[err])

def listener_handler(_tagged, _handle, _answer):
    mprint("req_neg initial value : peer offered {}".format(cbor.loads(_answer.value)))
    _answer.value = _tagged.objective.value
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
    attempt = 5
    while attempt != 0:
        _, ll = graspi.discover(_tagged.source,_tagged.objective, 10000, flush=True)
        mprint(len(ll))
        for item in ll:
            mprint("asking {}".format(item.locator))
            # threading.Thread(target=neg, args=[_tagged, item]).start()
            sleep(5)
        attempt-=1

def neg(_tagged, ll):
    if _old_API:
        err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, ll, None) #TODO
        reason = answer
    else:
        err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, ll, None)
    if not err:
        mprint("neg_step value : peer {} offered {}".format(ll.locator, cbor.loads(answer.value)))
        _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
    else:
        mprint("neg failed")
        _err = graspi.end_negotiate(_tagged.source, handle, False, "value not received")


if sp.getoutput('hostname') == 'Dijkstra':
    tagged.objective.value = cbor.dumps(10)
    threading.Thread(target=listen, args=[tagged]).start()
    threading.Thread(target=discover, args=[tagged]).start()

if sp.getoutput('hostname') == 'Ritchie':
    tagged.objective.value = cbor.dumps(20)
    threading.Thread(target=listen, args=[tagged]).start()
    threading.Thread(target=discover, args=[tagged]).start()

if sp.getoutput('hostname') == 'Gingko':
    tagged.objective.value = cbor.dumps(30)
    threading.Thread(target=listen, args=[tagged]).start()
    threading.Thread(target=discover, args=[tagged]).start()
