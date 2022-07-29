from grasp import asa_locator
from utility import *
from utility import _old_API as _old_API
import random

MAP = {MY_ULA:NEIGHBOR_ULA} #the whole map of the network, only map
NETWORK_INFO = {} #what info was received from each node
nodes_locator = {}

node_info = {'MAP':MAP, 'PORTS':{'registrar':0, 'proxy':0}} #my info

asa, err = ASA_REG('brski')

proxy_obj, err, node_info['PORTS']['proxy'] = OBJ_REG('proxy', None, True, False, 10, asa, True) #for pledges and communication only
proxy_tagged = TAG_OBJ(proxy_obj,asa)
proxy_sem = threading.Semaphore()

registrar_obj, err, node_info['PORTS']['registrar'] = OBJ_REG('registrar', None, True, False, 10, asa, False) #for transferring updates
registrar_tagged = TAG_OBJ(registrar_obj, asa)
registrar_sem = threading.Semaphore()

pledge_obj, err, pledge_port = OBJ_REG('pledge', None, True, False, 10, asa, True)#for communication with pledge only
pledge_tagged = TAG_OBJ(pledge_obj, asa)
pledge_sem = threading.Semaphore()

proxy_tagged.objective.value = cbor.dumps(node_info)
registrar_tagged.objective.value = cbor.dumps(node_info)

def listen_proxy(_tagged, _handle, _answer): #to join pledge
    mprint("the handler is link-local {}".format(ipaddress.IPv6Address(_handle.id_source).is_link_local) ,2)
    proxy_address = str(ipaddress.IPv6Address(_handle.id_source))

    tmp_answer = cbor.loads(_answer.value) #{map:..., ports:....}

    actual_initiator_ula = tmp_answer['my_ula']
    mprint("\033[1;32;1m incoming request from {}\033[0m".format(actual_initiator_ula), 2)

    if True:
        proxy_sem.acquire()
        _answer.value = cbor.dumps(True)
        mprint("allowing {} to join the domain".format(tmp_answer), 2)
    else:
        _answer.value = cbor.dumps(False)
        mprint("Rejecting pledge")
    for i in range(3):
        try:
            _r = graspi.negotiate_step(_tagged.source, _handle, _answer, 10000)
            
            if _old_API:
                err, temp, answer = _r
                reason = answer
            else:
                err, temp, answer, reason = _r
            if (not err) and (temp == None):
                mprint("\033[1;32;1m negotiation with peer {} with proxy {} ended successfully with value {}\033[0m".format(actual_initiator_ula, proxy_address,cbor.loads(_answer.value)), 2)  
                proxy_sem.release()
                break
            else:
                mprint("\033[1;31;1m in listen handler - neg with peer {} with proxy {} interrupted with error code {} \033[0m".format(actual_initiator_ula, proxy_address, graspi.etext[err]), 2)
                mprint("5s Zzz", 2)
                sleep(5)
                
        except Exception as err:
            mprint("\033[1;31;1m exception in linsten handler {} \033[0m".format(err), 2)
            proxy_sem.release()
    proxy_sem.release()

def listen_registrar(_tagged, _handle, _answer):#to get updates from nodes
    actual_initiator_ula = str(ipaddress.IPv6Address(_handle.id_source))
    mprint("incoming request from node {}".format(actual_initiator_ula), 2)

    tmp_answer = cbor.loads(_answer.value)

    registrar_sem.acquire()

    MAP.update(tmp_answer['MAP'])
    node_info['MAP'].update(tmp_answer['MAP'])
    nodes_locator[actual_initiator_ula] = tmp_answer['PORTS']
    _answer.value = cbor.dumps(node_info)
    registrar_tagged.objective.value = cbor.dumps(node_info)

    registrar_sem.release()
    try:
        _r = graspi.negotiate_step(registrar_tagged.source, _handle, _answer, 10000)
        if _old_API:
            err, temp, answer = _r
            reason = answer
        else:
            err, temp, answer, reason = _r
        if (not err) and (temp == None):
            mprint("\033[1;32;1m negotiation with node {} for updates ended successfully with value {}\033[0m".format(actual_initiator_ula, cbor.loads(_answer.value)), 2)  
        else:
            mprint("\033[1;31;1m in registrar listen handler - neg with node interrupted with error code {} \033[0m".format(graspi.etext[err]), 2)
    except Exception as e:
        mprint("\033[1;31;1m exception in linsten handler {} \033[0m".format(e), 2)
        
def neg_registrar(_tagged, ll):
    global MAP
    mprint("sending updates to {}".format(str(ll.locator)), 2)
    for i in range(2):
        try:
            _tagged.objective.value = cbor.dumps(MAP)
            if _old_API:
                err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, ll, 10000) #TODO
                reason = answer
            else:
                err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, ll, None)
            if not err:
                mprint("got response from node {}".format(str(ll.locator)), 2)
                tmp_answer = cbor.loads(answer.value)
                registrar_sem.acquire()
                MAP.update(tmp_answer)
                node_info['MAP'].update(tmp_answer)
                registrar_tagged.objective.value = cbor.dumps(node_info)
                registrar_sem.release()
                mprint("MAP updated\n {}".format(MAP), 2)
                _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
                return
            else:
                mprint("update not received by node\ntrying again after 10s Zzz", 2)
                sleep(10)
        except Exception as e:
            mprint("there was an error occurred in neg_with_proxy with code {}".format(graspi.etext[e]), 2)
            return

def send_update(_tagged, ll):
    global MAP, pledge_sem, pledge_tagged
    mprint("sending updates to {}".format(str(ll.locator)), 2)
    for i in range(2):
        try:
            _tagged.objective.value = cbor.dumps(MAP)
            if _old_API:
                err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, ll, 10000) #TODO
                reason = answer
            else:
                err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, ll, None)
            if not err:
                tmp_answer = cbor.loads(answer)
                pledge_sem.acquire()
                MAP.update(tmp_answer)
                mprint("MAP updated {}".format(MAP), 2)
                _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
                return
            else:
                mprint("update not received by node\ntrying again after 10s Zzz", 2)
                sleep(10)
        except Exception as e:
            mprint("there was an error occurred in neg_with_proxy with code {}".format(graspi.etext[e]), 2)
            return

            
def update(_tagged):
    locators = []
    for item in nodes_locator:
        locators.append(locator_maker(item, nodes_locator[item]['registrar'], False))
    
    for item in locators:
        threading.Thread(target=send_update, args=[_tagged, item]).start()


threading.Thread(target=listen, args = [proxy_tagged    , listen_proxy])    .start()
threading.Thread(target=listen, args = [registrar_tagged, listen_registrar]).start()

def run_update(_tagged):
    while len(nodes_locator) < 9:
        sleep(1)
    mprint("sending updates to nodes", 2)
    sleep(2)
    update(_tagged)

threading.Thread(target=run_update, args=[pledge_tagged]).start()
