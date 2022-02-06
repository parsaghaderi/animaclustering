import json
from cluster import *
from grasp import tagged_objective

NODE_ID, NEIGHBORS = readmap(MAP_PATH)
CLUSTER = False
CLUSTER_SET = []
HEAVIER = [] #nodes with heavier weights

INIT = False
err, cluster = ASA_REG("cluster")

def get_node_value(): #TODO change to get_node_weight
    rand = random.random()
    num_neighbors = len(NEIGHBORS)
    return num_neighbors*rand

WEIGHT = get_node_value()

WEIGHTS_RCVD = False
CH = False
NEIGHBOR_INFO = {}
node_json = {"node_id":NODE_ID,
             "weight": WEIGHT,
             "head": CLUSTER,
             "cluster_set": CLUSTER_SET}
def json_generator():
    return json.dumps(node_json)

node, err = OBJ_REG(NODE_ID, json_generator(), False,True,10,cluster)
tagged = TAG_OBJ(node,cluster)

def flooder(tagged, asa):
    while True:
        err = graspi.flood(asa, 59000, [graspi.tagged_objective(tagged.objective, None)])
        if not err:
            mprint("flooding objective {}".format(tagged.objective.name))
        else:
            mprint("can't flood because {}".format(graspi.etext[err]))
        sleep(1)

flooding_thread = threading.Thread(target=flooder, args=[tagged, cluster])
flooding_thread.start()

def listener(tagged, asa):
    try_fail = 20
    while try_fail > 0:
        mprint("listening for objective {}".format(tagged.objective.name))
        err, result = graspi.synchronize(
                        asa, 
                        tagged.objective,
                        None, 
                        5000)
        if not err:
            value  = json.loads(result.value)
            mprint(value)
            NEIGHBOR_INFO[value["node_id"]] = value
            if value["head"] == NODE_ID and CLUSTER == NODE_ID:
                CLUSTER_SET.append(value["node_id"])
                node.value["cluster_set"].append(value["node_id"])
                tagged.objective.value["cluster_set"].append(value["node_id"])
            try_fail = 20
        else:
            mprint("can't get weight from {}".format(
                                    graspi.etext[err]))
            try_fail-=1
        sleep(3)
    if try_fail == 0:
        link_failure(tagged.objective.value["node_id"])

listener_threads = []
neighbor_objective = []
neighbors_tagged = []
for item in NEIGHBORS:
    tmp, err = OBJ_REG(item, None, False,True,10,cluster)
    tmp_tagged = TAG_OBJ(tmp, cluster)
    if not err:
        neighbor_objective.append(tmp)
        neighbors_tagged.append(tmp_tagged)

for item in neighbors_tagged:
    listener_threads.append(threading.Thread(target=listener, args=[item, cluster]))

for item in listener_threads:
    item.start()
def check_weights():
    check = True
    while check:
        for item in NEIGHBORS:
            try:
                if NEIGHBOR_INFO[item]["weight"]:
                    check = False
                else:
                    check = True
            except:
                check = True
    WEIGHTS_RCVD = True
receiving_all_weight = threading.Thread(target=check_weights, args=[])
receiving_all_weight.start()

def send_ch(): #init pre
    global CLUSTER
    global INIT
    global HEAVIER

    while not WEIGHTS_RCVD:
        sleep(2) #wait until receive all weights
    mprint("in sending ch")
    max_id = 0
    max_weight = 0
    for item in NEIGHBORS:
        if NEIGHBOR_INFO[item]["weight"] > WEIGHT and NEIGHBOR_INFO[item]["weight"] > max_weight:
            max_id = item
        if NEIGHBOR_INFO[item]["weight"] > WEIGHT:
            HEAVIER.append(item)

    if max_id == 0:
        CLUSTER = NODE_ID
        node.value["head"] = NODE_ID
        node.value["cluster_set"].append(NODE_ID)
        tagged.objective.value["head"] = NODE_ID
        tagged.objective.value["cluster_set"].append(NODE_ID)
    INIT = True

init_procedure = threading.Thread(target=send_ch, args=[])
init_procedure.start()

def return_heads():
    head = 0
    head_weight = 0
    for item in HEAVIER:
        if NEIGHBOR_INFO[item]["weight"] > head_weight and NEIGHBOR_INFO[item]["head"] == item: #ch sets head to its own node_id
            head = item
    return head

def receive_ch():
    global CLUSTER
    while not INIT:
        sleep(2) #wait until init procedure is done
    check = True
    while check:
        for item in NEIGHBORS:
            if NEIGHBOR_INFO[item]["head"] != False:
                check = False
        sleep(2) #wait until the roles of heavier nodes are decided
    # head = 0
    # head_weight = 0
    # for item in HEAVIER:
    #     if NEIGHBOR_INFO[item]["weight"] > head_weight and NEIGHBOR_INFO[item]["head"] == item: #ch sets head to its own node_id
    #         head = item
    head = return_heads()
    if head != 0:
        CLUSTER = head
        node.value["head"] = head
        tagged.objective.value["head"] = head
        node.value["cluster_set"] = []
        tagged.objective.value["cluster_set"] = []
    

on_ch_receive = threading.Thread(target=receive_ch, args=[])
on_ch_receive.start()


def receive_join():
    while not INIT:
        sleep(2) #wait until init procedure is done
    mprint("in receiving join")
    while True:
        if NEIGHBOR_INFO[CLUSTER]["head"] != CLUSTER:
            head = return_heads()
            CLUSTER = head
            node.value["head"] = head
            tagged.objective.value["head"] = head
        sleep(5)

on_join_receive = threading.Thread(target=receive_join, args=[])
on_join_receive.start()

def join_link(): #TODO required ACP
    pass

def link_failure(node_id):
    global CLUSTER
    while True:
        if CLUSTER == node_id:
            NEIGHBORS.remove(node_id) #removed failed link date
            NEIGHBOR_INFO.pop(node_id) #removed failed link data
            if HEAVIER.__contains__(node_id):
                HEAVIER.remove(node_id)

            #look for a new head
            head = return_heads()
            if head != 0:
                CLUSTER = head
                node.value["head"] = head
                tagged.objective.value["head"] = head
                node.value["cluster_set"] = []
                tagged.objective.value["cluster_set"] = [] 
            else:
                CLUSTER = NODE_ID
                node.value["head"] = NODE_ID
                tagged.objective.value["head"] = NODE_ID
                node.value["cluster_set"].append(NODE_ID)
                tagged.objective.value["cluster_set"].append(NODE_ID)
        sleep(5)    


    
    

    
    
    

        
    