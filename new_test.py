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
CLUSTER_INFO = {}
CLUSTER_INFO_KEYS = []
CLUSTER_NODES = {}

TP_MAP = {}
MAP_SEM = threading.Semaphore()

listen_sub = None


'''
# node_info['weight'] is run once, that's why we don't need a tmp variable to store node's weight
# status 1:not decided, 2:cluster-head, 3:want to join, 4:joined 5:changed (!)
'''
asa, err = ASA_REG('node_neg')
asa2, err = ASA_REG('cluster_neg')

node_info = {'weight':get_node_value(),
             'cluster_head':False, 'cluster_set':[], 'neighbors':NEIGHBORS_STR, 
             'status': 1} 

obj, err = OBJ_REG('node', cbor.dumps(node_info), True, False, 10, asa)
tagged   = TAG_OBJ(obj, asa)
tagged_sem = threading.Semaphore()

cluster_obj1, err = OBJ_REG("cluster_head", cbor.dumps(TP_MAP), True, False, 10, asa)
cluster_tagged = TAG_OBJ(cluster_obj1, asa)
cluster_tagged_sem = threading.Semaphore()

sub_cluster_obj, err = OBJ_REG("sub_cluster", cbor.dumps(TP_MAP), True, False, 10, asa)
sub_cluster_tagged = TAG_OBJ(sub_cluster_obj, asa)
cluster_tagged_sem = threading.Semaphore()


def listen_handler(_tagged, _handle, _answer):
    initiator_ula = str(ipaddress.IPv6Address(_handle.id_source))
    tmp_answer = cbor.loads(_answer.value)
    mprint("req_neg initial value : peer offered {}".format(tmp_answer))#√
    for item in NEIGHBOR_INFO:#TODO just deleted
        if str(item.locator) == str(ipaddress.IPv6Address(_handle.id_source)):
            NEIGHBOR_INFO[item] = tmp_answer
            if node_info['cluster_set'].__contains__(initiator_ula):
                mprint("*\n&\n*\n&\n*\n&\n*\n&\n*\n&\n*\n&\n")
    tagged_sem.acquire()
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
            mprint("\033[1;31;1m in listen handler - neg with peer interrupted with error code {} \033[0m".format(graspi.etext[err]))
            pass
    except Exception as err:
        mprint("\033[1;31;1m exception in linsten handler {} \033[0m".format(err))

def discovery_node_handler(_tagged, _locators):
    for item in _locators:
        if str(item.locator) not in NEIGHBOR_STR_TO_LOCATOR:
            NEIGHBOR_STR_TO_LOCATOR[str(item.locator) ] = item
            NEIGHBORS_STR.append(str(item.locator))
            NEIGHBOR_INFO[item] = 0
            tagged_sem.acquire()
            _tagged.objective.value = cbor.dumps(node_info)
            tagged_sem.release()
    mprint(NEIGHBORS_STR)
    threading.Thread(target=run_neg, args=[tagged, NEIGHBOR_INFO.keys(), 1]).start()


def discovery_cluster_handler(_tagged, _locators):
    for item in _locators:
        if str(item.locator) != MY_ULA:
            CLUSTER_INFO[str(item.locator)] = 0
            CLUSTER_INFO_KEYS.append(item)
            mprint("cluster head found at {}".format(str(item.locator)))
    threading.Thread(target=run_clustering_neg, args=[_tagged, CLUSTER_INFO_KEYS, 1]).start()


def run_neg(_tagged, _locators, _attempts = 1, phase = 1):
    global INITIAL_NEG
    for item in _locators:
        if phase == 1 and NEIGHBOR_INFO[item]!=0:
            mprint("already negotiated with {}".format(str(item.locator)))
            continue
        threading.Thread(target=neg, args=[_tagged, item, _attempts]).start()
    while list(NEIGHBOR_INFO.values()).__contains__(0):
        pass
    sleep(5)
    INITIAL_NEG = True


