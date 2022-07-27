from utility import *
from utility import _old_API as _old_API
import random
MAP = {MY_ULA:NEIGHBOR_ULA, 'PORTS':{'pledge':0, 'registrar':0, 'proxy':0}}

list_of_approved = []

asa, err  = ASA_REG('brski')

pledge, err, pledge_port = OBJ_REG('pledge', cbor.dumps(MAP), True, False, 10, asa)
pledge_tagged = TAG_OBJ(pledge, asa)
pledge_sem = threading.Semaphore()

registrar, err, registrar_port = OBJ_REG('registrar', cbor.dumps(MAP), True, False, 10, asa)
registrar_tagged = TAG_OBJ(registrar, asa)
registrar_sem = threading.Semaphore()

proxy, err, proxy_port = OBJ_REG('proxy', cbor.dumps(MAP), True, False, 10, asa, True)
proxy_tagged = TAG_OBJ(proxy, asa)
proxy_sem = threading.Semaphore()
# proxy, err = OBJ_REG('brski_proxy', False, True, False, 10, asa)
# proxy_tagged = TAG_OBJ(proxy, asa)


def listen_proxy_handler(_tagged, _handle, _answer):
    global list_of_approved, pledge_tagged, proxy_tagged
    initiator_ula = str(ipaddress.IPv6Address(_handle.id_source))
    mprint("***\n{}\n***".format(type(_handle)), 2)
    mprint("\033[1;32;1m incoming request from {}\033[0m".format(initiator_ula), 2)
    tmp_answer = cbor.loads(_answer.value)
    if True:
        mprint("contacting MASA with the Pledge's certificate", 2)
        list_of_approved.append(initiator_ula)
        mprint(list_of_approved)

    try:
        if random.randint(0, 10)%3 != 0:
            proxy_sem.acquire()
            registrar_sem.acquire()
            pledge_sem.acquire()
            MAP.update(tmp_answer)
            _tagged.objective.value = cbor.dumps(MAP)
            proxy_tagged.objective.value = cbor.dumps(MAP)
            pledge_tagged.objective.value = cbor.dumps(MAP)
            _answer.value = cbor.dumps(MAP)
            proxy_sem.release()
            registrar_sem.release()
            pledge_sem.release()
        else:
            _answer.value = cbor.dumps(False)

        _r = graspi.negotiate_step(_tagged.source, _handle, _answer, 10000)
        if _old_API:
            err, temp, answer = _r
            reason = answer
        else:
            err, temp, answer, reason = _r
        if (not err) and (temp == None):
            mprint("\033[1;32;1m negotiation with peer {} ended successfully with value {}\033[0m".format(initiator_ula, cbor.loads(_answer.value)), 2)  
            mprint("trying to contact pledge", 2)
            sleep(10)
            threading.Thread(target=neg_with_pledge, args=[registrar_tagged,ipaddress.IPv6Address(_handle.id_source),MAP['PORTS']['registrar']]).start()
        else:
            mprint("\033[1;31;1m in listen handler - neg with peer {} interrupted with error code {} \033[0m".format(initiator_ula, graspi.etext[err]), 2)
            pass
    except Exception as err:
        mprint("\033[1;31;1m exception in linsten handler {} \033[0m".format(err), 2)

def listen_registrar_handler(_tagged, _handle, _answer):
    global MAP
    initiator_ula = str(ipaddress.IPv6Address(_handle.id_source))
    mprint("\033[1;32;1m incoming request from {}\033[0m".format(initiator_ula), 2)
    tmp_answer = cbor.loads(_answer.value)
    # MAP[initiator_ula] = tmp_answer
    # registrar_sem.acquire()

    proxy_sem.acquire()
    registrar_sem.acquire()
    pledge_sem.acquire()
    MAP.update(tmp_answer)
    _tagged.objective.value = cbor.dumps(MAP)
    proxy_tagged.objective.value = cbor.dumps(MAP)
    pledge_tagged.objective.value = cbor.dumps(MAP)
    _answer.value = cbor.dumps(MAP)
    proxy_sem.release()
    registrar_sem.release()
    pledge_sem.release()

    _answer.value = cbor.dumps(MAP)
    registrar_tagged.objective.value = cbor.dumps(MAP)
    registrar_sem.release()
    try:
        _r = graspi.negotiate_step(_tagged.source, _handle, _answer, 10000)
        if _old_API:
                err, temp, answer = _r
                reason = answer
        else:
            err, temp, answer, reason = _r
        if (not err) and (temp == None):
            mprint("\033[1;32;1m negotiation with peer {} ended successfully \033[0m".format(initiator_ula), 2)  
        
        else:
            mprint("\033[1;31;1m in listen handler - neg with peer {} interrupted with error code {} \033[0m".format(initiator_ula, graspi.etext[err]), 2)
            pass
    except Exception as err:
        mprint("\033[1;31;1m exception in linsten handler {} \033[0m".format(err), 2)
        

def neg_with_pledge(_tagged, _ll, _port):
    
    tmp_locator = graspi.asa_locator(_ll, 0, True)
    tmp_locator.port = _port

    try:
        if _old_API:
            err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, tmp_locator, 10000) #TODO
            reason = answer
        else:
            err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, tmp_locator, None)

        if not err:
            mprint("communicating with the pledge with answer {}".format(cbor.loads(answer.value)), 2)
            _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
            
    except Exception as e:
        mprint("there was an error occurred in neg_with_registrar with code {}".format(graspi.etext[e]), 2)


threading.Thread(target=listen, args=[proxy_tagged, listen_proxy_handler]).start()
threading.Thread(target=listen, args=[registrar_tagged, listen_registrar_handler]).start()
