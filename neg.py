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

READ_LOCK = False
WRITE_LOCK = False

#########################
# utility function for reading info from map; 
# later this info will be received from ACP
#########################
def readmap(path):
    file = open(path)
    l = file.readlines()
    l = [str(int(item)) for item in l]
    return l[0], l[1:]

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



import subprocess as sp
from time import sleep
NEIGHBOR_LOCATORS = set()
NEIGHBOR_weights = {}
asa, err = ASA_REG('domain1')

obj, err = OBJ_REG('node', None, True, False, 10, asa)
tagged = TAG_OBJ(obj, asa)

node, err = OBJ_REG('node_info', cbor.dumps(get_node_value()), True, False, 10, asa)
tagged_node = TAG_OBJ(node, asa)


def listen_neg_ND(_tagged):
    while True:
        err, handle, answer = graspi.listen_negotiate(_tagged.source, _tagged.objective)
        if not err:
            pass
        else:
            mprint("listen negotiation err {}".format(graspi.etext[err]))
        sleep(3)

def discovery(tag):
    while True:
        err, ll = graspi.discover(tag.source, tag.objective, 10000, True)
        if (not err) and (len(ll) != 0):
            for item in ll:
                NEIGHBOR_LOCATORS.add(item)
        sleep(5)

def listen_node_info_handler(_tagged, handle, answer):
    answer.value = cbor.loads(answer.value)
    NEIGHBOR_weights[str(handle.locator)] = answer.value
    answer.value = _tagged.objective.value
    answer.value = cbor.dumps(answer.value)
    _r = graspi.negotiate_step(_tagged.source, handle, answer, 10000)
    if _old_API:
        err, temp, answer = _r
        reason = answer
    else:
        err, temp, answer, reason = _r
    if (not err) and (temp == None):
        mprint("neg ended, from {} weight {} received".format(handle.locator, NEIGHBOR_weights[str(handle.locator)] ))
    

def listen_neg_node_info(_tagged):
    while True:
        err, handle, answer = graspi.listen_negotiate(
            _tagged.source,
            _tagged.objective, 
        )
        if not err:
            threading.Thread(target=listen_node_info_handler, 
                             args=[_tagged, handle, answer]
            )

def request_neg_node_info(_tagged, handler):
    if _old_API:
        err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.obj, handler, None) #TODO
        reason = answer
    else:
        err, handle, answer, reason = graspi.req_negotiate(_tagged.source,_tagged.obj, handler, None)
    if not err:
        answer.value = cbor.loads(answer.value)
        NEIGHBOR_weights[str(handle.locator)] = answer.value
        _err = graspi.end_negotiate(_tagged.source, handle, True, reason="Got weights")
        if not _err:
            mprint("neg ended, from {} weight {} received".format(handle.locator, NEIGHBOR_weights[str(handle.locator)]))

def send_req_node_info(_tagged):
    for item in NEIGHBOR_LOCATORS:
        threading.Thread(target=request_neg_node_info, args=[_tagged, item]).start()
    

threading.Thread(target=listen_neg_ND, args = [tagged]).start()
threading.Thread(target=discovery, args=[tagged]).start()
def print_neighbors():
    for i in range(1, 20):
        for item in NEIGHBOR_LOCATORS:
            print(item.locator)
        print("----------------------------")
        sleep(5)
threading.Thread(target=print_neighbors, args=[]).start()

threading.Thread(target=listen_neg_node_info, args=[tagged_node]).start()
threading.Thread(target=send_req_node_info, args=[tagged_node]).start()