def neg(_tagged, ll, _attempt, phase = 1):
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
            NEIGHBOR_INFO[ll] = cbor.loads(answer.value)#√
            mprint("neg_step value : peer {} offered {}".format(str(ll.locator), NEIGHBOR_INFO[ll]))#√
            
            if NEIGHBOR_INFO[ll]['cluster_head'] == str(MY_ULA): #√
                tagged_sem.acquire()
                tagged.objective.value = cbor.loads(tagged.objective.value)
                if not node_info['cluster_set'].__contains__(str(ll.locator)):
                    node_info['cluster_set'].append(str(ll.locator))
                tagged.objective.value = cbor.dumps(node_info)
                tagged_sem.release()
            try:
                _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
                if not _err:
                    mprint("\033[1;32;1m neg with {} ended successfully\033[0m".format(str(ll.locator)))
                else:
                    mprint("\033[1;31;1m in neg_end error happened {} \033[0m".format(graspi.etext[_err]))
            except Exception as e:
                mprint("\033[1;31;1m in neg_neg exception happened {} \033[0m".format(e))
        else:
            mprint("\033[1;31;1m in neg_req - neg with {} failed + {} \033[0m".format(str(ll.locator), graspi.etext[err]))
            attempt+=1
        attempt-=1
        sleep(3)
        threading.Thread(target=init, args = []).start()

def init():
    global HEAVIER, HEAVIEST, LIGHTER, node_info
    
    while not INITIAL_NEG:
        pass
    
    mprint("entering init phase - deciding role")
    HEAVIER, HEAVIEST, LIGHTER = sort_weight(node_info['weight'], NEIGHBOR_INFO, HEAVIER, HEAVIEST, LIGHTER)


    
    if find_next_heaviest() == None:
        mprint("tmp_ch == None")
    else:
        while tmp_ch != None:
            mprint("new tmp_locator is {}".format(str(tmp_ch.locator)))
            tmp_ch = find_next_heaviest(tmp_ch, HEAVIER)
    
    if HEAVIEST == None:
        mprint("I'm clusterhead")
        tagged_sem.acquire()
        tagged.objective.value = cbor.loads(tagged.objective.value)
        tagged.objective.value['cluster_head'] = True
        tagged.objective.value['status'] = 2
        if not tagged.objective.value['cluster_set'].__contains__(MY_ULA):
            tagged.objective.value['cluster_set'].append(MY_ULA)
        node_info = tagged.objective.value
        tagged.objective.value = cbor.dumps(tagged.objective.value)
        tagged_sem.release()
        mprint(node_info['weight'])
        mprint(list(NEIGHBOR_INFO.values()))
        TO_JOIN = None
        CLUSTER_HEAD = True
        listen_sub.start() #TODO how to stop
    else:
        mprint("I want to join {}".format(HEAVIEST.locator))
        TO_JOIN = HEAVIEST
        tagged_sem.acquire()
        tagged.objective.value = cbor.loads(tagged.objective.value)
        tagged.objective.value['cluster_head'] = False #to let lighter nodes know I'm not ch
        tagged.objective.value['status'] = 3
        tagged.objective.value['cluster_set']  = []
        tagged.objective.value = cbor.dumps(tagged.objective.value)
        tagged_sem.release()
        tagged_sem.acquire()
        mprint(cbor.loads(tagged.objective.value))
        tagged_sem.release()
        mprint(list(NEIGHBOR_INFO.values()))
    INITIAL_NEG = False
    threading.Thread(target=run_neg, args=[tagged, NEIGHBOR_INFO.keys(), 1]).start()
    while not INITIAL_NEG:
        pass



listen_1 = threading.Thread(target=listen, args=[tagged, listen_handler]) #TODO change the name
listen_1.start()

discovery_1 = threading.Thread(target=discovery, args=[tagged,discovery_node_handler, 2])
discovery_1.start()
