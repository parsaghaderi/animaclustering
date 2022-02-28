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

def discovery(_tagged):
    # while True:
    for i in range(1, 3):
        err, ll = graspi.discover(_tagged.source, _tagged.objective, 10000, True)
        if (not err) and (len(ll) != 0):
            for item in ll:
                flag = False
                for neighbors in NEIGHBOR_LOCATORS:
                    if item.locator == neighbors.locator:
                        flag = True
                if not flag:
                    NEIGHBOR_LOCATORS.add(item)
        mprint(NEIGHBOR_LOCATORS)        
        sleep(1)   
    send_req_node_info(_tagged)
        

def listen_node_info_handler(_tagged, handle, answer):
    mprint("handling request from {}".format(cbor.loads(handle.id_source).decode("utf-8")))
    answer.value = cbor.loads(answer.value)
    # NEIGHBOR_weights[str(handle.locator)] = answer.value
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
    else:
        mprint(graspi.etext[err])

def listen_neg_node_info(_tagged):
    mprint("listening for incoming requests")
    while True:
        
        err, handle, answer = graspi.listen_negotiate(
            _tagged.source,
            _tagged.objective, 
        )
        if not err:
            mprint("openening a new thread {}".format(cbor.loads(answer.value)))
            threading.Thread(target=listen_node_info_handler, 
                             args=[_tagged, handle, answer]
            ).start()
        else:
            mprint(graspi.etext[err])
        sleep(3)

def request_neg_node_info(_tagged, handler):
    mprint("negotiation with {}".format(handler.locator))
    mprint("requesting {}".format(_tagged.objective.name))
    if _old_API:
        err, handle, answer = graspi.request_negotiate(_tagged.source,_tagged.objective, handler, None) #TODO
        reason = answer
    else:
        err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, handler, None)
    if not err:
        answer.value = cbor.loads(answer.value)
        mprint(answer.value)
        NEIGHBOR_weights[str(handle.locator)] = answer.value
        _err = graspi.end_negotiate(_tagged.source, handle, True, reason="Got weights")
        if not _err:
            mprint("neg ended, from {} weight {} received".format(handle.locator, NEIGHBOR_weights[str(handle.locator)]))
        else:
            mprint(graspi.etext[err])
def send_req_node_info(_tagged):
    for item in NEIGHBOR_LOCATORS:
        threading.Thread(target=request_neg_node_info, args=[_tagged, item]).start()
    

# threading.Thread(target=listen_neg_ND, args = [tagged_node]).start()
# sleep(10)
# threading.Thread(target=discovery, args=[tagged_node]).start()
def print_neighbors():
    for i in range(1, 5):
        for item in NEIGHBOR_LOCATORS:
            print("----------------------------")
            print(item.locator)
            print("----------------------------")

        print(len(NEIGHBOR_LOCATORS))
        sleep(3)
    send_req_node_info(tagged_node)
# threading.Thread(target=print_neighbors, args=[]).start()
import subprocess as sp
if sp.getoutput('hostname') == 'Dijkstra':
    threading.Thread(target=listen_neg_node_info, args=[tagged_node]).start()
elif sp.getoutput('hostname') == 'Gingko':
    threading.Thread(target=discovery, args = [tagged_node]).start()
    # threading.Thread(target=request_neg_node_info, args=[tagged_node, None]).start()
# threading.Thread(target=send_req_node_info, args=[tagged_node]).start()
# send_req_node_info(tagged_node)



