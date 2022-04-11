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
asa2, err = ASA_REG('cluster_neg')

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

##########
# locator of heavier nodes
##########
HEAVIER = {}
##########
# locator of lighter nodes
##########
LIGHTER = {}
##########
# locator of heaviest node
##########
HEAVIEST = None
########Flags#######
CLUSTER_HEAD = False
INITIAL_NEG = False
CLUSTERING_DONE = False
SYNCH = False
CLUSTERING_DONE = False
SYNCH = False
TO_JOIN = None


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
listen_1 = threading.Thread(target=listen, args=[tagged])
listen_1.start()
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
    # while len(NEIGHBOR_INFO)!=len(NEIGHBOR_ULA): #why? 
    #     pass
    # NEIGHBOR_INFO[NEIGHBOR_LOCATOR_STR[tmp_answer['ula']]] =  tmp_answer
    for item in NEIGHBOR_INFO:#TODO just deleted
        if str(item.locator) == tmp_answer['ula']:
            NEIGHBOR_INFO[item] = tmp_answer
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
discovery_1 = threading.Thread(target=discover, args=[tagged, 1])
discovery_1.start()
############
# run neg for initial step of exchanging information w/ neighbors
############
def run_neg(_tagged, _locators, _attempts = 1):
    global INITIAL_NEG
    # while len(NEIGHBOR_INFO)!=len(NEIGHBOR_ULA): 
    #     pass
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
    global NEIGHBOR_INFO, MY_ULA, node_info
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
                    tagged_sem.acquire()
                    tagged.objective.value = cbor.loads(tagged.objective.value)
                    if not tagged.objective.value['cluster_set'].__contains__(str(ll.locator)):
                        tagged.objective.value['cluster_set'].append(str(ll.locator))
                    node_info = tagged.objective.value
                    tagged.objective.value = cbor.dumps(tagged.objective.value)
                    tagged_sem.release()

                    # if not node_info['cluster_set'].__contains__(str(ll.locator)):TODO just deleted
                    #     node_info['cluster_set'].append(str(ll.locator))
                    # while not tag_lock:
                    #     mprint("stuck here in neg")
                    #     pass
                    # tag_lock = False
                    # tagged_sem.acquire() #TODO just deleted
                    # _tagged.objective.value = tagged.objective.value
                    # tagged_sem.release()
                    # tag_lock = True
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

############
# to show the map and info stored
############
def show():
    mprint("clustering done")
    tagged_sem.acquire()
    mprint("\033[1;36;1m {} \033[0m".format(cbor.loads(tagged.objective.value)))
    tagged_sem.release()
    mprint("\033[1;33;1m {} \033[0m".format(NEIGHBOR_INFO))
    mprint("\033[1;33;1m {} \033[0m".format(INITIAL_NEG))

#############
# sort nodes based on their weights
#############
def sort_weight():
    global NEIGHBOR_INFO, HEAVIER, LIGHTER, HEAVIEST
    my_weight = node_info['weight']
    max_weight = my_weight
    for item in NEIGHBOR_INFO:
        if NEIGHBOR_INFO[item]['weight']> my_weight:
            HEAVIER[item] = NEIGHBOR_INFO[item]['weight']
            if NEIGHBOR_INFO[item]['weight']> max_weight:
                HEAVIEST = item #locator #TODO subject to change if it joins another cluster
                max_weight = NEIGHBOR_INFO[item]['weight']
        else:
            LIGHTER[item] = NEIGHBOR_INFO[item]['weight']

    HEAVIER = dict(sorted(HEAVIER.items(), key=lambda item: item[1], reverse = True))
    mprint("heavier:{}".format(HEAVIER))
    mprint("lighter:{}".format(LIGHTER))
    mprint("heaviest:{}".format(HEAVIEST))


#########
# @param _heaviest takes the current heaviest(locator), return next one in line
# @return locator of the 2nd heaviest node
#########
def find_next_heaviest(_heaviest):
    global HEAVIER, HEAVIEST
    heavier_lst = list(HEAVIER.keys())
    if len(heavier_lst) == 0:
        return None
    if heavier_lst.index(_heaviest) == len(heavier_lst)-1:
        return None
    else:
        index = heavier_lst.index(_heaviest)
        return heavier_lst[index+1]


