from utility import *
from utility import _old_API as _old_API
import sys
import random

MAP = {}

list_of_approved = []

asa, err  = ASA_REG('brski')

pledge, err = OBJ_REG('pledge', True, True, False, 10, asa)
pledge_tagged = TAG_OBJ(pledge, asa)

registrar, err = OBJ_REG('registrar', cbor.dumps(True), True, False, 10, asa)
registrar_tagged = TAG_OBJ(registrar, asa)

proxy, err = OBJ_REG('proxy', cbor.dumps(False), True, False, 10, asa, True)
proxy_tagged = TAG_OBJ(proxy, asa)
proxy_sem = threading.Semaphore()
# proxy, err = OBJ_REG('brski_proxy', False, True, False, 10, asa)
# proxy_tagged = TAG_OBJ(proxy, asa)


def listen_proxy_handler(_tagged, _handle, _answer):
    global list_of_approved
    initiator_ula = str(ipaddress.IPv6Address(_handle.id_source))
    mprint("\033[1;32;1m incoming request from {}\033[0m".format(initiator_ula), 2)
    tmp_answer = cbor.loads(_answer.value)
    if True:
        mprint("contacting MASA with the Pledge's certificate", 2)
        list_of_approved.append(initiator_ula)
        mprint(list_of_approved)

    try:
        _answer.value = cbor.dumps(random.randint(0, 10)%3==0)
        _r = graspi.negotiate_step(_tagged.source, _handle, _answer, 10000)
        if _old_API:
            err, temp, answer = _r
            reason = answer
        else:
            err, temp, answer, reason = _r
        if (not err) and (temp == None):
            mprint("\033[1;32;1m negotiation with peer {} ended successfully with value {}\033[0m".format(initiator_ula, cbor.loads(_answer.value)), 2)  
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
    MAP[initiator_ula] = tmp_answer
    _answer.value = cbor.dumps(MAP)
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
        



threading.Thread(target=listen, args=[proxy_tagged, listen_proxy_handler]).start()
threading.Thread(target=listen, args=[registrar_tagged, listen_registrar_handler]).start()
