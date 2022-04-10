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

asa, err = ASA_REG('node_neg')

############
# keep running
############
def gremlin():
    while True:
        sleep(1)
threading.Thread(target=gremlin, args=[]).start()

##########
# MY_ULA str
# NEIGHBOR_ULA list[str]
##########
MY_ULA, NEIGHBOR_ULA = get_neighbors() 


##########
# NEIGHBOR_INFO dict locator:json
##########
NEIGHBOR_INFO = {}

##########
# dict to map str(locator) -> locator; then can be used to access neighbor_info
##########
NEIGHBOR_LOCATOR_STR = {}

##########
# ?
##########
NEIGHBOR_UPDATE = {} 

########Flags#######
CLUSTER_HEAD = False
INITIAL_NEG = False
CLUSTERING_DONE = False
SYNCH = False


##########
# node_info['weight'] is run once, that's why we don't need a tmp variable to store node's weight
# status 1:not decided, 2:cluster-head, 3:want to join, 4:joined 5:changed (!)
##########
node_info = {'ula':str(acp._get_my_address()), 'weight':get_node_value(),
             'cluster_head':False, 'cluster_set':[], 'neighbors':NEIGHBOR_ULA, 
             'status': 1} 
obj, err = OBJ_REG('node', cbor.dumps(node_info), True, False, 10, asa)
# tag_lock = True
tagged   = TAG_OBJ(obj, asa)
tagged_sem = threading.Semaphore()


##########
# @param _tagged, a tagged objective to listen for
##########
def listen(_tagged):
    while True:
        err, handle, answer = graspi.listen_negotiate(_tagged.source, _tagged.objective)
        if not err:
            mprint("incoming request")
            threading.Thread(target=listener_handler, args=[_tagged, handle, answer]).start()
        else:
            mprint("\033[1;31;1m in listen error {} \033[0m" .format(graspi.etext[err]))
threading.Thread(target=listen, args=[tagged]).start()

###########
# @param _tagged tagged objective listening for
# @param _handle handler for the incoming request
# @param _answer offered answer from neg peer
###########
def listener_handler(_tagged, _handle, _answer):
    global tag_lock
    tmp_answer = cbor.loads(_answer.value)
    mprint("req_neg initial value : peer offered {}".format(tmp_answer))#√
    #TODO get info from the answer
    #we already know the dict of neighbor_info has been created!
    ###########
    while len(NEIGHBOR_INFO)!=len(NEIGHBOR_ULA): #why? 
        pass
    NEIGHBOR_INFO[NEIGHBOR_LOCATOR_STR[tmp_answer['ula']]] =  tmp_answer
    # for item in NEIGHBOR_INFO:#TODO just deleted
    #     if str(item.locator) == tmp_answer['ula']:
    #         NEIGHBOR_INFO[item] = tmp_answer
    ############
    
    # while not tag_lock:#TODO just deleted
    #     mprint("stuck here in listen handler")
    #     pass
    # tag_lock = False
    tagged_sem.acquire()
    _answer.value = _tagged.objective.value #TODO can be optimized by using the info in request (answer) - just deleted
    tagged_sem.release()
    # tag_lock = True #TODO just deleted
    try:
        _r = graspi.negotiate_step(_tagged.source, _handle, _answer, 10000)
        if _old_API:
            err, temp, answer = _r
            reason = answer
        else:
            err, temp, answer, reason = _r
        if (not err) and (temp == None):
            pass
        else:
            mprint("\033[1;31;1m in listen handler - neg with peer interrupted with error code {} \033[0m".format(graspi.etext[err]))
            pass
    except Exception as err:
        mprint("\033[1;31;1m exception in linsten handler {} \033[0m".format(err))

