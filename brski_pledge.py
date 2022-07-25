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

def discovery_proxy(_tagged):
    global PROXY_LOCATOR
    mprint("discoverying proxy")
    _, ll = graspi.discover(_tagged.source,_tagged.objective, 10000, flush=True, minimum_TTL=50000)
    mprint("proxy locator found at {}".format(str(ll[0].locator)), 2)
    PROXY_LOCATOR = ll[0]
    threading.Thread(target=neg_with_proxy, args=[_tagged, PROXY_LOCATOR]).start()

def discovery_registrar(_tagged): 
    global PROXY_STATE
    if PROXY_STATE:
        mprint("looking for registrar")

def neg_with_proxy(_tagged, ll):
    global PROXY_STATE
    mprint("negotiating with REGISTRAR")
    try:
        if _old_API:
            err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, ll, 10000) #TODO
            reason = answer
        else:
            err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, ll, None)

        if not err:
            if cbor.loads(answer) == True:
                mprint("can join network - key stored for further comm - ACP booted up")
                PROXY_STATE = True
                _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
                return answer
        else:
            mprint("Registrar didn't respond")
            _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
            return False
    except Exception as e:
        mprint("there was an error occurred in neg_REGISTRAR with code {}".format(graspi.etext[e]))

# def proxy_listen_handler(_tagged, _handle, _answer):



def init_proxy(): #listener
    global PROXY_STATE
    while not PROXY_STATE:
        sleep(5)
    mprint("acting as proxy")
    

threading.Thread(target=discovery_proxy, args=[pledge_tagged]).start()