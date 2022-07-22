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
    mprint("@@@@@@\n{}\n@@@@@@".format(type(_handle.id_source)))
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
 

