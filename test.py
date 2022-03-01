from base64 import decode
import os
import random
import threading
import cbor
import subprocess as sp
from time import sleep
import grasp
try:
    import graspi
    _old_API = False

except:
    _old_API = True
    import grasp as graspi
import acp
mprint(acp._get_my_address())
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
obj, err = OBJ_REG('node', cbor.dumps(get_node_value()), True, False, 10, asa)
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
    mprint("handling request from {}".format(handle.id_value))
    answer.value = cbor.loads(answer.value)
    mprint("peer offered {}".format(answer.value))
    #TODO do something with the answer
    answer.value = _tagged.objective.value
    answer.value = cbor.dumps(answer.value)
    _r = graspi.negotiate_step(_tagged.source, handle, answer, 10000)
    if _old_API:
        err, temp, answer = _r
        reason = answer
    else:
        err, temp, answer, reason = _r
    if (not err) and (temp == None):
        mprint("neg ended with reason {}".format(reason))
    else:
        mprint(graspi.etext[err])

def request_neg(_tagged, ll):
    mprint("requestion objective {}".format(_tagged.objective.name))
    if _old_API:
        err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, ll, None) #TODO
        reason = answer
    else:
        err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, ll, None)

    if not err:
        mprint("peer offered {}".format(cbor.loads(answer.value)))
        #TODO use the value here
        _err = graspi.end_negotiate(_tagged.source, handle, True, "neg finished")
        if not _err:
            mprint("neg finished successfully")
        else:
            mprint("error in ending negotiation {}".format(graspi.etext[_err]))
    else:
        mprint("can't make neg request {}".format(graspi.etext[err]))

def discovery(_tagged):
    while True:
        err, ll = graspi.discover(_tagged.source, _tagged.objective, 10000)
        if (not err) and len(ll) != 0:
            for item in ll:
                mprint("node {} has objective {}".format(item.locator, _tagged.objective.name))
            break
        else:
            mprint(graspi.etext[err])
        sleep(3)
    threading.Thread(target=request_neg, args=[_tagged, ll[0]]).start()

if sp.getoutput('hostname') == "Dijkstra":
    threading.Thread(target=listener, args = [tagged]).start()
elif sp.getoutput('hostname') == "Ritchie":
    threading.Thread(target = discovery, args=[tagged]).start()
else:
    while True:
        grasp._initialise_grasp()
        while True:
            sleep(5)
