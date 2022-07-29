from ast import Pass
from os import stat
from utility import *
from utility import _old_API as _old_API


'''
NEIGHBORS str(item.locator)
NEIGHBOR_STR to stor ula addresses as string
NEIGHBOR_DATA to store neighbor information
HEAVIER to store heavier neighbors ()
HEAVIEST to store the heaviest neighbor ()
LIGHTER to store lighter neighbors ()
'''

NEIGHBORS_STR = []
NEIGHBOR_STR_TO_LOCATOR = {}
NEIGHBOR_INFO = {} #TODO change

HEAVIER = {}
LIGHTER = {}
HEAVIEST = None

CLUSTER_HEAD = False
INITIAL_NEG = False
CLUSTERING_DONE = False
SYNCH = False
TO_JOIN = None

CLUSTER_STR_TO_ULA = {}
CLUSTER_NODES = {}
CLUSTER_INFO  = {}
CLUSTER_UPDATE = {}
TP_MAP = {}
MAP_SEM = threading.Semaphore()

PHASE = 0

TMP_CLUSTER_VERSION = None
SYNCH_COUNTER = 0
SENT_TO_CLUSTERHEADS = {}
UPDATE = False
'''
# node_info['weight'] is run once, that's why we don't need a tmp variable to store node's weight
# status 1:not decided, 2:cluster-head, 3:want to join, 4:joined 5:changed (!)
'''


asa, err = ASA_REG('node_neg')
asa2, err = ASA_REG('cluster_neg')

node_info = {'weight':get_node_value(),
             'cluster_head':False, 'cluster_set':[], 'neighbors':NEIGHBORS_STR, 
             'status': 1, 'ports':{'cluster':0, 'obj':0, 'sub_cluster':0}} 

obj, err, node_info['ports']['obj'] = OBJ_REG('node', None, True, False, 10, asa, False)
tagged   = TAG_OBJ(obj, asa)
tagged_sem = threading.Semaphore()

cluster_obj1, err, node_info['ports']['cluster'] = OBJ_REG("cluster_head", cbor.dumps(TP_MAP), True, False, 10, asa, False)
cluster_tagged = TAG_OBJ(cluster_obj1, asa)
cluster_tagged_sem = threading.Semaphore()

sub_cluster_obj, err, node_info['ports']['sub_cluster'] = OBJ_REG("sub_cluster", cbor.dumps(TP_MAP), True, False, 10, asa, False)
sub_cluster_tagged = TAG_OBJ(sub_cluster_obj, asa)
cluster_tagged_sem = threading.Semaphore()

obj.value = cbor.dumps(node_info)

def listen_handler(_tagged, _handle, _answer):
    initiator_ula = str(ipaddress.IPv6Address(_handle.id_source))
    tmp_answer = cbor.loads(_answer.value)
    #mprint("req_neg initial value : peer {} offered {}".format(initiator_ula, tmp_answer))
    NEIGHBOR_INFO[initiator_ula] = tmp_answer
    if node_info['cluster_set'].__contains__(initiator_ula):
        mprint("*\n&\n*\n&\n*\n&\n*\n&\n*\n&\n*\n&\n")
    
    tagged_sem.acquire()
    if tmp_answer['cluster_head'] == str(MY_ULA) and (not node_info['cluster_set'].__contains__(initiator_ula)):
        node_info['cluster_set'].append(initiator_ula)
        mprint(node_info, 2)
        _tagged.objective.value = cbor.dumps(node_info)
    _answer.value = _tagged.objective.value
    tagged_sem.release()
    try:
        _r = graspi.negotiate_step(_tagged.source, _handle, _answer, 10000)
        if _old_API:
            err, temp, answer = _r
            reason = answer
        else:
            err, temp, answer, reason = _r
        if (not err) and (temp == None):
            mprint("\033[1;32;1m negotiation with peer {} ended successfully \033[0m".format(initiator_ula))  
        else:
            mprint("\033[1;31;1m in listen handler - neg with peer {} interrupted with error code {} \033[0m".format(initiator_ula, graspi.etext[err]))
            pass
    except Exception as err:
        mprint("\033[1;31;1m exception in linsten handler {} \033[0m".format(err))

