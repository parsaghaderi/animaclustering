import random
import threading
import cbor, cbor2
try:
    import graspi
    _old_API = False  
    
except:
    import grasp as graspi
    _old_API = True
import multiping 
#########################
# utility function for setting the value of
# each node randomly. 
#########################
def get_node_value():
    return random.random()
    
#########################
# utility print function
#########################
def mprint(msg, mode = 1):
    if mode!= 1:
        print("\n#######################")
        print(msg)
        print("#######################\n")

##############
# geting the locators as strings
##############
def get_neighbors():
    f = open('/etc/TD_neighbor/locators')
    l = f.readlines()
    l = [item.rstrip('\n') for item in l]
    return l[0], l[1:]
MY_ULA, NEIGHBOR_ULA = get_neighbors()  #ACP job to give the list of neighbors! ACP not available hence hardcoded

#########################
#Registering ASA 
#########################
def ASA_REG(name):
    mprint("registering asa and objective")
    err, asa_handle = graspi.register_asa(name)
    if not err:
        mprint("ASA registered successfully")
        return asa_handle, err
    else:
        mprint("Cannot register ASA:\n\t" + graspi.etext[err])
        mprint("exiting now.")


#########################
#Registering objectives
#########################
def OBJ_REG(name, value, neg, synch, loop_count, ASA, _local = False):
    obj = graspi.objective(name)
    obj.value = value
    obj.neg = neg
    obj.synch = synch
    obj.loop_count = loop_count
    err = graspi.register_obj(ASA, obj, local=_local)
    if not err:
        mprint("Objective registered successfully")
        if _old_API:
          for item in graspi._obj_registry:
                if item.objective.name == name:
                    mprint 
        else:
            for item in graspi.grasp._obj_registry:
                if item.objective.name == name:
                    mprint("$%#\n{}\n#$%".format(item.port),2)



    else:
        mprint("Cannot register Objective:\n\t"+ graspi.etext[err])
        mprint("exiting now.")
    return obj, err

###########
# mapping each objective to an ASA
###########
def TAG_OBJ(obj, ASA):
    return graspi.tagged_objective(obj, ASA)


def check_alive(_neighbors):
    req = multiping.MultiPing(_neighbors)
    req.send()
    _available, _not_available = req.receive(5)
    return _available, _not_available


def listen(_tagged, _listen_handler):
    mprint("start listening for objective {}".format(_tagged.objective.name))
    while True:
        err, handle, answer = graspi.listen_negotiate(_tagged.source, 
                                                      _tagged.objective)       
        if not err:
            mprint("\033[1;32;1m incoming request \033[0m")
            threading.Thread(target=_listen_handler, args=[_tagged,handle,answer]).start()
        else:
            mprint("\033[1;31;1m in listen error {} \033[0m" .format(graspi.etext[err]))

#shouldn't be here, but whatever !!!!
def sort_weight(_my_weight, _neighbor_info, _heavier, _heaviest, _lighter):
    max_weight = _my_weight
    mprint(_neighbor_info)
    for item in _neighbor_info:
        if _neighbor_info[item]['weight']> _my_weight:
            _heavier[item] = _neighbor_info[item]['weight']
            if _neighbor_info[item]['weight']> max_weight:
                _heaviest = item #locator #TODO subject to change if it joins another cluster
                max_weight = _neighbor_info[item]['weight']
        else:
            _lighter[item] = _neighbor_info[item]['weight']

    _heavier = dict(sorted(_heavier.items(), key=lambda item: item[1], reverse = True))
    mprint("heavier:{}".format(_heavier))
    mprint("lighter:{}".format(_lighter))
    mprint("heaviest:{}".format(_heaviest))
    return _heavier, _heaviest, _lighter

#########
# @param _heaviest takes the current heaviest(locator), return next one in line
# @return locator of the 2nd heaviest node
#########
def find_next_heaviest(_heaviest, _heavier):
    heavier_lst = list(_heavier.keys())
    if len(heavier_lst) == 0:
        return None
    if heavier_lst.index(_heaviest) == len(heavier_lst)-1:
        return None
    else:
        index = heavier_lst.index(_heaviest)
        return heavier_lst[index+1]

def ping_neighbor():    
    ping=multiping.MultiPing(NEIGHBOR_ULA)
    ping.send()
    result = ping.receive(2)
    return result

def discovery(_tagged, _discovery_handler, _attempts=3):
    mprint("entering discovery for {}".format(_tagged.objective.name))
    attempt = _attempts
    while attempt != 0:
        _, ll = graspi.discover(_tagged.source,_tagged.objective, 10000, flush=True, minimum_TTL=50000)
        for item in ll:
            mprint(str(item.locator))
        attempt-=1
    _discovery_handler(_tagged, ll)