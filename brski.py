from utility import *
from utility import _old_API as _old_API
import sys

REGISTRAR = sys.argv[1] == "True"
REGISTRAR_LOCATOR = None
PROXY_LOCATOR = None


asa, err  = ASA_REG('brski')

obj, err = OBJ_REG('brski_obj', False, True, False, 10, asa)
tagged_obj = TAG_OBJ(obj, asa)

def discovery_proxy(_tagged):
    global PROXY_LOCATOR
    mprint("discoverying proxy")
    _, ll = graspi.discover(_tagged.source,_tagged.objective, 10000, flush=True, minimum_TTL=50000)
    mprint("proxy locator found at {}".format(str(ll[0].locator)), 2)
    PROXY_LOCATOR = ll[0]

def listen_proxy_req(_tagged, _listen_handler=None):
    mprint("start listening for objective {}".format(_tagged.objective.name))
    while True:
        err, handle, answer = graspi.listen_negotiate(_tagged.source, 
                                                      _tagged.objective)       
        if not err:
            initiator_ula = str(ipaddress.IPv6Address(handle.id_source))
            mprint("\033[1;32;1m incoming request from {}\033[0m".format())
            if REGISTRAR:
                mprint("From Registrar")
            else:
                mprint("From Proxy")

if REGISTRAR:
    threading.Thread(target=listen_proxy_req, args=[tagged_obj]).start()
else:
    threading.Thread(target=discovery_proxy, args=[tagged_obj]).start()

