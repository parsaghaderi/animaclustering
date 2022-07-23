from utility import *
from utility import _old_API as _old_API


NEIGHBORS_STR = []
NEIGHBOR_INFO = {} #str to info
NEIGHBOR_STR_TO_LOCATOR = {} #str to ula

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

PHASE = 0
listen_sub = None


SENT_TO_CLUSTERHEADS = {}
UPDATE = False

MAP = None

asa, err = ASA_REG('node_neg')
node_info = {'weight':get_node_value(),
             'cluster_head':False, 'cluster_set':[], 'neighbors':NEIGHBORS_STR, 
             'status': 1} 

obj, err = OBJ_REG('node', cbor.dumps(node_info), True, False, 10, asa)
tagged   = TAG_OBJ(obj, asa)
tagged_sem = threading.Semaphore()

def listen_handler(_tagged, _handle, _answer):
    initiator_ula = str(ipaddress.IPv6Address(_handle.id_source))
    tmp_answer = cbor.loads(_answer.value)
    mprint("req_neg initial value : peer {} offered {}".format(initiator_ula, tmp_answer))
    if NEIGHBORS_STR.__contains__(initiator_ula):
        NEIGHBOR_INFO[initiator_ula] = tmp_answer
    else:
        NEIGHBORS_STR.append(initiator_ula)
        NEIGHBOR_INFO[initiator_ula] = tmp_answer
    if node_info['cluster_set'].__contains__(initiator_ula):
        mprint("update from sub-cluster node\nNode_INFO already updated!")
        
    if tmp_answer['cluster_head'] == str(MY_ULA):
        mprint("\033[1;32;1m neg_initiator selected ME as cluster head \033[0m")
        tagged_sem.acquire()
        node_info['cluster_set'].append(initiator_ula)
        _tagged.objective.value = cbor.dumps(node_info)
        tagged_sem.release()
    _answer.value = _tagged.objective.value
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
    mprint(NEIGHBORS_STR)
    sleep(10)
    threading.Thread(target=run_neg, args=[tagged, NEIGHBOR_INFO.keys(), 1, 1]).start()


def run_neg(_tagged, _locators, _next, _attempts = 1):
    global INITIAL_NEG, PHASE
    neg_threads = []
    for item in _locators:
        neg_threads.append(threading.Thread(target=neg, args=[_tagged, NEIGHBOR_STR_TO_LOCATOR[item], _attempts]))
    for item in neg_threads:
        item.start()
    for item in neg_threads:
        item.join()
    sleep(10) #TODO check if can be reduced
    INITIAL_NEG = True
    PHASE = _next

def neg(_tagged, ll, _attempt):
    attempt = _attempt
    while attempt!=0:
        mprint("start negotiating with {} for {}th time - try {}".format(ll.locator, attempt, _attempt-attempt+1))
        if _old_API:
            err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, ll, 10000) #TODO
            reason = answer
        else:
            err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, ll, None)
        if not err:
            mprint("\033[1;32;1m got answer form peer {} on try {}\033[0m".format(str(ll.locator), _attempt-attempt+1))
            NEIGHBOR_INFO[str(ll.locator)] = cbor.loads(answer.value)#TODO check
            mprint("neg_step value : peer {} offered {}".format(str(ll.locator), NEIGHBOR_INFO[str(ll.locator)]))#√
            
            if NEIGHBOR_INFO[str(ll.locator)]['cluster_head'] == str(MY_ULA): #√
                tagged_sem.acquire()
                # tagged.objective.value = cbor.loads(tagged.objective.value)
                if not node_info['cluster_set'].__contains__(str(ll.locator)):
                    node_info['cluster_set'].append(str(ll.locator))
                    mprint("added a new member to cluster set")
                tagged.objective.value = cbor.dumps(node_info)
                tagged_sem.release()
            if NEIGHBOR_INFO[str(ll.locator)]['cluster_head'] == True and str(ll.locator) == HEAVIEST:
                mprint("\033[1;32;1m joining {}\033[0m".format(str(ll.locator)))
                
            try:
                _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
                if not _err:
                    mprint("\033[1;32;1m neg with {} ended successfully\033[0m".format(str(ll.locator)))
                    break
                else:
                    mprint("\033[1;31;1m in neg_end error happened {} \033[0m".format(graspi.etext[_err]))
            except Exception as e:
                mprint("\033[1;31;1m in neg_neg exception happened {} \033[0m".format(e))
            
        else:
            mprint("\033[1;31;1m in neg_req - neg with {} failed + {} \033[0m".format(str(ll.locator), graspi.etext[err]))
            attempt+=1
        attempt-=1
        sleep(3)

def init(_next):
    global HEAVIER, HEAVIEST, LIGHTER, node_info, TO_JOIN, CLUSTER_HEAD, PHASE, CLUSTERING_DONE #,INITIAL_NEG
    
    # while not INITIAL_NEG:
    #     pass
    
    mprint("\033[1;32;1m  entering init phase - deciding role  {}\033[0m")
    HEAVIER, HEAVIEST, LIGHTER = sort_weight(node_info['weight'], NEIGHBOR_INFO, HEAVIER, HEAVIEST, LIGHTER)

    
    if HEAVIEST == None:
        mprint("I'm clusterhead")
        tagged_sem.acquire()
        node_info['cluster_head'] = True
        node_info['status'] = 2
        if not node_info['cluster_set'].__contains__(MY_ULA):
            node_info['cluster_set'].append(MY_ULA)
        tagged.objective.value = cbor.dumps(node_info)
        tagged_sem.release()
        mprint(node_info['weight'])
        mprint(NEIGHBOR_INFO)
        TO_JOIN = None
        CLUSTER_HEAD = True
        CLUSTERING_DONE = True
        # cluster_listen_1.start()
    PHASE = _next   

listen_node_1 = threading.Thread(target=listen, args=[tagged, listen_handler]) #TODO change the name
listen_node_1.start()

discovery_1 = threading.Thread(target=discovery, args=[tagged,discovery_node_handler, 2])
discovery_1.start()

def control():
    while True:
        if PHASE == 1:
            mprint("starting phase 0 - init")
            init_thread = threading.Thread(target=init, args = [2])
            init_thread.start()
            init_thread.join()
        elif PHASE == 2:
            mprint("in phase 2")
            run_neg_thread = threading.Thread(target=run_neg, args=[tagged, NEIGHBOR_INFO.keys(),6, 1])
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
            pass

threading.Thread(target=control, args = []).start()