from grasp import asa_locator
from utility import *
from utility import _old_API as _old_API
import random

MAP = {MY_ULA:NEIGHBOR_ULA} #the whole map of the network, only map
NETWORK_INFO = {} #what info was received from each node
nodes_locator = {}

node_info = {'MAP':MAP} #my info

asa, err = ASA_REG('brski')

proxy_obj, err, proxy_port = OBJ_REG('proxy', None, True, False, 10, asa, True) #for pledges and communication only
proxy_tagged = TAG_OBJ(proxy_obj,asa)
proxy_sem = threading.Semaphore()

registrar_obj, err, registrar_port = OBJ_REG('registrar', None, True, False, 10, asa, False) #for transferring updates
registrar_tagged = TAG_OBJ(registrar_obj, asa)
registrar_sem = threading.Semaphore()

pledge_obj, err, pledge_port = OBJ_REG('pledge', None, True, False, 10, asa, True)#for communication with pledge only
pledge_tagged = TAG_OBJ(pledge_obj, asa)
pledge_sem = threading.Semaphore()


def listen_proxy(_tagged, _handle, _answer): #to join pledge
    
    proxy_address = str(ipaddress.IPv6Address(_handle.id_source))
    tmp_answer = cbor.loads(_answer.value) #{map:..., ports:....}
    actual_initiator_ula = list(tmp_answer['MAP'].keys())[0]
    mprint("\033[1;32;1m incoming request from {}\033[0m".format(actual_initiator_ula), 2)

    if (random.randint(0, 10)%4 != 0):
        mprint("connecting to MASA", 2)
        sleep(2)
        mprint("MASA approved")
        proxy_sem.acquire()
        registrar_sem.acquire()
        MAP.update(tmp_answer['MAP'])
        nodes_locator[actual_initiator_ula] = tmp_answer['PORTS']
        _answer.value = cbor.dumps(node_info)
        proxy_sem.release()
        registrar_sem.release()
        
    else:
        mprint("Rejecting pledge")
        _answer.value = cbor.dumps(False)

    try:
        _r = graspi.negotiate_step(_tagged.source, _handle, _answer, 10000)
        if _old_API:
            err, temp, answer = _r
            reason = answer
        else:
            err, temp, answer, reason = _r
        if (not err) and (temp == None):
            mprint("\033[1;32;1m negotiation with peer {} with proxy {} ended successfully with value {}\033[0m".format(actual_initiator_ula, proxy_address,cbor.loads(_answer.value)), 2)  
        else:
            mprint("\033[1;31;1m in listen handler - neg with peer {} with proxy {} interrupted with error code {} \033[0m".format(actual_initiator_ula, proxy_address, graspi.etext[err]), 2)
            pass
    except Exception as err:
        mprint("\033[1;31;1m exception in linsten handler {} \033[0m".format(err), 2)
    
threading.Thread(target=listen, args = [proxy_tagged, listen_proxy]).start()


def listen_registrar(_tagged, _handle, _answer):#to get updates from nodes
    pass

