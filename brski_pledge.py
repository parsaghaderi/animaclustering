from cmath import phase
from utility import *
from utility import _old_API as _old_API
import sys

REGISTRAR_LOCATOR = None
PROXY_LOCATOR = None

PROXY_STATE = False

asa, err  = ASA_REG('brski')

pledge, err = OBJ_REG('pledge', cbor.dumps(False), True, False, 10, asa)
pledge_tagged = TAG_OBJ(pledge, asa)


registrar, err = OBJ_REG('registrar', cbor.dumps(False), True, False, 10, asa)
registrar_tagged = TAG_OBJ(registrar, asa)

def discovery_proxy(_tagged):
    global PROXY_LOCATOR
    mprint("discoverying proxy", 2)
    _, ll = graspi.discover(_tagged.source,_tagged.objective, 10000, flush=True, minimum_TTL=50000)
    mprint("proxy locator found at {}".format(str(ll[0].locator)), 2)
    PROXY_LOCATOR = ll[0]
    mprint("start negotiation with proxy", 2)
    threading.Thread(target=neg_with_proxy, args=[_tagged, PROXY_LOCATOR]).start()

def discovery_registrar(_tagged): 
    global REGISTRAR_LOCATOR
    mprint("discoverying registrar", 2)
    _, ll =  graspi.discover(_tagged.source,_tagged.objective, 10000, flush=True, minimum_TTL=50000)
    mprint("Registrar found at {}".format(str(ll[0].locator)), 2)
    REGISTRAR_LOCATOR = ll[0]
    threading.Thread(target=neg_with_registrar, args=[_tagged, REGISTRAR_LOCATOR]).start()

def neg_with_proxy(_tagged, ll):
    global PROXY_STATE, registrar_tagged
    mprint("negotiating with REGISTRAR", 2)
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
                threading.Thread(target=discovery_registrar, args=[registrar_tagged]).start()   
        else:
            mprint("Proxy didn't respond")
            _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
            return False
    except Exception as e:
        mprint("there was an error occurred in neg_with_proxy with code {}".format(graspi.etext[e]), 2)

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
                PROXY_STATE = True
                _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
                
        else:
            mprint("Registrar didn't respond")
            _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
            return False
    except Exception as e:
        mprint("there was an error occurred in neg_with_registrar with code {}".format(graspi.etext[e]), 2)


# def proxy_listen_handler(_tagged, _handle, _answer):



def init_proxy(): #listener
    global PROXY_STATE
    while not PROXY_STATE:
        sleep(5)
    mprint("acting as proxy")
    

threading.Thread(target=discovery_proxy, args=[pledge_tagged]).start()