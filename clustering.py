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
CLUSTERHEAD_OBJECTIVE = {'map':TP_MAP, 'port':0}
PHASE = 0

CLUSTERHEADS_VERSIONS = {}

TMP_CLUSTER_VERSION = None
SYNCH_COUNTER = 0
SENT_TO_CLUSTERHEADS = {}
UPDATE = False

SUBCLUSTERS = {}
CLUSTERHEADS = {}

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
CLUSTERHEAD_OBJECTIVE['port'] = node_info['ports']['cluster']

sub_cluster_obj, err, node_info['ports']['sub_cluster'] = OBJ_REG("sub_cluster", cbor.dumps(TP_MAP), True, False, 10, asa, False)
sub_cluster_tagged = TAG_OBJ(sub_cluster_obj, asa)
sub_cluster_sem = threading.Semaphore()

obj.value = cbor.dumps(node_info)
cluster_tagged.objective.value  = cbor.dumps(CLUSTERHEAD_OBJECTIVE)

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
        SUBCLUSTERS[initiator_ula] = locator_maker(initiator_ula, NEIGHBOR_INFO[initiator_ula]['ports']['sub_cluster'],False)
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

def cluster_listener_handler(_tagged, _handle, _answer):
    initiator_ula = str(ipaddress.IPv6Address(_handle.id_source))
    tmp_answer = cbor.loads(_answer.value)
    mprint("req_neg initial cluster value: peer {} offered {}".format(initiator_ula, tmp_answer), 2)
    cluster_tagged_sem.acquire()
    
    if list(CLUSTER_INFO.keys()).__contains__(initiator_ula):
        CLUSTER_INFO[initiator_ula] = tmp_answer
        CLUSTER_UPDATE[initiator_ula] = False
        if not list(CLUSTERHEADS.keys()).__contains__(initiator_ula):
            CLUSTERHEADS[initiator_ula] = locator_maker(initiator_ula, tmp_answer['port'], False)
            CLUSTER_STR_TO_ULA[initiator_ula] = CLUSTERHEADS[initiator_ula]

    TP_MAP.update(tmp_answer['map'])
    CLUSTERHEAD_OBJECTIVE['map'].update(tmp_answer['map'])
    cluster_tagged.objective.value =  cbor.dumps(CLUSTERHEAD_OBJECTIVE)
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

def discovery_cluster_handler(_tagged, _locators):
    global PHASE
    for item in _locators:
        if str(item.locator) != MY_ULA:
            CLUSTER_INFO[str(item.locator)] = 0
            CLUSTER_UPDATE[str(item.locator)] = False
            CLUSTER_STR_TO_ULA[str(item.locator)] = item
            CLUSTERHEADS[str(item.locator)] = item
            mprint("cluster head found at {}".format(str(item.locator)), 2)
    sleep(20)
    # threading.Thread(target=maintenance, args=[]).start()
    PHASE = 6

def send_subcluster_update(ll, _attempt):
    global SUBCLUSTERS, sub_cluster_tagged, sub_cluster_sem
    mprint("sending updates for Topology MAP to subcluster ndoe {}".format(ll))
    attempt = _attempt
    while attempt!=0:
        sub_cluster_sem.acquire()
        sub_cluster_tagged.objective.value = cbor.dumps(TP_MAP)
        sub_cluster_sem.release()

        mprint("start negotiating with {} for {}th time - try {}".format(ll, attempt, _attempt-attempt+1),2)
        if _old_API:
            err, handle, answer = graspi.req_negotiate(sub_cluster_tagged.source,sub_cluster_tagged.objective, SUBCLUSTERS[ll], 10000) #TODO
            reason = answer
        else:
            err, handle, answer, reason = graspi.request_negotiate(sub_cluster_tagged.source,sub_cluster_tagged.objective, SUBCLUSTERS[ll], None)

        if not err:
            mprint("subcluster node {} received update and responded with {}".format(ll, cbor.loads(answer.value)))
            try:
                _err = graspi.end_negotiate(sub_cluster_tagged.source, handle, True, reason="value received")
                mprint("successfully ended update negotiation with {}".format(ll))
                return
            except Exception as e:
                mprint("there has been a problem in the communication with subcluster node {}, trying again".format(ll))
                sleep(5)
                attempt-=1

