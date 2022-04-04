import random
import threading
import cbor
import subprocess as sp
from time import sleep



# import grasp
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
# NEIGHBOR_ULA str
##########
MY_ULA, NEIGHBOR_ULA = get_neighbors() 
##########
# NEIGHBOR_INFO dict locator:json
##########
NEIGHBOR_INFO = {}
##########
# ?
##########
NEIGHBOR_UPDATE = {} 
##########
# node_info['weight'] is run once, that's why we don't need a tmp variable to store node's weight
# status 1:not decided, 2:cluster-head, 3:want to join, 4:joined 5:changed (!)
##########
node_info = {'ula':str(acp._get_my_address()), 'weight':get_node_value(), 'cluster_head':False, 'cluster_set':[], 'neighbors':NEIGHBOR_ULA, 
             'status': 1} 
obj, err = OBJ_REG('node', cbor.dumps(node_info), True, False, 10, asa)
tag_lock = True
tagged   = TAG_OBJ(obj, asa)



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
            mprint("in listen error {}" .format(graspi.etext[err]))
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
    
    mprint("sent from peer {}".format(tmp_answer))
    #TODO get info from the answer
    #we already know the dict of neighbor_info has been created!
    ###########
    # while len(NEIGHBOR_INFO)!=len(NEIGHBOR_ULA): #TODO why? 
    #     pass

    for item in NEIGHBOR_INFO:
        if str(item.locator) == tmp_answer['ula']:
            NEIGHBOR_INFO[item] = tmp_answer
    ############
    while not tag_lock:
        pass
    tag_lock = False
    _answer.value = _tagged.objective.value #TODO can be optimized by using the info in request (answer)
    tag_lock = True
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
            mprint("in listen handler - neg with peer interrupted with error code {}".format(graspi.etext[err]))
            pass
    except Exception as err:
        mprint("exception in linsten handler {}".format(err))


def discover(_tagged):
    global NEIGHBOR_INFO
    attempt = 3
    while attempt != 0:
        _, ll = graspi.discover(_tagged.source,_tagged.objective, 10000, flush=True, minimum_TTL=50000)
        mprint(len(ll))
        attempt-=1
    for item in ll:
        NEIGHBOR_INFO[item] = 0
    threading.Thread(target=run_neg, args=[tagged, NEIGHBOR_INFO.keys()]).start()

threading.Thread(target=discover, args=[tagged]).start()

INITIAL_NEG = False

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
    INITIAL_NEG = True



############
# @param _tagged tagged objective for negotiating over
# @param ll locator of the peer
# @param _attempt number of attempts for negotiating 
############
def neg(_tagged, ll, _attempt = 3):
    global NEIGHBOR_INFO

    if _attempt!=3:
        mprint("start negotiation o kire khar {}".format(ll.locator))
    attempt = _attempt
    while attempt!=0:
        mprint("start negotiating with {} for {}th time".format(ll.locator, attempt))
        if _old_API:
            err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, ll, None) #TODO
            reason = answer
        else:
            err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, ll, None)
            try:
                if not err:
                    NEIGHBOR_INFO[ll] = cbor.loads(answer.value)#√
                    mprint("neg_step value : peer {} offered {}".format(str(ll.locator), NEIGHBOR_INFO[ll]))#√
                    if NEIGHBOR_INFO[ll]['cluster_head'] == str(acp._get_my_address()): #√
                        if not node_info['cluster_set'].__contains__(str(ll.locator)):
                            node_info['cluster_set'].append(str(ll.locator))
                        while not tag_lock:
                            pass
                        tag_lock = False
                        _tagged.objective.value = cbor.dumps(node_info)
                        tag_lock = True
                        NEIGHBOR_UPDATE[ll.locator] = True
                    _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
                else:
                    mprint("in neg - neg with {} failed + {}".format(str(ll.locator), graspi.etext[err]))
                    attempt+=1
            except Exception as err:
                mprint("exception in neg with code {}".format(err))
                attempt+=1
        try:
            err = graspi.end_negotiate(_tagged.source, handle, False, "value not received")
        except Exception as err:
            mprint("in neg exception happened {}".format(err))
        attempt-=1
        
