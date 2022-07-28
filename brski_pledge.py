from concurrent.futures import thread
from utility import *
from utility import _old_API as _old_API
import ipaddress

MAP = {MY_ULA:NEIGHBOR_ULA}

REGISTRAR_LOCATOR = None
PROXY_LOCATOR = None

NODE_INFO = {}
REGISTRAR_UPDATES = {}
PORTS = {'proxy':0, 'registrar':0}
node_info = {'MAP':MAP, 'PORTS':PORTS}

asa, err = ASA_REG('brski')

proxy_obj, err, PORTS['proxy'] = OBJ_REG('proxy', None, True, False, 10, asa, True) #for pledges and communication only
proxy_tagged = TAG_OBJ(proxy_obj,asa)
proxy_sem = threading.Semaphore()

registrar_obj, err, PORTS['registrar'] = OBJ_REG('registrar', None, True, False, 10, asa, False) #for transferring updates
registrar_tagged = TAG_OBJ(registrar_obj, asa)
registrar_sem = threading.Semaphore()

proxy_tagged.objective.value = cbor.dumps(node_info)
registrar_tagged.objective.value = cbor.dumps(node_info)

pledge_obj, err, pledge_port = OBJ_REG('pledge', None, True, False, 10, asa, True)#for communication with pledge only
pledge_tagged = TAG_OBJ(pledge_obj, asa)
pledge_sem = threading.Semaphore()

def discover_proxy(_tagged):
    global PROXY_LOCATOR
    for i in range(0, 5):
        _, ll = graspi.discover(_tagged.source,_tagged.objective, 10000, flush=True, minimum_TTL=50000)
        if len(ll) != 0:
            mprint("proxy found at {}".format(str(ll[0].locator)), 2)
            PROXY_LOCATOR = ll[0]
            sleep(2)
            threading.Thread(target=send_voucher_req, args = [_tagged, PROXY_LOCATOR]).start()
            return
        else:
            mprint("trying one more time - waiting for {}".format(5*(i+1)), 2)
            sleep(6*(i+1))
    mprint("no proxy found", 2)

def send_voucher_req(_tagged, ll):
    global registrar_tagged, REGISTRAR_LOCATOR
    mprint("negotiating with registrar through proxy {}".format(str(ll.locator)), 2)
    try:
        if _old_API:
            err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, ll, 10000) #TODO
            reason = answer
        else:
            err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, ll, None)
    
        if not err:
            mprint("response from registrar = {}".format(cbor.loads(answer.value)),2)
            if cbor.loads(answer.value) != False:
                mprint("Registrar accepted request, can join network!", 2)
                _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
                post_join()
    except Exception as e:
        mprint("there was an error occurred in neg_with_proxy with code {}".format(graspi.etext[e]), 2)

def listen_proxy(_tagged, _handle, _answer):
    pledge_ula = str(ipaddress.IPv6Address(_handle.id_source))
    mprint("incoming request from pledge {}, forwarding it to registrar".format(pledge_ula), 2)
    proxy_sem.acquire()
    _tagged.objective.value = _answer.value
    registrar_response = relay(_tagged, pledge_ula)
    if registrar_response == False:
        proxy_sem.release()
        pass
    else:
        mprint("returning registrar's response to the pledge")
        try:
            _tagged.objective.value = registrar_response
            _r = graspi.negotiate_step(_tagged.source, _handle, _answer, 10000)
            if _old_API:
                err, temp, answer = _r
                reason = answer
            else:
                err, temp, answer, reason = _r
            if (not err) and (temp == None):
                mprint("\033[1;32;1m negotiation with pledge {} ended successfully.\033[0m".format(str(REGISTRAR_LOCATOR.locator)), 2)  
                proxy_sem.release()
            else:
                mprint("\033[1;31;1m negotiation in listen_proxy with pledge interrupted with error code {} \033[0m".format(graspi.etext[err]), 2)
                proxy_sem.release()
        except Exception as e:
            mprint("\033[1;31;1m exception in linsten handler {} \033[0m".format(graspi.etext[e]), 2)

def relay(_tagged, _p): #listen for incoming request from pledge to forward to the registrar
    mprint("forwarding pledge's {} voucher request to registrar".format(_p), 2)
    try:
        if _old_API:
            err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, REGISTRAR_LOCATOR, 10000) #TODO
            reason = answer
        else:
            err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, REGISTRAR_LOCATOR, None)
        if not err:
            _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
            return answer
        else:
            mprint("\033[1;31;1m negotiation in relay with registrar interrupted with error code {} \033[0m".format(graspi.etext[err]), 2)
            return False
    except Exception as e:
        mprint("there was an error occurred in relay with code {}".format(graspi.etext[e]), 2)
        return False

def post_join():
    global REGISTRAR_LOCATOR, registrar_tagged, proxy_tagged
    discover_registrar_thread = threading.Thread(target=discover_registrar, args=[registrar_tagged])
    discover_registrar_thread.start()
    discover_registrar_thread.join()

    if REGISTRAR_LOCATOR != None:
        threading.Thread(target=listen, args=[proxy_tagged, listen_proxy]).start()
    else:
        mprint("registrar was not found exiting process")
        exit()

def discover_registrar(_tagged): #it doesn't pass the proxy since proxy has already cached the locator
    global REGISTRAR_LOCATOR
    for i in range(0, 3):
        _, ll = graspi.discover(_tagged.source,_tagged.objective, 10000, flush=True, minimum_TTL=50000)
        if len(ll) != 0:
            mprint("registrar found at {}".format(str(ll[0].locator)), 2)
            REGISTRAR_LOCATOR = ll[0]
            return
        else:
            mprint("no registrar found, trying again", 2)
    mprint("No registrar found!", 2)

threading.Thread(target=discover_proxy, args=[proxy_tagged]).start()

