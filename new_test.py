import grasp
import time
import subprocess as sp
import threading
# if sp.getoutput('hostname') == 'Gingko':
def gremlin():
    print("Starting GRASP daemon")
    grasp._initialise_grasp()
    grasp.init_bubble_text("GRASP daemon")
    grasp.tprint("Daemon running")
    while True:
        time.sleep(60)
# if sp.getoutput('hostname') == 'Gingko':
#     gremlin()


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

asa, err = ASA_REG('test')
obj, err = OBJ_REG('obj', None, True, False, 10, asa)
tagged   = TAG_OBJ(obj, asa)

def listen(_tagged):
    mprint("start listening")
    while True:
        while True:
            err, handle, answer = graspi.listen_negotiate(_tagged.source, _tagged.objective)
            if not err:
                pass
            else:
                mprint(graspi.etext[err])


def discovery(_tagged):
    mprint("start discovery")
    while True:
        err, ll = graspi.discover(_tagged.source, _tagged.objective, 500000, flush=True)
        if (not err) and len(ll) != 0:
            for item in ll:
                mprint(str(item.locator))
        sleep(2)

if sp.getoutput('hostname') == 'Dijkstra':
    while True:
        threading.Thread(target=discovery, args=[tagged]).start()       
        sleep(3)
if sp.getoutput('hostname') == 'Gingko':
    grasp._initialise_grasp()
    grasp.init_bubble_text("GRASP daemon")
    grasp.tprint("Daemon running")
    while True:
        time.sleep(60)

if sp.getoutput('hostname') == 'Ritchie' or sp.getoutput('hostname') == 'Tarjan':
    threading.Thread(target=listen, args=[tagged])