#from here

HEAVIER = {}
LIGHTER = {}
HEAVIEST = None

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

        
    mprint("heavier:{}".format(HEAVIER))
    mprint("lighter:{}".format(LIGHTER))
    mprint("heaviest:{}".format(HEAVIEST))

#########
# @param _heaviest takes the current heaviest(locator), return next one in line
# @return locator of the 2nd heaviest node
#########
def find_next_heaviest(_heaviest):
    global HEAVIER, HEAVIEST
    if HEAVIEST == None:
        return None
    tmp_max = 0
    tmp_heaviest = None
    for item in HEAVIER:
        if tmp_heaviest != None:
            mprint("heaviest now {} - tmp_max = {} - tmp_heaviest {} - item:weight = {}={}"
            .format(str(_heaviest.locator), tmp_max, str(tmp_heaviest.locator),
            str(item.locator), NEIGHBOR_INFO[item]['weight']))
        else:
            mprint("heaviest now {} - tmp_max = {} - tmp_heaviest {} - item:weight = {}={}"
            .format(str(_heaviest.locator), tmp_max, "none",
            str(item.locator), NEIGHBOR_INFO[item]['weight']))
        if item!= HEAVIEST and HEAVIER[item]> tmp_max and HEAVIER[_heaviest] > HEAVIER[item]:
            tmp_max = HEAVIER[item]
            tmp_heaviest = item
    return tmp_heaviest

###########
# init process
###########
TO_JOIN = None
def init():
    global tag_lock, tagged
    global INITIAL_NEG, HEAVIEST, MY_ULA, TO_JOIN
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
            tmp_ch = find_heavier(tmp_ch)

    # if HEAVIEST == None:
    #     mprint("I'm clusterhead")
    #     while not tag_lock:
    #         pass
    #     tag_lock = False
    #     tagged.objective.value = cbor.loads(tagged.objective.value)
    #     tagged.objective.value['cluster_head'] = True
    #     tagged.objective.value['status'] = 2
    #     tagged.objective.value['cluster_set'].append(MY_ULA)
    #     tagged.objective.value = cbor.dumps(tagged.objective.value)
    #     tag_lock = True
    #     mprint(node_info['weight'])
    #     mprint(list(NEIGHBOR_INFO.values()))

    # else:
    #     mprint("I want to join {}".format(HEAVIEST.locator))
    #     TO_JOIN = HEAVIEST
    #     while not tag_lock:
    #         pass
    #     tag_lock = False
    #     tagged.objective.value = cbor.loads(tagged.objective.value)
    #     tagged.objective.value['cluster_head'] = False #to let lighter nodes know I'm not ch
    #     tagged.objective.value['status'] = 3
    #     tagged.objective.value['cluster_set']  = []
    #     tagged.objective.value = cbor.dumps(tagged.objective.value)
    #     tag_lock = True
    #     mprint(node_info)
    #     mprint(list(NEIGHBOR_INFO.values()))
    # INITIAL_NEG = False
    # threading.Thread(target=run_neg, args=[tagged, NEIGHBOR_INFO.keys()]).start()
    # while not INITIAL_NEG:
    #     pass
    # threading.Thread(target=on_update_rcv, args=[]).start()
threading.Thread(target=init, args=[]).start() #initial init

# CLUSTERING_DONE = False
# def on_update_rcv():
#     global NEIGHBOR_INFO, HEAVIER, HEAVIEST, TO_JOIN, tag_lock, CLUSTERING_DONE
#     if TO_JOIN != None:
#         if NEIGHBOR_INFO[TO_JOIN]['cluster_head'] == True and NEIGHBOR_INFO[TO_JOIN]['status']==2:
#             mprint("Joining {}".format(HEAVIEST.locator))
#             tag_lock = False
#             tagged.objective.value = cbor.loads(tagged.objective.value)
#             tagged.objective.value['cluster_head'] = str(HEAVIEST.locator)
#             tagged.objective.value['cluster_set']  = []
#             tagged.objective.value = cbor.dumps(tagged.objective.value)
#             tag_lock = True
#             CLUSTERING_DONE = True
        
