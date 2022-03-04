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
            pass
        else:
            mprint(graspi.etext[err])

def discover(_tagged):
        _, ll = graspi.discover(_tagged.source,_tagged.objective, 10000, flush=False)
        if len(ll) != 0:
            mprint(str(ll[0].locator))

if sp.getoutput('hostname') == 'Dijkstra':
    threading.Thread(target=listen, args=[tagged]).start()
if sp.getoutput('hostname') == 'Gingko':
    threading.Thread(target=discover, args=[tagged]).start()
