import os
import random
import threading
import cbor

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

NEIGHBOR_LOCATORS = []

def get_my_neighbors():
    file = open('/etc/TD_neighbor/locators')
    l = file.readlines()
    l = [item.strip('\n') for item in l]
    mprint(l)
    file.close()
    return l[0], l[1:]

IFI, NEIGHBOR = get_my_neighbors()
# mprint("IFI {}".format(IFI))
# mprint("neighbor locators {}".format(NEIGHBOR))

ifi_info = {}
ifi_info[IFI] = NEIGHBOR
# mprint(ifi_info)
def get_node_value():
    rand = random.random()
    num_neighbors = len(NEIGHBOR)
    return num_neighbors*rand
    
asa, err = ASA_REG('asa')
obj, err = OBJ_REG('node', [ifi_info, get_node_value()], True, False, 10, asa)
tagged_node = TAG_OBJ(obj, asa)

# mprint(obj.value)
# def discover_neighbors(tagged_node):
#     err, ll = graspi.discover(tagged_node.source,
#                             tagged_node.objective,
#                             10000,
#                             flush = False)
#     mprint(len(ll))
#     if (not err) and len(ll)> 0:
#         for item in ll:
#             if NEIGHBOR.__contains__(str(item.locator)):
#                 NEIGHBOR_LOCATORS.append(item)
#                 print(str(item.locator))
# def req_neg(tagged, ll):
#     tagged.objective.value = cbor.dumps(tagged.objective.value)
#     if _old_API:
#         err, handle, answer = graspi.req_negotiate(
#                                     tagged.source,
#                                     tagged.objective,
#                                     ll,
#                                     None)
#         reason = answer
#     else:
#         err, handle, answer, reason = graspi.req_negotiate(
#                                     tagged.source, 
#                                     tagged.objective, 
#                                     ll, 
#                                     None)


# def lis_neg(tagged, handle, answer, old_API):
#     answer.value = cbor.loads(answer.value)
#     mprint(answer.value)
#     mprint(str(handle.handler))
#     err = graspi.end_negotiate(tagged.source, handle, True)
#     if not err:
#         mprint("neg ended successfully")
def listen_neg(tagged):
    while True:
        mprint("listening for incoming neg requests!")
        err, handle, answer = graspi.listen_negotiate(tagged.source, tagged.objective)
        if not err:
            pass
        
            #threading.Thread(target= lis_neg, args=[tagged, handle, answer, _old_API])
        sleep(3)

threading.Thread(target=listen_neg, args=[tagged_node]).start()
# threading.Thread(target=discover_neighbors, args=[tagged_node]).start()





