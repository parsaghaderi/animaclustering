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
            return
        else:
            mprint("trying one more time")
            sleep(5)
    

def send_voucher_req(_tagged, _proxy):
    pass

def discover_registrar(_tagged): #it doesn't pass the proxy since proxy has already cached the locator
    pass