def listen_to_updates_from_clusterhead(_tagged, _handle, _answer):
    tmp_answer = cbor.loads(_answer.value)
    mprint("cluster head sent updates with value {}".format(tmp_answer))
    sub_cluster_sem.acquire()
    TP_MAP.update(tmp_answer)
    _tagged.objective.value = cbor.dumps(TP_MAP)
    _answer.value = _tagged.objective.value
    sub_cluster_sem.release()
    
    try:
        _r = graspi.negotiate_step(_tagged.source, _handle, _answer, 10000)
        if _old_API:
            err, temp, answer = _r
            reason = answer
        else:
            err, temp, answer, reason = _r
        if (not err) and (temp == None):
            mprint("\033[1;32;1m update negotiation with clusterhead ended successfully \033[0m")  
        else:
            mprint("\033[1;31;1m in listen update from clusterhead with clusterhead interrupted with error code {} \033[0m".format(graspi.etext[err]))
            pass
    except Exception as e:
        mprint("\033[1;31;1m exception in linsten update from clusterhead {} \033[0m".format(e))

def listen_to_update_from_subcluster(_tagged, _handle, _answer):
    initiator_ula = str(ipaddress.IPv6Address(_handle.id_source))
    global cluster_tagged_sem, sub_cluster_sem, cluster_tagged, sub_cluster_tagged, TP_MAP
    tmp_answer = cbor.loads(_answer.value)
    
    cluster_tagged_sem.acquire()
    sub_cluster_sem.acquire()
    TP_MAP.update(tmp_answer)
    CLUSTERHEAD_OBJECTIVE['map'].update(tmp_answer['map'])
    cluster_tagged.objective.value =  cbor.dumps(CLUSTERHEAD_OBJECTIVE)
    sub_cluster_tagged.objective.value = cbor.dumps(TP_MAP)
    _answer.value = cluster_tagged.objective.value
    cluster_tagged_sem.release()
    sub_cluster_sem.release()

    try:
        _r = graspi.negotiate_step(_tagged.source, _handle, _answer, 10000)
        if _old_API:
            err, temp, answer = _r
            reason = answer
        else:
            err, temp, answer, reason = _r
        if (not err) and (temp == None):
           
            mprint("\033[1;32;1m update received successfully from subcluster node {}\033[0m".format(initiator_ula))  
        else:
            mprint("\033[1;31;1m in clusterhead listen for update with peer {} interrupted with error code {} \033[0m".format(initiator_ula, graspi.etext[err]))
            pass
    except Exception as e:
        mprint("\033[1;31;1m exception in cluster linsten handler {} \033[0m".format(e))

def send_update_to_clusterhead(_tagged, ll, _attempt):
    attempt = _attempt
    while attempt!=0:
        mprint("start negotiating with {} for {}th time - try {}".format(ll, attempt, _attempt-attempt+1),2)
        if _old_API:
            err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, ll, 10000) #TODO
            reason = answer
        else:
            err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, ll, None)
        if not err:
            mprint("update sent to clusterhead successfully")
            tmp_answer = cbor.loads(answer.value)
            mprint("clusterhead responded with an updated map {}".format(tmp_answer))
            sub_cluster_sem.acquire()
            TP_MAP.update(tmp_answer)
            _tagged.objective.value = cbor.dumps(TP_MAP)
            sub_cluster_sem.release()
            try:
                _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
                if not _err:
                    mprint("\033[1;32;1m sending updates to clusterhead ended successfully\033[0m".format(ll),2)
                    break
                else:
                    mprint("\033[1;31;1m in send update to clusterhead error happened {} \033[0m".format(graspi.etext[_err]),2)
            except Exception as e:
                mprint("\033[1;31;1m in send update to clusterhead exception happened {} \033[0m".format(e),2)
        else:
            mprint("\033[1;31;1m in send_update_to clusterhead failed + {} \033[0m".format(ll, graspi.etext[err]),2)
            attempt+=1
        attempt-=1
        sleep(3)


listen_node_1 = threading.Thread(target=listen, args=[tagged, listen_handler]) #TODO change the name
listen_node_1.start()

discovery_1 = threading.Thread(target=discovery, args=[tagged,discovery_node_handler, 2])
discovery_1.start()

cluster_listen_1 = threading.Thread(target=listen, args=[cluster_tagged, cluster_listener_handler])
cluster_discovery_1 = threading.Thread(target=discovery, args=[cluster_tagged,discovery_cluster_handler, 3])