def init():
    global tagged
    global INITIAL_NEG, TO_JOIN, CLUSTER_HEAD#, HEAVIEST, MY_ULA, MY_ULA #TODO just deleted
    while not INITIAL_NEG:
        pass
    mprint("deciding the role")
    sort_weight()
    tmp_ch = find_next_heaviest(HEAVIEST)
    if tmp_ch == None:
        mprint("tmp_ch == None")
    else:
        while tmp_ch != None:
            mprint("new tmp_locator is {}".format(str(tmp_ch.locator)))
            tmp_ch = find_next_heaviest(tmp_ch)

    if HEAVIEST == None:
        mprint("I'm clusterhead")
        # while not tag_lock: #TODO just deleted
        #     pass
        # tag_lock = False
        tagged_sem.acquire()
        tagged.objective.value = cbor.loads(tagged.objective.value)
        tagged.objective.value['cluster_head'] = True
        tagged.objective.value['status'] = 2
        if not tagged.objective.value['cluster_set'].__contains__(MY_ULA):
            tagged.objective.value['cluster_set'].append(MY_ULA)
        node_info = tagged.objective.value
        tagged.objective.value = cbor.dumps(tagged.objective.value)
        tagged_sem.release()
        # tag_lock = True
        mprint(node_info['weight'])
        mprint(list(NEIGHBOR_INFO.values()))
        TO_JOIN = None
        CLUSTER_HEAD = True
    else:
        mprint("I want to join {}".format(HEAVIEST.locator))
        TO_JOIN = HEAVIEST
        # while not tag_lock:
        #     pass
        # tag_lock = False
        tagged_sem.acquire()
        tagged.objective.value = cbor.loads(tagged.objective.value)
        tagged.objective.value['cluster_head'] = False #to let lighter nodes know I'm not ch
        tagged.objective.value['status'] = 3
        tagged.objective.value['cluster_set']  = []
        tagged.objective.value = cbor.dumps(tagged.objective.value)
        tagged_sem.release()
        # tag_lock = True
        tagged_sem.acquire()
        mprint(cbor.loads(tagged.objective.value))
        tagged_sem.release()
        mprint(list(NEIGHBOR_INFO.values()))
    INITIAL_NEG = False
    threading.Thread(target=run_neg, args=[tagged, NEIGHBOR_INFO.keys(), 1]).start()
    while not INITIAL_NEG:
        pass
    sleep(15)
    threading.Thread(target=on_update_rcv, args=[]).start()
threading.Thread(target=init, args=[]).start() #initial init

def on_update_rcv():
    global node_info, CLUSTERING_DONE, SYNCH, CLUSTER_HEAD #NEIGHBOR_INFO,HEAVIER,HEAVIER,TO_JOIN,tag_lock,
    if TO_JOIN == None:
        mprint("I'm clusterhead")
        # while not tag_lock:
        #     pass
        # tag_lock = False
        tagged_sem.acquire()
        mprint("\033[1;35;1m I'm in update rcv - I'm cluster head 1\033[0m")
        tagged.objective.value = cbor.loads(tagged.objective.value)
        tagged.objective.value['cluster_head'] = True
        if not tagged.objective.value['cluster_set'].__contains__(MY_ULA):
            tagged.objective.value['cluster_set'].append(MY_ULA)
        tagged.objective.value['status'] = 2
        node_info = tagged.objective.value
        tagged.objective.value = cbor.dumps(tagged.objective.value)
        tagged_sem.release()
        # tag_lock = True 
        tagged_sem.acquire()
        mprint(cbor.loads(tagged.objective.value))
        tagged_sem.release()
        mprint(NEIGHBOR_INFO)
        CLUSTERING_DONE = True 
        CLUSTER_HEAD = True    
    else:
        if NEIGHBOR_INFO[TO_JOIN]['cluster_head'] == True and NEIGHBOR_INFO[TO_JOIN]['status']==2:
            mprint("Joining {}".format(HEAVIEST.locator))
            mprint("\033[1;35;1m I'm in on update rcv - joining 1\033[0m")
            # while not tag_lock:
            #         pass
            # tag_lock = False
            tagged_sem.acquire()
            tagged.objective.value = cbor.loads(tagged.objective.value)
            tagged.objective.value['cluster_head'] = str(TO_JOIN.locator)
            tagged.objective.value['cluster_set']  = []
            tagged.objective.value['status'] = 4
            node_info = tagged.objective.value
            tagged.objective.value = cbor.dumps(tagged.objective.value)
            tagged_sem.release()
            # tag_lock = True
            tagged_sem.acquire()
            mprint(cbor.loads(tagged.objective.value))
            tagged_sem.release()
            mprint(NEIGHBOR_INFO)
            CLUSTERING_DONE = True
        
        else:
            mprint(HEAVIER)
            tmp_ch = find_next_heaviest(HEAVIEST)
            if tmp_ch == None:
                mprint("I'm clusterhead")
                mprint("\033[1;35;1m I'm in on update rcv - I'm cluster head 2\033[0m")
                # while not tag_lock:
                #     pass
                # tag_lock = False
                tagged_sem.acquire()
                tagged.objective.value = cbor.loads(tagged.objective.value)
                tagged.objective.value['cluster_head'] = True
                if not tagged.objective.value['cluster_set'].__contains__(MY_ULA):
                    tagged.objective.value['cluster_set'].append(MY_ULA)
                tagged.objective.value['status'] = 2
                node_info = tagged.objective.value
                tagged.objective.value = cbor.dumps(tagged.objective.value)
                tagged_sem.release()
                # tag_lock = True 
                tagged_sem.acquire()
                mprint(cbor.loads(tagged.objective.value))
                tagged_sem.release()
                mprint(NEIGHBOR_INFO)
                CLUSTERING_DONE = True
                CLUSTER_HEAD = True
            else:
                tmp_ch = find_next_heaviest(HEAVIEST)
                while tmp_ch != None:
                    if NEIGHBOR_INFO[tmp_ch]['cluster_head'] == True:
                        mprint("Joining {}".format(str(tmp_ch.locator)))
                        mprint("\033[1;35;1m I'm in on update rcv - joining 2\033[0m")
                        # while not tag_lock:
                        #     pass
                        # tag_lock = False
                        tagged_sem.acquire()
                        tagged.objective.value = cbor.loads(tagged.objective.value)
                        tagged.objective.value['cluster_head'] = str(tmp_ch.locator)
                        tagged.objective.value['cluster_set']  = []
                        tagged.objective.value['status'] = 4
                        node_info = tagged.objective.value
                        tagged.objective.value = cbor.dumps(tagged.objective.value)
                        tagged_sem.release()
                        # tag_lock = True
                        tagged_sem.acquire()
                        mprint(cbor.loads(tagged.objective.value))
                        tagged_sem.release()
                        mprint(NEIGHBOR_INFO)
                        CLUSTERING_DONE = True
                        break
                    else:
                        tmp_ch = find_next_heaviest(tmp_ch) #TODO check how we can stick in the loop
                        mprint("trying next heaviest node")
    sleep(15)
    threading.Thread(target=run_neg, args=[tagged, NEIGHBOR_INFO.keys(), 1]).start()
    SYNCH = True
    sleep(30)
    threading.Thread(target=show, args=[]).start()
    threading.Thread(target=generate_topology, args=[]).start()

