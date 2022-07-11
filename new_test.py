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
listen_sub = None


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
    #mprint("req_neg initial value : peer {} offered {}".format(initiator_ula, tmp_answer))
    NEIGHBOR_INFO[NEIGHBOR_STR_TO_LOCATOR[initiator_ula]] = tmp_answer
    if node_info['cluster_set'].__contains__(initiator_ula):
        mprint("*\n&\n*\n&\n*\n&\n*\n&\n*\n&\n*\n&\n")
    tagged_sem.acquire()
    if tmp_answer['cluster_head'] == str(MY_ULA):
        node_info['cluster_set'].append(initiator_ula)
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
            NEIGHBOR_INFO[item] = 0
            tagged_sem.acquire()
            _tagged.objective.value = cbor.dumps(node_info)
            tagged_sem.release()
    mprint(NEIGHBORS_STR)
    sleep(10)
    threading.Thread(target=run_neg, args=[tagged, NEIGHBOR_INFO.keys(), 1, 1]).start()

def discovery_cluster_handler(_tagged, _locators, _next = 6):
    for item in _locators:
        if str(item.locator) != MY_ULA:
            CLUSTER_INFO[item] = 0
            CLUSTER_UPDATE[str(item.locator)] = False
            CLUSTER_STR_TO_ULA[str(item.locator)] = item
            mprint("cluster head found at {}".format(str(item.locator)))
    sleep(10)
    mprint("")
    # threading.Thread(target=run_cluster_neg, args=[_tagged, CLUSTER_INFO.keys(),0, 1]).start()

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
    global HEAVIER, HEAVIEST, LIGHTER, node_info, INITIAL_NEG, TO_JOIN, CLUSTER_HEAD, PHASE, CLUSTERING_DONE
    
    while not INITIAL_NEG:
        pass
    
    mprint("entering init phase - deciding role")
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
        cluster_listen_1.start()
    PHASE = _next      

def on_update_rcv(_next):
    mprint("\033[1;35;1m *********************** 1\033[0m")

    global node_info, CLUSTERING_DONE, SYNCH, CLUSTER_HEAD, PHASE, HEAVIEST, HEAVIER, TO_JOIN
    if CLUSTERING_DONE:
        #already sent the updates
        PHASE = _next
        return
    if HEAVIEST != None:
        if NEIGHBOR_INFO[HEAVIEST]['cluster_head'] == True:
            mprint("\033[1;35;1m ####################### 1\033[0m")
            mprint("\033[1;35;1m Joining {} 1\033[0m".format(HEAVIEST.locator))
            tagged_sem.acquire()
            CLUSTERING_DONE = True
            node_info['cluster_head'] = str(HEAVIEST.locator)
            node_info['cluster_set'] = []
            node_info['status'] = 4
            tagged.objective.value = cbor.dumps(node_info)
            mprint("\033[1;35;1m {} 1\033[0m".format(cbor.loads(tagged.objective.value)))
            tagged_sem.release()
            mprint(NEIGHBOR_INFO)
            CLUSTERING_DONE = True
            PHASE = _next
        elif NEIGHBOR_INFO[HEAVIEST]['cluster_head'] != True and NEIGHBOR_INFO[HEAVIEST]['status'] == 4:
            mprint("\033[1;35;1m &&&&&&&&&&&&&&&&&&&&&& 1\033[0m")
            tmp_ch = find_next_heaviest(HEAVIEST, HEAVIER) #TODO check
            mprint("\033[1;35;1m finding next heaviest 1\033[0m")
            while tmp_ch!=None:
                mprint("\033[1;35;1m ^^^^^^^^^^^^^^^^^^^ 1\033[0m")
                if NEIGHBOR_INFO[tmp_ch]['cluster_head'] == True and NEIGHBOR_INFO[tmp_ch]['status'] == 2:
                    mprint("\033[1;35;1m Joining next heaviest{} 1\033[0m".format(HEAVIEST.locator))
                    tagged_sem.acquire()
                    CLUSTERING_DONE = True
                    node_info['cluster_head'] = str(tmp_ch.locator)
                    node_info['cluster_set'] = []
                    node_info['status'] = 4
                    tagged.objective.value = cbor.dumps(node_info)
                    mprint("\033[1;35;1m {} 1\033[0m".format(cbor.loads(tagged.objective.value)))
                    tagged_sem.release()
                    mprint(NEIGHBOR_INFO)
                    PHASE = _next
                    break
                elif NEIGHBOR_INFO[tmp_ch]['cluster_head'] != True and NEIGHBOR_INFO[tmp_ch]['status'] == 4:
                    mprint("\033[1;35;1m next heaviest 1\033[0m")
                    tmp_ch = find_next_heaviest(tmp_ch, HEAVIER)
                elif NEIGHBOR_INFO[tmp_ch]['cluster_head'] != True and ( NEIGHBOR_INFO[tmp_ch]['status'] == 1 or NEIGHBOR_INFO[tmp_ch]['status'] == 3):
                    #wait for an update message
                    mprint("\033[1;35;1m waiting for update from tmp_heaviest node1\033[0m")
                    PHASE = _next
                    break

            if tmp_ch == None:
                mprint("\033[1;35;1m $$$$$$$$$$$$$$$$$$$$$$$$$$ 1\033[0m")

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
                PHASE = _next
                cluster_listen_1.start()

