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
NEIGHBORS_LOCATOR_TO_STR = {}
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

node_info = {'ula':str(acp._get_my_address()), 'weight':get_node_value(),
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
            if node_info['cluster_set'].__contains__(tmp_answer['ula']):
                mprint("*\n&\n*\n&\n*\n&\n*\n&\n*\n&\n*\n&\n")
    tagged_sem.acquire()
    _answer.value = _tagged.objective.value #TODO can be optimized by using the info in request (answer) - just deleted
    tagged_sem.release()
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


def discovery_node_handler(_tagged, _locators):
    for item in _locators:
        if item not in NEIGHBORS_LOCATOR_TO_STR:
            NEIGHBORS_LOCATOR_TO_STR[item] = str(item.locator)
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



listen_1 = threading.Thread(target=listen, args=[tagged, listen_handler]) #TODO change the name
listen_1.start()

discovery_1 = threading.Thread(target=discovery, args=[tagged,discovery_node_handler, 2])
discovery_1.start()