listen_to_update_from_clusterhead_thread = threading.Thread(target=listen, args=[sub_cluster_tagged, listen_to_updates_from_clusterhead])

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
                SUBCLUSTERS[ll] = locator_maker(ll, NEIGHBOR_INFO[ll]['ports']['sub_cluster'],False)
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
    
def run_cluster_neg_all(_tagged, _next, _attempts = 1):
    global PHASE, CLUSTERHEADS
    # for i in range(len(_locators)):
    for item in CLUSTERHEADS:
        threading.Thread(target=neg_cluster, args = [_tagged, item, _attempts]).start()
    sleep(20)
    mprint("topology of the domain  - phase 1\n{}".format(TP_MAP))
    threading.Thread(target = maintenance, args = []).start()
    PHASE = _next


def neg_cluster(_tagged, ll, _attempt):
    attempt = _attempt
    while attempt!= 0:
        mprint("start cluster negotiating with {} for {}th time - try {}".format(ll, attempt, _attempt-attempt+1))
        try:
            if _old_API:
                err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, CLUSTERHEADS[ll], 10000) #TODO - clustertostr
                reason = answer
            else:
                    err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, CLUSTERHEADS[ll], None)
        except Exception as e:
            mprint("exception in neg_cluster req_neg with {} with code {}".format(ll, graspi.etext[e]), 2)

        if not err:
            SENT_TO_CLUSTERHEADS[ll] = TP_MAP
            tmp_answer = cbor.loads(answer.value)
            mprint("\033[1;32;1m got answer form peer {} on try {}\033[0m".format(ll, _attempt-attempt+1), 2)
            CLUSTER_INFO[ll] = cbor.loads(answer.value)
            # mprint("cluster_neg_step value : peer {} offered {}".format(str(ll.locator), CLUSTER_INFO[ll]))#
            cluster_tagged_sem.acquire()
            TP_MAP.update(tmp_answer['map'])
            CLUSTERHEAD_OBJECTIVE['map'].update(tmp_answer['map'])
            cluster_tagged.objective.value = cbor.dumps(CLUSTERHEAD_OBJECTIVE)
        
            cluster_tagged_sem.release()
            try:
                mprint("\033[1;32;1m replying to {} \033[0m".format(ll))
                _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
                if not _err:
                    mprint("\033[1;32;1m cluster neg with {} ended successfully\033[0m".format(ll), 2)
                    break
                else:
                    mprint("\033[1;31;1m in cluster_neg_end error happened {} \033[0m".format(graspi.etext[_err]), 2)
            except Exception as e:
                mprint("\033[1;31;1m in cluster_neg_neg exception happened {} \033[0m".format(e), 2)
            
        else:
            mprint("\033[1;31;1m in cluster_neg_req - neg with {} failed + {} \033[0m".format(ll, graspi.etext[err]), 2)
            if attempt == 1:
                break
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
        if not cluster_listen_1.is_alive():
            cluster_listen_1.start()
    else:
        mprint("I'm not the heaviest")
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
            mprint("\033[1;35;1m Joining {} 1\033[0m".format(HEAVIEST))
            tagged_sem.acquire()
            CLUSTERING_DONE = True
            node_info['cluster_head'] = str(HEAVIEST)
            node_info['cluster_set'] = []
            node_info['status'] = 4
            tagged.objective.value = cbor.dumps(node_info)
            mprint("\033[1;35;1m {} 1\033[0m".format(cbor.loads(tagged.objective.value)))
            tagged_sem.release()
            mprint(NEIGHBOR_INFO)
            CLUSTERING_DONE = True
            if PHASE < 5:
                PHASE = _next
            else:
                if CLUSTER_HEAD:
                    PHASE = 6
                else:
                    PHASE = 7
        elif NEIGHBOR_INFO[HEAVIEST]['cluster_head'] != True and NEIGHBOR_INFO[HEAVIEST]['status'] == 4:
            mprint("\033[1;35;1m &&&&&&&&&&&&&&&&&&&&&& 1\033[0m")
            tmp_ch = find_next_heaviest(HEAVIEST, HEAVIER) #TODO check
            mprint("\033[1;35;1m finding next heaviest 1\033[0m")
            while tmp_ch!=None:
                mprint("\033[1;35;1m ^^^^^^^^^^^^^^^^^^^ 1\033[0m")
                if NEIGHBOR_INFO[tmp_ch]['cluster_head'] == True and NEIGHBOR_INFO[tmp_ch]['status'] == 2:
                    mprint("\033[1;35;1m Joining next heaviest{} 1\033[0m".format(HEAVIEST))
                    tagged_sem.acquire()
                    CLUSTERING_DONE = True
                    node_info['cluster_head'] = tmp_ch
                    node_info['cluster_set'] = []
                    node_info['status'] = 4
                    tagged.objective.value = cbor.dumps(node_info)
                    mprint("\033[1;35;1m {} 1\033[0m".format(cbor.loads(tagged.objective.value)))
                    tagged_sem.release()
                    mprint(NEIGHBOR_INFO)
                    if PHASE < 5:
                        PHASE = _next
                    else:
                        if CLUSTER_HEAD:
                            PHASE = 6
                        else:
                            PHASE = 7
                elif NEIGHBOR_INFO[tmp_ch]['cluster_head'] != True and NEIGHBOR_INFO[tmp_ch]['status'] == 4:
                    mprint("\033[1;35;1m next heaviest 1\033[0m")
                    tmp_ch = find_next_heaviest(tmp_ch, HEAVIER)
                elif NEIGHBOR_INFO[tmp_ch]['cluster_head'] != True and ( NEIGHBOR_INFO[tmp_ch]['status'] == 1 or NEIGHBOR_INFO[tmp_ch]['status'] == 3):
                    #wait for an update message
                    mprint("\033[1;35;1m waiting for update from tmp_heaviest node1\033[0m")
                    if PHASE < 5:
                        PHASE = _next
                    else:
                        if CLUSTER_HEAD:
                            PHASE = 6
                        else:
                            PHASE = 7
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
                if not cluster_listen_1.is_alive():
                    cluster_listen_1.start()