def generate_topology():
    # global    #,SYNCH, NEIGHBOR_INFO,MY_ULA,CLUSTER_HEAD
    while not SYNCH:
        pass
    tmp_map = {}
    tmp_tagged = cbor.loads(tagged.objective.value)
    if len(tmp_tagged['cluster_set']) != 0:
        for item in tmp_tagged['cluster_set']:
            for locators in NEIGHBOR_INFO:
                if item == str(locators.locator) and item != MY_ULA:
                    tmp_map[item] = NEIGHBOR_INFO[locators]['neighbors']
        tmp_map.update({node_info['ula']:node_info['neighbors']})
        mprint("\033[1;36;1m topology of the cluster is \n{} \033[0m".format(tmp_map))
        sleep(15)
        threading.Thread(target=run_cluster, args=[]).start()

cluster_obj1, err = OBJ_REG("obj1", cbor.dumps(10), True, False, 10, asa2)
cluster_tagged = TAG_OBJ(cluster_obj1, asa2)

CLUSTERS_INFO = {}


def listen_cluster(tagged_obj):
    tmp_tagged = cbor.loads(tagged.objective.value)
    if tmp_tagged['status']!=2:
        return
    mprint("I'm in clusterhead discovery")
    while True:
        err, handle, answer = graspi.listen_negotiate(tagged_obj.source, tagged_obj.objective)
        if not err:
            mprint("incoming request")
            pass
        else:
            mprint("\033[1;31;1m in listen error {} \033[0m" .format(graspi.etext[err]))

def discover_cluster(_tagged_obj, _attempt=3):
    tmp_tagged = cbor.loads(tagged.objective.value)
    if tmp_tagged['status']!=2:
        return
    attempt = _attempt
    while attempt != 0:
        _, ll = graspi.discover(_tagged_obj.source, _tagged_obj.objective,
                            100000, flush=True, minimum_TTL=500000)
        for item in ll:
            mprint("item clusterhead locator {}".format(str(item.locator)))
            if str(item.locator) == MY_ULA:
                attempt+=1
        attempt-=1
    
def run_cluster():
    mprint("running listen and discovery")
    listen_1.join()
    threading.Thread(target=listen_cluster, args=[cluster_tagged]).start()
    sleep(30)
    discovery_1.join()
    threading.Thread(target=discover_cluster, args=[cluster_tagged, 3]).start()

    # tmp_tagged = cbor.loads(tagged.objective.value)
    # while len(tmp_tagged['cluster_set']) == 0:
    #     pass
    # mprint("I'm in clusterhead discovery")
    # attempt = _attempt
    # while attempt != 0:
    #     _, ll = graspi.discover(_tagged.source,_tagged.objective, 10000, flush=True, minimum_TTL=1000000)
    #     for item in ll:
    #         CLUSTERS_INFO[item] = 0
    #         mprint("\033[1;32;1m locator of cluster found {} - on try {}\033[0m".format(item.locator, _attempt-attempt))
    #     attempt-=1
    # for item in ll:
    #     CLUSTERS_INFO[item] = 0
    #     mprint("\033[1;32;1m locator of cluster found {} \033[0m".format(item.locator))

cluster_sem = threading.Semaphore()

def neg_cluster(_tagged):
    pass
