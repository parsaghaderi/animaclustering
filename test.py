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


asa, err = ASA_REG('neg1')
obj, err = OBJ_REG('node', None, True, False, 10, asa)
tagged   = TAG_OBJ(obj, asa)

def listener(_tagged):
    mprint("listening to incoming requests")
    while True:
        err, handle, answer = graspi.listen_negotiate(_tagged.source, _tagged.objective)
        if not err:
            threading.Thread(target = request_handler, args = [_tagged, handle, answer]).start()
        else:
            mprint(graspi.etext[err])
def request_handler(_tagged, handle, answer):
    pass

def request_neg(_tagged, ll):
    pass

def discovery(_tagged):
    err, ll = graspi.discover(_tagged.source, _tagged.objective, 10000)
    if (not err) and len(ll) != 0:
        for item in ll:
            mprint("node {} has objective {}".format(item.locator, _tagged.objective.name))
    else:
        mprint(graspi.etext[err])

if sp.getoutput('hostname') == "Dijkstra":
    threading.Thread(target=listener, args = [tagged]).start()
else:
    threading.Thread(target = discovery, args=[tagged]).start()