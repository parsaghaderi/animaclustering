import json
from cluster import *

NODE_ID, NEIGHBORS = readmap(MAP_PATH)
CLUSTER = False
CLUSTER_SET = []

err, cluster = ASA_REG("cluster")

def get_node_value(): #TODO change to get_node_weight
    rand = random.random()
    num_neighbors = len(NEIGHBORS)
    return num_neighbors*rand

WEIGHT = get_node_value()
node_json = {"name":NODE_ID,
             "weight": WEIGHT,
             "head": CLUSTER,
             "cluster_set": CLUSTER_SET}
def json_generator():
    return json.dumps(node_json)

node, err = OBJ_REG("test", node_json, False,True,10,cluster)
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
    while True:
        mprint("listening for objective {}".format(tagged.objective.name))
        err, result = graspi.synchronize(
                        asa, 
                        tagged.objective,
                        None, 
                        5000)
        if not err:
            pass
        else:
            mprint("can't get weight from {}".format(
                                    graspi.etext[err]))
        sleep(3)


listeners = threading.Thread(target=listener, args=[tagged, cluster])
listeners.start()