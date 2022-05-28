import random
import threading
import cbor
import subprocess as sp
from time import sleep
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


def check_alive(_neighbors):
    req = multiping.MultiPing(_neighbors)
    req.send()
    _available, _not_available = req.receive(5)
    return _available, _not_available


def listen(_tagged, _handler):
    mprint("start listening for objective {}".format(_tagged.objective.name))
    while True:
        err, handle, answer = graspi.listen_negotiate(_tagged.source, 
                                                      _tagged.objective)       
        if not err:
            mprint("\033[1;32;1m incoming request \033[0m")
            threading.Thread(target=_handler, args=[_tagged,handle,answer]).start()
        else:
            mprint("\033[1;31;1m in listen error {} \033[0m" .format(graspi.etext[err]))