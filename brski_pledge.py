from cmath import phase
from utility import *
from utility import _old_API as _old_API
import sys

REGISTRAR_LOCATOR = None
PROXY_LOCATOR = None

PROXY_STATE = False
PHASE = 1
asa, err  = ASA_REG('brski')

pledge, err = OBJ_REG('pledge', cbor.dumps(False), True, False, 10, asa)
pledge_tagged = TAG_OBJ(pledge, asa)


registrar, err = OBJ_REG('registrar', cbor.dumps(NEIGHBOR_ULA), True, False, 10, asa)
registrar_tagged = TAG_OBJ(registrar, asa)

proxy, err = OBJ_REG('proxy', cbor.dumps(False), True, False, 10, asa, True)
proxy_tagged = TAG_OBJ(proxy, asa)
proxy_sem = threading.Semaphore()


def discovery_proxy(_tagged):
    while True:
        global PROXY_LOCATOR, PHASE
        mprint("discoverying proxy", 2)
        _, ll = graspi.discover(_tagged.source,_tagged.objective, 10000, flush=True, minimum_TTL=50000)
        if len(ll) != 0:
            mprint("proxy locator found at {} on interface {}".format(str(ll[0].locator), str(ll[0].ifi)), 2)
            PROXY_LOCATOR = ll[0]
            mprint("start negotiation with proxy", 2)
            PHASE = 2
            break
        else:
            sleep(10)
    
    # threading.Thread(target=neg_with_proxy, args=[_tagged, PROXY_LOCATOR]).start()

def discovery_registrar(_tagged): 
    global REGISTRAR_LOCATOR, PHASE
    while True:
        mprint("discoverying registrar", 2)
        _, ll =  graspi.discover(_tagged.source,_tagged.objective, 10000, flush=True, minimum_TTL=50000)
        if len(ll)!= 0:
            mprint("Registrar found at {}".format(str(ll[0].locator)), 2)
            REGISTRAR_LOCATOR = ll[0]
            break   
        else:
            sleep(5)
    threading.Thread(target=listen, args=[proxy_tagged, proxy_listen_handler]).start() #to communicate with registrar
    threading.Thread(target=listen, args=[pledge_tagged, pledge_listen_handler]).start() #to update registred nodes
    sleep(5)
    PHASE = 4
    

def neg_with_proxy(_tagged, ll):
    global PROXY_STATE, registrar_tagged, PHASE
    mprint("negotiating with proxy", 2)
    try:
        if _old_API:
            err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, ll, 10000) #TODO
            reason = answer
        else:
            err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, ll, None)

        if not err:
            if cbor.loads(answer.value) == True:
                mprint("can join network - key stored for further comm - ACP booted up", 2)
                PROXY_STATE = True
                _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
                mprint("looking for the registrar", 2)
                PHASE = 3
                # discovery_registrar_thread = threading.Thread(target=discovery_registrar, args=[registrar_tagged])
                # discovery_registrar_thread.start()
                # discovery_registrar_thread.join()
                # threading.Thread(target=listen, args=[proxy_tagged, proxy_listen_handler]).start()
            else:
                mprint("Registrar rejected Pledge or there is problem in communication with Registrar")
                _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
                sleep(20)
                PHASE = 1
        else:
            mprint("Proxy didn't respond")
            # _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
            sleep(20)
            PHASE = 1
            
    except Exception as e:
        mprint("there was an error occurred in neg_with_proxy with code {}".format(graspi.etext[e]), 2)
        PHASE = 1
        

def neg_with_registrar(_tagged, ll):
    mprint("negotiating with registrar")
    try:
        if _old_API:
            err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, ll, 10000) #TODO
            reason = answer
        else:
            err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, ll, None)

        if not err:
            if cbor.loads(answer.value) == True:
                mprint("communicating with the registrar", 2)
                _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
                return True
        else:
            mprint("Registrar didn't respond")
            _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
            return False
    except Exception as e:
        mprint("there was an error occurred in neg_with_registrar with code {}".format(graspi.etext[e]), 2)

def relay(_answer):
    global proxy_tagged
    mprint("relaying voucher request")
    proxy_sem.acquire()
    proxy_tagged.objective.value = cbor.dumps(_answer)
    
    try:
        if _old_API:
                err, handle, answer = graspi.req_negotiate(proxy_tagged.source,proxy_tagged.objective, REGISTRAR_LOCATOR, 10000) #TODO
                reason = answer
        else:
            err, handle, answer, reason = graspi.request_negotiate(proxy_tagged.source,proxy_tagged.objective, REGISTRAR_LOCATOR, None)
        proxy_sem.release()
        if not err:
            mprint("got voucher response form registrar", 2)
            _err = graspi.end_negotiate(proxy_tagged.source, handle, True, reason="value received")
            proxy_sem.release()
            return cbor.loads(answer.value)
    except Exception as e:
        mprint("exception experienced during relay negotiation process with code {}".format(graspi.etext[e]), 2)
        return cbor.dumps(False)

# def proxy_listen_handler(_tagged, _handle, _answer):

def proxy_listen_handler(_tagged, _handle, _answer):
    initiator_ula = str(ipaddress.IPv6Address(_handle.id_source))
    _answer.value = cbor.dumps(relay(cbor.loads(_answer.value)))#TODO

    try:
        _r = graspi.negotiate_step(_tagged.source, _handle, _answer, 10000)
        if _old_API:
            err, temp, answer = _r
            reason = answer
        else:
            err, temp, answer, reason = _r
        if (not err) and (temp == None):
            mprint("\033[1;32;1m negotiation with pledge {} ended successfully \033[0m".format(initiator_ula), 2)  
        else:
            mprint("\033[1;31;1m in proxy_listen_handler - neg with peer {} interrupted with error code {} \033[0m".format(initiator_ula, graspi.etext[err]), 2)
            pass
    except Exception as err:
        mprint("\033[1;31;1m exception in proxy_listen_handler {} \033[0m".format(err), 2)

def pledge_listen_handler(_tagged, _handle, _answer):
    mprint("waiting for updates from registrar", 2)



def control():
    global PHASE
    while True:
        if PHASE == 1:
            discovery_proxy_thread = threading.Thread(target=discovery_proxy, args=[proxy_tagged])
            discovery_proxy_thread.start()
            discovery_proxy_thread.join()
        elif PHASE == 2:
            neg_with_proxy_thread = threading.Thread(target=neg_with_proxy, args=[proxy_tagged, PROXY_LOCATOR])
            neg_with_proxy_thread.start()
            neg_with_proxy_thread.join()
        elif PHASE == 3:
            discovery_registrar_thread = threading.Thread(target=discovery_registrar, args=[registrar_tagged])
            discovery_registrar_thread.start()
            discovery_registrar_thread.join()
        elif PHASE == 4:
            mprint("calling neg with registrar")
            neg_with_registrar_thread = threading.Thread(target=neg_with_registrar, args=[registrar_tagged, REGISTRAR_LOCATOR])
            neg_with_registrar_thread.start()
            neg_with_registrar_thread.join()
        sleep(1)
threading.Thread(target=control, args = []).start()