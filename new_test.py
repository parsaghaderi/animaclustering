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
CLUSTER_INFO = {}
CLUSTER_INFO_KEYS = []
CLUSTER_NODES = {}

TP_MAP = {}
MAP_SEM = threading.Semaphore()

PHASE = 0

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
    mprint("req_neg initial value : peer {} offered {}".format(initiator_ula, tmp_answer))#√
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
    threading.Thread(target=run_neg, args=[tagged, NEIGHBOR_INFO.keys(), 1, 1]).start()


def discovery_cluster_handler(_tagged, _locators):
    for item in _locators:
        if str(item.locator) != MY_ULA:
            CLUSTER_INFO[str(item.locator)] = 0
            CLUSTER_INFO_KEYS.append(item)
            mprint("cluster head found at {}".format(str(item.locator)))
    threading.Thread(target=run_clustering_neg, args=[_tagged, CLUSTER_INFO_KEYS, 1]).start()


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

    # if HEAVIEST != None:
    # tmp_ch = find_next_heaviest(HEAVIEST, HEAVIER)
    # if  tmp_ch == None:
    #     mprint("tmp_ch == None")
    # else:
    #     while tmp_ch != None:
    #         mprint("new tmp_locator is {}".format(str(tmp_ch.locator)))
    #         tmp_ch = find_next_heaviest(tmp_ch, HEAVIER)
    
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
        # listen_sub.start() #TODO how to stop
    # else:
    #     mprint("I want to join {}".format(HEAVIEST.locator))
    #     TO_JOIN = HEAVIEST
    #     tagged_sem.acquire()
    #     tagged.objective.value = cbor.loads(tagged.objective.value)
    #     tagged.objective.value['cluster_head'] = False #to let lighter nodes know I'm not ch
    #     tagged.objective.value['status'] = 3
    #     tagged.objective.value['cluster_set']  = []
    #     tagged.objective.value = cbor.dumps(tagged.objective.value)
    #     tagged_sem.release()
    #     tagged_sem.acquire()
    #     mprint(cbor.loads(tagged.objective.value))
    #     tagged_sem.release()
    #     mprint(list(NEIGHBOR_INFO.values()))
    # sleep(10) #TODO check if can be reduced
    PHASE = _next

    # INITIAL_NEG = False
    # threading.Thread(target=run_neg, args=[tagged, NEIGHBOR_INFO.keys(), 1]).start()
    # while not INITIAL_NEG:
    #     pass

def on_update_rcv(_next):
    mprint("\033[1;35;1m *********************** 1\033[0m")

    global node_info, CLUSTERING_DONE, SYNCH, CLUSTER_HEAD, PHASE, HEAVIEST, HEAVIER, TO_JOIN
    if CLUSTERING_DONE:
        #already sent the updates
        PHASE = 0
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
            
            


