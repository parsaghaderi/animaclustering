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

proxy_obj, err, PORTS['PORTS']['proxy'] = OBJ_REG('proxy', None, True, False, 10, asa, True) #for pledges and communication only
proxy_tagged = TAG_OBJ(proxy_obj,asa)
proxy_sem = threading.Semaphore()

registrar_obj, err, PORTS['PORTS']['registrar'] = OBJ_REG('registrar', None, True, False, 10, asa, False) #for transferring updates
registrar_tagged = TAG_OBJ(registrar_obj, asa)
registrar_sem = threading.Semaphore()

proxy_tagged.objective.value = cbor.dumps(node_info)
registrar_tagged.objective.value = cbor.dumps(node_info)

pledge_obj, err, pledge_port = OBJ_REG('pledge', None, True, False, 10, asa, True)#for communication with pledge only
pledge_tagged = TAG_OBJ(pledge_obj, asa)
pledge_sem = threading.Semaphore()

def discover_proxy(_tagged):
    global PROXY_LOCATOR
    for i in range(0, 3):
        _, ll = graspi.discover(_tagged.source,_tagged.objective, 10000, flush=True, minimum_TTL=50000)
        if len(ll) != 0:
            mprint("proxy found at {}".format(str(ll[0].locator)), 2)
            PROXY_LOCATOR = ll[0]
            sleep(2)
            threading.Thread(target=send_voucher_req, args = [_tagged, PROXY_LOCATOR]).start()
            return
        else:
            mprint("trying one more time", 2)
            sleep(5)
    mprint("no proxy found", 2)

def send_voucher_req(_tagged, ll):
    mprint("negotiating with registrar through proxy {}".format(str(ll.locator)), 2)
    try:
        if _old_API:
            err, handle, answer = graspi.req_negotiate(_tagged.source,_tagged.objective, ll, 10000) #TODO
            reason = answer
        else:
            err, handle, answer, reason = graspi.request_negotiate(_tagged.source,_tagged.objective, ll, None)
    
        if not err:
            mprint("response from registrar = {}".format(cbor.loads(answer.value)),2)
            _err = graspi.end_negotiate(_tagged.source, handle, True, reason="value received")
    except Exception as e:
        mprint("there was an error occurred in neg_with_proxy with code {}".format(graspi.etext[e]), 2)



def discover_registrar(_tagged): #it doesn't pass the proxy since proxy has already cached the locator
    pass

threading.Thread(target=discover_proxy, args=[proxy_tagged]).start()