def generate_topology():
    global TP_MAP, CLUSTERHEAD_OBJECTIVE
    tmp_map = {}
    tmp_tagged = cbor.loads(tagged.objective.value)
    if len(tmp_tagged['cluster_set']) != 0:
        for item in tmp_tagged['cluster_set']:
            for locators in NEIGHBOR_INFO:
                if item == locators and item != MY_ULA:
                    tmp_map[item] = NEIGHBOR_INFO[locators]['neighbors']
        tmp_map.update({str(MY_ULA):node_info['neighbors']})
        mprint("\033[1;36;1m topology of the cluster is \n{} \033[0m".format(tmp_map))
        cluster_tagged_sem.acquire()
        TP_MAP = {MY_ULA:tmp_map}
        CLUSTERHEAD_OBJECTIVE['map'] = TP_MAP 
        cluster_tagged.objective.value = cbor.dumps(CLUSTERHEAD_OBJECTIVE)
        cluster_tagged_sem.release()
        sleep(15)
        cluster_discovery_1.start()
    else:
       pass 

def maintenance():
    for item in SUBCLUSTERS:
        threading.Thread(target=send_subcluster_update, args = [item, 2]).start()
    # for item in CLUSTERHEADS:
    #     threading.Thread(target=neg_cluster, args=[cluster_tagged, item, 2]).start()
def clusterhead_maintenance():
    while CLUSTER_HEAD:
        for item in CLUSTERHEADS:
            if SENT_TO_CLUSTERHEADS[item] != TP_MAP:
                threading.Thread(target=neg_cluster, args=[cluster_tagged, item, 2]).start()
        sleep(10)

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
                # sleep(20)
                # cluster_discovery_1.start()
            else:
                mprint("\033[1;35;1m I joined {} \033[0m".format(node_info['cluster_head']))
                listen_to_update_from_clusterhead_thread.start()
        elif PHASE == 6:
            mprint("updating clusterheads")
            clusterhead_update_thread = threading.Thread(target=run_cluster_neg_all, args=[cluster_tagged, 7, 2])
            clusterhead_update_thread.start()
            clusterhead_update_thread.join()
            sleep(30)
            threading.Thread(target = clusterhead_maintenance, args = []).start()
            # maintenance_thread = threading.Thread(target=maintenance, args = []).start()
        elif PHASE == 7:
            pass


threading.Thread(target=control, args = []).start()