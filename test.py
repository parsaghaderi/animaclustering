import random
import threading
import cbor
import subprocess as sp
from time import sleep
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


asa, err = ASA_REG("test")
obj1, err = OBJ_REG("test_obj", 10, True, False, 10, asa)
tagged_1 = TAG_OBJ(obj1, asa)
# obj2, err = OBJ_REG("test_obj2", 20, True, False, 10, asa)
# tagged_2 = TAG_OBJ(obj2, asa)

def listen(_tagged, _phase = 0):
    while True:
        err, handle, answer = graspi.listen_negotiate(_tagged.source, _tagged.objective)
        if not err:
            mprint("incoming request")
            if _tagged.objective.name == 'node':
                pass
            else:
                pass
        else:
            mprint("\033[1;31;1m in listen error {} \033[0m" .format(graspi.etext[err]))

def discover(_tagged, _attempt=3, _phase=0):
    global NEIGHBOR_INFO
    attempt = _attempt
    while attempt != 0:
        _, ll = graspi.discover(_tagged.source,_tagged.objective, 10000, flush=True, minimum_TTL=50000)
        mprint(len(ll))
        sleep(2)
        attempt-=1
    for items in ll:
        mprint("obj {}, locator {}".format(_tagged.objective.name, str(items.locator)))


threading.Thread(target=listen, args=[tagged_1]).start()      

if sp.getoutput('hostname') == 'Dijkstra':


    obj2, err = OBJ_REG("test_obj2", 20, True, False, 10, asa)
    tagged_2 = TAG_OBJ(obj2, asa)
    threading.Thread(target=listen, args=[tagged_2]).start()      
    threading.Thread(target=discover, args=[tagged_1]).start()
    sleep(20)
    threading.Thread(target=discover, args=[tagged_2]).start()

if sp.getoutput('hostname') == 'Gingko':
    threading.Thread(target=discover, args=[tagged_1]).start()

if sp.getoutput('hostname') == 'Ritchie':
    threading.Thread(target=discover, args=[tagged_1]).start()

if sp.getoutput('hostname') == 'Tarjan':
    obj2, err = OBJ_REG("test_obj2", 20, True, False, 10, asa)
    tagged_2 = TAG_OBJ(obj2, asa)
    threading.Thread(target=listen, args=[tagged_2]).start()
    threading.Thread(target=discover, args=[tagged_1]).start()
    sleep(20)
    threading.Thread(target=discover, args=[tagged_2]).start()

if sp.getoutput('hostname') == 'Iverson':
    threading.Thread(target=discover, args=[tagged_1]).start()

if sp.getoutput('hostname') == 'Backus':
    obj2, err = OBJ_REG("test_obj2", 20, True, False, 10, asa)
    tagged_2 = TAG_OBJ(obj2, asa)
    threading.Thread(target=listen, args=[tagged_2]).start()
    threading.Thread(target=discover, args=[tagged_1]).start()
    sleep(20)
    threading.Thread(target=discover, args=[tagged_2]).start()