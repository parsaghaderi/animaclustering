import time
import os
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
        return err, asa_handle
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

old_API = _old_API

err, asa = ASA_REG('testing')

obj_synch, err = OBJ_REG('test_synch', None, False, True ,50, asa)
tagged_synch   = TAG_OBJ(obj_synch, asa)
obj_neg,   err = OBJ_REG('test_neg',   None, True , False,50, asa)
tagged_neg     = TAG_OBJ(obj_neg, asa)

def get_name():
    return sp.getoutput('hostname')


def flooder(tagged):
    while True:
        err = graspi.flood(tagged.source, 59000, [graspi.tagged_objective(tagged.objective, None)])
        if not err:
            mprint("flooding objective {}'s role".format(tagged.objective.name))
        else:
            mprint("can't flood because {}".format(graspi.etext[err]))
        sleep(1.5)


def negotiate_listener_side(tagged, handle, answer, old):
    old_API = old
    answer.value=cbor.loads(answer.value)
    if answer.dry:
        mprint("Dry run")
        result = True
        reason = None
        
    elif answer.value < 100:
        step = 1
        neg_loop = True
        mprint("peer offered {} - step {}".format(answer.value, step))
        answer.value += 1 #based on grasp doc page 12 comment section paragraph 5 line 2
        answer.value=cbor.dumps(answer.value)
        
        while neg_loop:
            neg_step_output = graspi.negotiate_step(tagged.source, handle, answer, 1000)
            if old_API:
                err, temp, answer = neg_step_output #TODO figure out whats each of them 
                reason = answer
            else:
                err, temp, answer, reason = neg_step_output
            answer.value = cbor.loads(answer.value)
            mprint("peer offered {} {} {} {}".format(err, temp, answer, reason))
            step += 1
            if not err:
                if answer.value < 88:
                    answer.value += 1
                if answer.value >= 88:
                   break
            else:
                mprint("err {}".format(graspi.etext[err]))
                neg_loop = False
                break
            # if (not err) and temp == None:
            #     err = graspi.end_negotiate(tagged.source, handle, True)
            #     if not err:
            #         neg_loop = False
            #         mprint("negotiation succeeded")
            # elif not err:
            #     try:
            #         answer.value = cbor.loads(answer.value)
            #     except:
            #         pass
            mprint("loop count {}, request {}".format(answer.loop_count, answer.value))
            answer.value = cbor.dumps(answer.value)
            
        err = graspi.end_negotiate(tagged.source, handle, True)
        if not err:
            mprint("negotiation done with value {}".format(answer.value))
            tagged.objective.value = answer.value
    else:
        err = graspi.end_negotiate(tagged.source, handle, True)
        if not err:
            mprint("negotiation done with value {}".format(answer.value))
                
            
def negotiate_request_side(tagged, old):
    while True:
        _, ll = graspi.discover(tagged.source, tagged.objective, 1000, flush = True)

        if ll == []:
            mprint("discovery failed, no handlers found")
            continue
        mprint("{} locators found, locator {} was chosen".format(len(ll), ll[0].locator))
        tagged.objective.value = cbor.dumps(tagged.objective.value)
        if _old_API:
            err, handle, answer = graspi.request_negotiate(tagged.source, tagged.objective, ll[0], None)
            reason = answer
        else:
        # err, handle, answer, reason = graspi.req_negotiate(tagged.source, tagged.objective, ll[0], None)
            err, handle, answer ,reason = graspi.request_negotiate(tagged.source, tagged.objective, ll[0], None)
        if err:
            mprint("neg request failed because {}".format(graspi.etext[err]))
            continue
        elif (not err) and handle:
            answer.value = cbor.loads(answer.value)
            mprint("session started {}, answer {}".format(handle, answer))
            # try:
            #     answer.value = cbor.loads(answer.value)
            # except:
            #     pass
            mprint("peer offered {}".format(answer.value))
            step = 1
            if answer.value < 100:
                answer.value += 1
                neg_loop = True
                while neg_loop:
                    answer.value = cbor.dumps(answer.value)
                    _r = graspi.negotiate_step(tagged.source, handle, answer, 1000)
                    if old_API:
                        err, temp, answer = _r
                        reason = answer
                    else:
                        err, temp, answer, reason = _r
                    # mprint("loopcount {}, offered {}".format(answer.loop_count, answer.value))
                    if (not err):
                        answer.value = cbor.loads(answer.value)
                        mprint("peer offered {}".format(answer.value))
                        step += 1
                        if answer.value > 80:
                            err, graspi.end_negotiate(tagged.source, handle, True)
                            if not err:
                                mprint("negotiation successfully done!")
                                neg_loop = False
                            break
                            
                        elif answer.value < 100:
                            answer.value += 1
        else:
            neg_loop = False
            break
        






def listen_neg(tagged):
    while True:
        err, handle, answer = graspi.listen_negotiate(tagged.source, tagged.objective)
        if not err:
            if answer.value != tagged.objective.value:
                threading.Thread(target=negotiate_listener_side, args=[tagged, handle, answer, old_API]).start()
            else: #answer == obj.value no need for negotiation
                pass #end negotiation
        if err:
            mprint("listen negotiation err {}".format(graspi.etext[err]))
            break

        sleep(3)


def synch(tagged):
    while True:
        err, result = graspi.synchronize(
                    tagged.source,
                    tagged.objective,
                    None, 
                    59000
                    )      
        if not err:
            mprint("synch successful with value {}".format(result.value))
        sleep(3)


if get_name() == 'Dijkstra':
    obj_synch.value = 'Dijkstra_synch'
    obj_neg.value = 1
    threading.Thread(target=flooder,    args = [tagged_synch]).        start()
    threading.Thread(target=listen_neg, args = [tagged_neg])  .        start()

if get_name() == 'Ritchie':
    threading.Thread(target=synch,      args = [tagged_synch]).        start()

if get_name() == 'Gingko':
    tagged_neg.objective.value = 50
    threading.Thread(target=negotiate_request_side, args=[tagged_neg, old_API]).start()

