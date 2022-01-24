from time import sleep
from cluster import *
import random
import threading
HEAD = False
NODE_ID, NEIGHBORS = readmap(MAP_PATH)
CLUSTER = False
CLUSTER_SET = []

'''
each time node receives an update from neighbors
the update will be saved in this dict.
Update messages can be:
    * join(u, v) where u is the neighbor ID and v is the node they're joining
    * head(v) where v is the neighbor and announces itself as clusterhead
the values in dict are initialized to False.
'''
RCV_NEIGHBORS = dict((RCV_NEIGHBORS,False) for RCV_NEIGHBORS in NEIGHBORS)

'''
registering ASA named cluster
'''
cluster = ASA_REG("cluster")


def get_node_value():
    rand = random.random()
    num_neighbors = len(NEIGHBORS)
    return num_neighbors*rand
'''
registering objective called node
the value of this objective is weight of the node.
it's only for sync. 
@param name = node ; same in all nodes
@param neg = False
@param synch = True
@param value = random number + number of neighbors
@param asa
@param loop-count 
'''
# node = OBJ_REG("node", get_node_value(), False, True, 10, cluster)

testobj = OBJ_REG(NODE_ID, get_node_value(), False, True, 10, cluster)

def changetestvalue(obj):
    while True:
        sleep(10)
        obj.value +=1

tagged = TAG_OBJ(testobj, cluster)

class flooder(threading.Thread):
    def __init__(self, obj):
        threading.Thread.__init__(self)
        self.obj = obj
    def run(self):
        while True:
            err = graspi.flood(self.obj.source, 59000, [graspi.tagged_objective(self.obj.objective, None)])
            time.sleep(3)

threading.Thread(target=changetestvalue, args=[]).start()
flooder(tagged).start()



