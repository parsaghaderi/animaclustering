import os
import random
import threading
import cbor
import subprocess as sp
try:
    import graspi
    _old_API = False

except:
    _old_API = True
    import grasp as graspi

# try:
#     import graspi
# except:
#     print("Cannot find the RFC API module graspi.py.")
#     print("Will run with only the basic grasp.py module.")
#     try:
#         _old_API = True
#         import grasp as graspi
#     except:
#         print("Cannot import grasp.py")
#         time.sleep(10)
#         exit()

try: 
    import networkx as nx
except:
    print("can't import networkx; installing networkx")
    import os
    os.system('python3 -m pip install networkx')

MAP_PATH = '/etc/TD_map/neighbors.map'

#########################
#check grasp
#########################
try:
    graspi.checkrun
except:
    #not running under ASA loader
    graspi.tprint("========================")
    graspi.tprint("ASA server is starting up.")
    graspi.tprint("========================")


#########################
# utility function for reading info from map; 
# later this info will be received from ACP
#########################
def readmap(path):
    file = open(path)
    l = file.readlines()
    l = [str(int(item)) for item in l]
    return l[0], l[1:]


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



import subprocess as sp
from time import sleep

asa, err = ASA_REG('domain1')
obj, err = OBJ_REG('node', None, True, False, 10, asa)
tagged = TAG_OBJ(obj, asa)
def listen_neg(_tagged):
    while True:
        err, handle, answer = graspi.listen_negotiate(_tagged.source, _tagged.objective)
        if not err:
            pass
        else:
            mprint("listen negotiation err {}".format(graspi.etext[err]))
        sleep(3)

def discovery(tag):
    while True:
        err, ll = graspi.discover(tag.source, tag.objective, 10000, False)
        if (not err) and (len(ll) != 0):
            print("##################")
            for item in ll:
                print(item.locator)
            print("##################")
        sleep(5)
    
threading.Thread(target=listen_neg, args = [tagged]).start()
threading.Thread(target=discovery, args=[tagged]).start()