# def on_update_rcv():
    # global node_info, CLUSTERING_DONE, SYNCH, CLUSTER_HEAD, PHASE
    # if TO_JOIN == None:
    #     mprint("I'm clusterhead")
    #     tagged_sem.acquire()
    #     CLUSTERING_DONE = True 
    #     CLUSTER_HEAD = True   
    #     mprint("\033[1;35;1m I'm in update rcv - I'm cluster head 1\033[0m")
    #     node_info['cluster_head'] = True
    #     if not node_info['cluster_set'].__contains__(MY_ULA):
    #         node_info['cluster_set'].append(MY_ULA)
    #     node_info['status'] = 2
    #     # node_info = tagged.objective.value
    #     tagged.objective.value = cbor.dumps(node_info)
    #     mprint("\033[1;35;1m {} 1\033[0m".format(cbor.loads(tagged.objective.value)))
    #     tagged_sem.release()
    #     mprint(NEIGHBOR_INFO)
    #     PHASE = 2
    # else:
    #     if NEIGHBOR_INFO[TO_JOIN]['cluster_head'] == True and NEIGHBOR_INFO[TO_JOIN]['status']==2: #TODO check if it works with only one of the conditions
    #         mprint("\033[1;35;1m Joining {} 1\033[0m".format(HEAVIEST.locator))
    #         mprint("\033[1;35;1m I'm in on update rcv - joining 1\033[0m")
    #         tagged_sem.acquire()
    #         CLUSTERING_DONE = True
    #         node_info['cluster_head'] = str(TO_JOIN.locator)
    #         node_info['cluster_set'] = []
    #         node_info['status'] = 4
    #         tagged.objective.value = cbor.dumps(node_info)
    #         mprint("\033[1;35;1m {} 1\033[0m".format(cbor.loads(tagged.objective.value)))
    #         tagged_sem.release()
    #         mprint(NEIGHBOR_INFO)
    #         PHASE = 2
    #     else:
    #         mprint("\033[1;35;1m HEAVIER  = {} 1\033[0m".format(HEAVIER))
    #         tmp_ch = find_next_heaviest(HEAVIEST, HEAVIER)
    #         while tmp_ch != None:
    #             if NEIGHBOR_INFO[tmp_ch]['cluster_head'] == True:
    #                 mprint("Joining {}".format(str(tmp_ch.locator)))
    #                 mprint("\033[1;35;1m I'm in on update rcv - joining 2\033[0m")
    #                 tagged_sem.acquire()
    #                 node_info["cluster_head"] = str(tmp_ch.locator)
    #                 node_info["cluster_set"] = []
    #                 node_info['status'] = 4
    #                 tagged.objective.value = cbor.dumps(node_info)
    #                 mprint("\033[1;35;1m {} 1\033[0m".format(cbor.loads(tagged.objective.value)))
    #                 tagged_sem.release()
    #                 mprint(NEIGHBOR_INFO)
    #                 CLUSTERING_DONE = True
    #                 PHASE = 2
    #                 break
    #             elif NEIGHBOR_INFO[tmp_ch]['status'] == 1 or NEIGHBOR_INFO[tmp_ch]['status'] != 3:
    #                 mprint("can't decide now!")
    #                 PHASE = 3
    #                 break
                    
                
    #             #     mprint("\033[1;31;1m fucked up situation {} \033[0m")
    #             #     tmp_ch = find_next_heaviest(tmp_ch, HEAVIER) #TODO check how we can stick in the loop
    #             #     mprint("trying next heaviest node")
    #             else:
    #                 tmp_ch = find_next_heaviest(tmp_ch, HEAVIER) #TODO check how we can stick in the loop
    #                 mprint("trying next heaviest node")
    #         if tmp_ch == None:    
    #             mprint("I'm clusterhead")
    #             tagged_sem.acquire()
    #             CLUSTERING_DONE = True 
    #             CLUSTER_HEAD = True   
    #             mprint("\033[1;35;1m I'm in update rcv - I'm cluster head 1\033[0m")
    #             node_info['cluster_head'] = True
    #             if not node_info['cluster_set'].__contains__(MY_ULA):
    #                 node_info['cluster_set'].append(MY_ULA)
    #             node_info['status'] = 2
    #             # node_info = tagged.objective.value
    #             tagged.objective.value = cbor.dumps(node_info)
    #             mprint("\033[1;35;1m {} 1\033[0m".format(cbor.loads(tagged.objective.value)))
    #             tagged_sem.release()
    #             mprint(NEIGHBOR_INFO)
    #             PHASE = 2


# def update_3_step():
#     pass

listen_1 = threading.Thread(target=listen, args=[tagged, listen_handler]) #TODO change the name
listen_1.start()

discovery_1 = threading.Thread(target=discovery, args=[tagged,discovery_node_handler, 2])
discovery_1.start()

# init_1 = threading.Thread(target=init, args = [])
# init_1.start()

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
            work_on_update_thread = threading.Thread(target = on_update_rcv, args=[0])
            work_on_update_thread.start()
            work_on_update_thread.join()
            mprint("\033[1;35;1m DONE 1\033[0m")
threading.Thread(target=control, args = []).start()