###########
# @param _tagged tagged objective trying to discover 
# @param _attempt number of attempts before start negotiating
###########
def discover(_tagged, _attempt=3, _phase=1):
    if _phase == 1:
        global NEIGHBOR_INFO
        attempt = 3
        while attempt != 0:
            _, ll = graspi.discover(_tagged.source,_tagged.objective, 10000, flush=True, minimum_TTL=50000)
            mprint(len(ll))
            attempt-=1
        for item in ll:
            NEIGHBOR_INFO[item] = 0
            NEIGHBOR_LOCATOR_STR[str(item.locator)] = item
        threading.Thread(target=run_neg, args=[tagged, NEIGHBOR_INFO.keys(), _attempt]).start()
        mprint(NEIGHBOR_LOCATOR_STR)
    #TODO for maintenance you have to do something!
threading.Thread(target=discover, args=[tagged, 1]).start()

############
# run neg for initial step of exchanging information w/ neighbors
############
def run_neg(_tagged, _locators, _attempts = 1):
    global INITIAL_NEG
    while len(NEIGHBOR_INFO)!=len(NEIGHBOR_ULA):
        pass
    for item in _locators:
        # mprint(item.locator)
        threading.Thread(target=neg, args=[_tagged, item, _attempts]).start()
    while list(NEIGHBOR_INFO.values()).__contains__(0):
        pass
    sleep(15)
    show()
    INITIAL_NEG = True

############
# @param _tagged tagged objective for negotiating over
# @param ll locator of the peer
# @param _attempt number of attempts for negotiating 
############
def neg(_tagged, ll, _attempt):
    global NEIGHBOR_INFO, tag_lock, MY_ULA
    _try = 1
    # if _attempt!=3:
    #     mprint("start negotiation with non-default attempt {}".format(ll.locator))
    attempt = _attempt
    while attempt!=0:
        mprint("start negotiating with {} for {}th time - try {}".format(ll.locator, attempt, _try))
        if _old_API:
            err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, ll, 10000) #TODO
            reason = answer
        else:
            err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, ll, None)
            if not err:
                mprint("\033[1;32;1m got answer form {} on {}th try\033[0m".format(str(ll.locator), _try))
                NEIGHBOR_INFO[ll] = cbor.loads(answer.value)#√
                mprint("neg_step value : peer {} offered {}".format(str(ll.locator), NEIGHBOR_INFO[ll]))#√
                
                if NEIGHBOR_INFO[ll]['cluster_head'] == str(MY_ULA): #√
                    if not node_info['cluster_set'].__contains__(str(ll.locator)):
                        node_info['cluster_set'].append(str(ll.locator))
                    while not tag_lock:
                        mprint("stuck here in neg")
                        pass
                    tag_lock = False
                    _tagged.objective.value = cbor.dumps(node_info)
                    tag_lock = True
                    NEIGHBOR_UPDATE[ll.locator] = True
                try:
                    _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
                    if not _err:
                        mprint("\033[1;32;1m neg with {} ended \033[0m".format(str(ll.locator)))
                    else:
                        mprint("\033[1;31;1m in neg_end error happened {} \033[0m".format(graspi.etext[_err]))
                except Exception as e:
                    mprint("\033[1;31;1m in neg_neg exception happened {} \033[0m".format(e))
            else:
                mprint("\033[1;31;1m in neg_req - neg with {} failed + {} \033[0m".format(str(ll.locator), graspi.etext[err]))
                attempt+=1
        # try:
        #     err = graspi.end_negotiate(_tagged.source, handle, False, "value not received")
        #     if err:
        #         mprint("\033[1;31;1m in neg error happened {} \033[0m".format(graspi.etext[err]))
        # except Exception as e:
        #     mprint("\033[1;31;1m in neg exception happened {} \033[0m".format(e))
        attempt-=1
        _try += 1
        sleep(3)


def show():
    mprint("clustering done")
    mprint("\033[1;36;1m {} \033[0m".format(cbor.loads(tagged.objective.value)))
    mprint("\033[1;33;1m {} \033[0m".format(NEIGHBOR_INFO))
