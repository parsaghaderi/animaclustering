from cluster import *
import subprocess as sp
from time import sleep

err, asa = ASA_REG('testing')

obj_synch, err = OBJ_REG('test_synch', None, False, True ,50, asa)
tagged_synch   = TAG_OBJ(obj_synch, asa)
obj_neg,   err = OBJ_REG('test_neg',   None, True , False,50, asa)
tagged_neg     = TAG_OBJ(obj_neg, asa)

def get_name():
    return sp.getoutput('hostname')


if get_name() == 'Dijkstra':
    obj_synch.value = 'Dijkstra_synch'
    obj_neg.value = 'Dijkstra_neg'

def flooder(tagged):
    while True:
        err = graspi.flood(tagged.source, 59000, [graspi.tagged_objective(tagged.objective, None)])
        if not err:
            mprint("flooding objective {}'s role".format(tagged.objective.name))
        else:
            mprint("can't flood because {}".format(graspi.etext[err]))
        sleep(1.5)

if get_name() == 'Dijkstra':
    threading.Thread(target=flooder, args=[tagged_synch]).start()

def synch(tagged):
    err, result = graspi.synchronize(
                tagged.source,
                tagged.objective,
                None, 
                59000
                )      
    if not err:
        mprint("synch successful with value {}".format(result.value))

if get_name() == 'Ritchie':
    threading.Thread(target=synch, args=[obj_synch]).start()