def generate_topology():
    global TP_MAP
    tmp_map = {}
    tmp_tagged = cbor.loads(tagged.objective.value)
    if len(tmp_tagged['cluster_set']) != 0:
        for item in tmp_tagged['cluster_set']:
            for locators in NEIGHBOR_INFO:
                if item == str(locators.locator) and item != MY_ULA:
                    tmp_map[item] = NEIGHBOR_INFO[locators]['neighbors']
        tmp_map.update({str(MY_ULA):node_info['neighbors']})
        mprint("\033[1;36;1m topology of the cluster is \n{} \033[0m".format(tmp_map))
        TP_MAP = {MY_ULA:tmp_map}
        cluster_tagged_sem.acquire()
        cluster_tagged.objective.value = cbor.dumps(TP_MAP)
        cluster_tagged_sem.release()
        sleep(15)
        #cluster_discovery_1.start()
    else:
       pass 

def cluster_listener_handler(_tagged, _handle, _answer):
    mprint("@@@@@@@@@@\n{}\n@@@@@@@@@@".format(type(_handle)))
    initiator_ula = str(ipaddress.IPv6Address(_handle.id_source))
    tmp_answer = cbor.loads(_answer.value)
    mprint("req_neg initial cluster value: peer {} offered {}".format(initiator_ula, tmp_answer))
    cluster_tagged_sem.acquire()
    if CLUSTER_STR_TO_ULA.__contains__(initiator_ula):
        CLUSTER_INFO[CLUSTER_STR_TO_ULA[initiator_ula]] = tmp_answer
    TP_MAP.update(tmp_answer)
    cluster_tagged.objective.value =  cbor.dumps(TP_MAP)
    _answer.value = cluster_tagged.objective.value
    cluster_tagged_sem.release()
    try:
        _r = graspi.negotiate_step(_tagged.source, _handle, _answer, 10000)
        if _old_API:
            err, temp, answer = _r
            reason = answer
        else:
            err, temp, answer, reason = _r
        if (not err) and (temp == None):
            SENT_TO_CLUSTERHEADS[initiator_ula] = TP_MAP
            mprint("\033[1;32;1m cluster negotiation with peer {} ended successfully \033[0m".format(initiator_ula))  
        else:
            mprint("\033[1;31;1m in cluster listen handler - neg with peer {} interrupted with error code {} \033[0m".format(initiator_ula, graspi.etext[err]))
            pass
    except Exception as err:
        mprint("\033[1;31;1m exception in cluster linsten handler {} \033[0m".format(err))

def run_cluster_neg(_tagged, _locators, _next, _attempts = 1):
    global PHASE
    # for i in range(len(_locators)):
    for item in _locators:
        threading.Thread(target=neg_cluster, args = [_tagged, item, _attempts]).start()
    sleep(20)
    mprint("topology of the domain  - phase 1\n{}".format(TP_MAP))
    # PHASE = _next
    threading.Thread(target=check_to_update_clusterhead, args=[_tagged]).start()

    # sleep(15)
    # mprint("topology after 1 round of neg \n{}".format(TP_MAP))
    # PHASE = _next

def neg_cluster(_tagged, ll, _attempt):
    attempt = _attempt
    while attempt!= 0:
        mprint("start cluster negotiating with {} for {}th time - try {}".format(str(ll.locator), attempt, _attempt-attempt+1))
        if _old_API:
            err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, ll, 10000) #TODO
            reason = answer
        else:
            err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, ll, None)
        if not err:
            SENT_TO_CLUSTERHEADS[str(ll.locator)] = TP_MAP

            mprint("\033[1;32;1m got answer form peer {} on try {}\033[0m".format(str(ll.locator), _attempt-attempt+1))
            CLUSTER_INFO[ll] = cbor.loads(answer.value)
            # mprint("cluster_neg_step value : peer {} offered {}".format(str(ll.locator), CLUSTER_INFO[ll]))#
            cluster_tagged_sem.acquire()
            TP_MAP.update(cbor.loads(answer.value))
            cluster_tagged.objective.value = cbor.dumps(TP_MAP)
        
            cluster_tagged_sem.release()
            try:
                mprint("\033[1;32;1m replying to {} \033[0m".format(str(ll.locator)))
                _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
                if not _err:
                    mprint("\033[1;32;1m cluster neg with {} ended successfully\033[0m".format(str(ll.locator)))
                    break
                else:
                    mprint("\033[1;31;1m in cluster_neg_end error happened {} \033[0m".format(graspi.etext[_err]))
            except Exception as e:
                mprint("\033[1;31;1m in cluster_neg_neg exception happened {} \033[0m".format(e))
            
        else:
            mprint("\033[1;31;1m in cluster_neg_req - neg with {} failed + {} \033[0m".format(str(ll.locator), graspi.etext[err]))
            if attempt == 1:
                break
        attempt-=1
        sleep(3)

listen_node_1 = threading.Thread(target=listen, args=[tagged, listen_handler]) #TODO change the name
listen_node_1.start()

discovery_1 = threading.Thread(target=discovery, args=[tagged,discovery_node_handler, 2])
discovery_1.start()

cluster_listen_1 = threading.Thread(target=listen, args=[cluster_tagged, cluster_listener_handler])
cluster_discovery_1 = threading.Thread(target=discovery, args=[cluster_tagged,discovery_cluster_handler, 3])

def check_to_update_clusterhead(_tagged, _next = 0):
    global UPDATE, PHASE
    # for k in CLUSTER_INFO:
    #     if SENT_TO_CLUSTERHEADS[str(k.locator)] != TP_MAP:
    #         UPDATE = True

    # if UPDATE:
    threading.Thread(target=run_cluster_neg, args=[_tagged, CLUSTER_INFO.keys(),0, 3]).start()
    sleep(5)
    # else:
    #     mprint("No changes")
    #     PHASE = 0
    # UPDATE = False
    
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
            pass

threading.Thread(target=control, args = []).start()