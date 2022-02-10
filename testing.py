from unittest import result
from cluster import *
import subprocess as sp
import sys
from time import sleep
def get_ll_address():
    try:
        f = open('/etc/TD_map/interfaces.txt')
    except:
        f = None
    if f == None:
        mprint("interfaces doesn't exist")
        return 0
    # interfaces = f.readlines().rstrip('\n')
    interfaces = f.read().splitlines()
    # interfaces = [item for item in interfaces]

    out_lines = sp.getoutput('ip -6 neigh').splitlines()
    neighbors = []
    for line in out_lines:
        tmp = line.split()
        if interfaces.__contains__(tmp[2]):
            neighbors.append([tmp[2], tmp[0]])
    
    return neighbors


err, test_ASA = ASA_REG("test")
if sys.argv[1] == 'mc':
    obj, err = OBJ_REG('test_obj', 10, False, True, 10, test_ASA)
    tagged = TAG_OBJ(obj, test_ASA)
else:
    obj, err = OBJ_REG('test_obj', 0, False, True, 10, test_ASA)
    tagged = TAG_OBJ(obj, test_ASA)


def flooder(tagged, asa):
    while True:
        err = graspi.flood(asa, 59000, [graspi.tagged_objective(tagged.objective, None)])
        if not err:
            mprint("flooding")
        else:
            mprint("can't flood")
        sleep(1)

flooder_thread = threading.Thread(target=flooder, args=[tagged, test_ASA])

if sys.argv[1] == 'mc':
    flooder_thread.start()

def listener(tagged, asa, ll):
    while True:
        mprint("listening")
        err, result = graspi.synchronize(
                    asa, 
                    tagged.objective, 
                    ll, 
                    5000
        )       
        if not err:
            mprint(result.value)
        else:
            mprint("didn't work | {}".format(graspi.etext[err]))
        sleep(3)
ll = get_ll_address()
listening = threading.Thread(target=listener, args=[tagged, test_ASA, ll[0][1]])
if sys.argv[1] != 'mc':
    # listening.start()
    print(graspi.discover(test_ASA, obj, 59000))