def discovery_node_handler(_tagged, _locators):
    for item in _locators:
        if str(item.locator) not in NEIGHBOR_STR_TO_LOCATOR:
            NEIGHBOR_STR_TO_LOCATOR[str(item.locator) ] = item
            NEIGHBORS_STR.append(str(item.locator))
            NEIGHBOR_INFO[str(item.locator)] = 0
            tagged_sem.acquire()
            _tagged.objective.value = cbor.dumps(node_info)
            tagged_sem.release()
    mprint(NEIGHBORS_STR, 2)
    sleep(10)
    threading.Thread(target=run_neg, args=[_tagged, NEIGHBOR_INFO.keys(), 1, 1]).start()

listen_node_1 = threading.Thread(target=listen, args=[tagged, listen_handler]) #TODO change the name
listen_node_1.start()

discovery_1 = threading.Thread(target=discovery, args=[tagged,discovery_node_handler, 2])
discovery_1.start()

def run_neg(_tagged, _locators, _next, _attempts = 1):
    global INITIAL_NEG, PHASE
    
    for item in _locators:
        threading.Thread(target=neg, args=[_tagged, item, _attempts]).start()
    sleep(10) #TODO check if can be reduced
    INITIAL_NEG = True
    PHASE = _next

def neg(_tagged, ll, _attempt):
    attempt = _attempt
    while attempt!=0:
        mprint("start negotiating with {} for {}th time - try {}".format(ll, attempt, _attempt-attempt+1),2)
        if _old_API:
            err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, NEIGHBOR_STR_TO_LOCATOR[ll], 10000) #TODO
            reason = answer
        else:
            err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, NEIGHBOR_STR_TO_LOCATOR[ll], None)
        if not err:
            mprint("\033[1;32;1m got answer form peer {} on try {}\033[0m".format(ll, _attempt-attempt+1),2)
            NEIGHBOR_INFO[ll] = cbor.loads(answer.value)#√
            mprint("neg_step value : peer {} offered {}".format(ll, NEIGHBOR_INFO[ll]))#√
            
            if NEIGHBOR_INFO[ll]['cluster_head'] == str(MY_ULA): #√
                tagged_sem.acquire()
                tagged.objective.value = cbor.loads(tagged.objective.value)
                if not node_info['cluster_set'].__contains__(ll):
                    node_info['cluster_set'].append(ll)
                tagged.objective.value = cbor.dumps(node_info)
                tagged_sem.release()
                mprint(node_info, 2)
            try:
                _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
                if not _err:
                    mprint("\033[1;32;1m neg with {} ended successfully\033[0m".format(ll),2)
                    break
                else:
                    mprint("\033[1;31;1m in neg_end error happened {} \033[0m".format(graspi.etext[_err]),2)
            except Exception as e:
                mprint("\033[1;31;1m in neg_neg exception happened {} \033[0m".format(e),2)
        else:
            mprint("\033[1;31;1m in neg_req - neg with {} failed + {} \033[0m".format(ll, graspi.etext[err]),2)
            attempt+=1
        attempt-=1
        sleep(3)
    


def control():
    while True:
        if PHASE == 1:
            mprint("starting phase 0 - init")
            init_thread = threading.Thread(target=init, args = [2])
            init_thread.start()
            init_thread.join()
        elif PHASE == 2:
            run_neg_thread = threading.Thread(target=run_neg, args=[tagged, NEIGHBOR_INFO.keys(),3, 1])
            run_neg_thread.start()
            run_neg_thread.join()
        elif PHASE == 3:
            work_on_update_thread = threading.Thread(target = on_update_rcv, args=[4])
            work_on_update_thread.start()
            work_on_update_thread.join()
        elif PHASE == 4:
            run_neg_thread = threading.Thread(target=run_neg, args=[tagged, NEIGHBOR_INFO.keys(),5, 1])
            run_neg_thread.start()
            run_neg_thread.join()
        elif PHASE == 5:
            work_on_update_thread = threading.Thread(target = on_update_rcv, args=[6])
            work_on_update_thread.start()
            work_on_update_thread.join()
            mprint("\033[1;35;1m DONE \033[0m")
            if CLUSTER_HEAD == True:
                mprint("\033[1;35;1m I'm cluster head \033[0m")
                threading.Thread(target=generate_topology, args=[]).start()
                sleep(20)
                cluster_discovery_1.start()
            else:
                mprint("\033[1;35;1m I joined {} \033[0m".format(node_info['cluster_head']))
        elif PHASE == 6:
            # mprint("entering maintenance phase")
            # maintenance_thread = threading.Thread(target=maintenance, args = []).start()
            pass

# threading.Thread(target=control, args = []).start()