#         else:
#             mprint(HEAVIER)
#             tmp_ch = find_next_heaviest(HEAVIEST)
#             if tmp_ch == None:
#                 mprint("I'm clusterhead")
#                 while not tag_lock:
#                     pass
#                 tag_lock = False
#                 tagged.objective.value = cbor.loads(tagged.objective.value)
#                 tagged.objective.value['cluster_head'] = True
#                 tagged.objective.value['cluster_set'].append(MY_ULA)
#                 tagged.objective.value = cbor.dumps(tagged.objective.value)
#                 tag_lock = True 
#                 mprint(node_info)
#                 mprint(NEIGHBOR_INFO)
#                 CLUSTERING_DONE = True
                
#             else:
#                 tmp_ch = find_next_heaviest(HEAVIEST)
#                 while tmp_ch != None:
#                     if NEIGHBOR_INFO[tmp_ch]['cluster_head'] == True:
#                         mprint("Joining {}".format(str(tmp_ch.locator)))
#                         tag_lock = False
#                         tagged.objective.value = cbor.loads(tagged.objective.value)
#                         tagged.objective.value['cluster_head'] = str(tmp_ch.locator)
#                         tagged.objective.value['cluster_set']  = []
#                         tagged.objective.value = cbor.dumps(tagged.objective.value)
#                         tag_lock = True
#                         mprint(node_info)
#                         mprint(NEIGHBOR_INFO)
#                         CLUSTERING_DONE = True
#                         break
#                     else:
#                         tmp_ch = find_next_heaviest(tmp_ch) #TODO check how we can stick in the loop
#                         mprint("trying next heaviest node")
    
#     # threading.Thread(target=run_neg, args=[tagged, NEIGHBOR_INFO.keys()]).start()
    

# def show():
#     while not CLUSTERING_DONE:
#         pass
#     sleep(60)
#     mprint("clustering done")
#     mprint(node_info)
#     mprint(NEIGHBOR_INFO)

# threading.Thread(target=show, args=[]).start()



# def ch_obj():
#     while not CLUSTERING_DONE:
#         pass
#     if node_info['cluster_head'] == True:
#         global cluster, tagged_cluster
#         try:
#             cluster, err   = OBJ_REG('CH', None, True, 10, asa)
#             tagged_cluster = TAG_OBJ(cluster, asa)
#         except:
#             mprint("creating cluster head objective error ".format(graspi.etext[err]))

# # threading.Thread(target=ch_obj, args=[]).start()


# def listen_ch(_tagged):
#     err, handle, answer = graspi.listen_negotiate(_tagged.source, _tagged.objective)
#     if not err:
#         pass
#         #mprint("incoming request")
#         #threading.Thread(target=listener_handler, args=[_tagged, handle, answer]).start()
#     else:
#         mprint(graspi.etext[err])


# def discover_ch(_tagged):
#     global NEIGHBOR_INFO
#     attempt = 3
#     while attempt != 0:
#         _, ll = graspi.discover(_tagged.source,_tagged.objective, 10000, flush=True, minimum_TTL=50000)
#         mprint(len(ll))
#         attempt-=1
#     for item in ll:
#         mprint("ch found at 2 hops away {}".format(item.locator))


# def find_ch():
#     while not CLUSTERING_DONE:
#         pass
#     if node_info['cluster_head'] == True:
#         threading.Thread(target=listen_ch, args=[tagged_cluster]).start()
#         threading.Thread(target=discover_ch, args=[tagged_cluster]).start()
# # threading.Thread(target=find_ch, args=[]).start()