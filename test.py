from cluster import *
import subprocess as sp
from time import sleep

from grasp import objective

err, asa = ASA_REG('testing')

obj_synch, err = OBJ_REG('test_synch', None, False, True ,50, asa)
tagged_synch   = TAG_OBJ(obj_synch, asa)
obj_neg,   err = OBJ_REG('test_neg',   None, True , False,50, asa)
tagged_neg     = TAG_OBJ(obj_neg, asa)

def get_name():
    return sp.getoutput('hostname')


def flooder(tagged):
    while True:
        err = graspi.flood(tagged.source, 59000, [graspi.tagged_objective(tagged.objective, None)])
        if not err:
            mprint("flooding objective {}'s role".format(tagged.objective.name))
        else:
            mprint("can't flood because {}".format(graspi.etext[err]))
        sleep(1.5)


def negotiate_listener_side(tagged, handle, answer, old):
    _old_API = old
    answer.value=cbor.loads(answer.value)
    if answer.dry:
        mprint("Dry run")
        result = True
        reason = None
        
    elif answer.value < 1000:
        step = 1
        neg_loop = True
        while neg_loop:
            mprint("peer offered {} - step {}".format(answer.value, step))
            answer.value += 1 #based on grasp doc page 12 comment section paragraph 5 line 2
            answer.value=cbor.dumps(answer.value)
            neg_step_output = graspi.negotiate_step(tagged.source, handle, answer, 1000)
            if _old_API:
                err, temp, answer = neg_step_output #TODO figure out whats each of them 
                reason = answer
            else:
                err, temp, answer, reason = neg_step_output
            mprint("peer offered {} {} {} {}".format(err, temp, answer, reason))
            step += 1
            if (not err) and temp == None:
                neg_loop = False
                mprint("negotiation succeeded")
            elif not err:
                try:
                    answer.value = cbor.loads(answer.value)
                except:
                    pass
                mprint("loop count {}, request {}".format(answer.loop_count, answer.value))
                if tagged.objective.value < answer.value:
                    tagged.objective.value = answer.value
                elif tagged.objective.value > 1000:
                    neg_loop = False
    else:
        err = graspi.end_negotiate(tagged.source, handle, True)
        if not err:
            mprint("negotiation done with value {}".format(answer.value))
                
            
def negotiate_request_side(tagged, old):
    _old_API = old
    while True:
        _, ll = graspi.discover(tagged.source, tagged.objective, 1000, flush = True)

        if ll == []:
            mprint("discovery failed, no handlers found")
            continue
        mprint("{} locators found, locator {} was chosen".format(len(ll), ll[0].locator))
        tagged.objective.value = cbor.dumps(tagged.objective.value)
        if _old_API:
            err, handle, answer = graspi.req_negotiate(tagged.source, tagged.objective, ll[0], None)
            reason = answer
        else:
            err, handle, answer, reason = graspi.req_negotiate(tagged.source, tagged.objective, ll[0], None)
        
        if err:
            mprint("neg request failed because {}".format(graspi.etext[err]))
            continue
        elif (not err) and handle:
            mprint("session started {}, answer {}".format(handle, answer))
            try:
                answer.value = cbor.loads(answer.value)
            except:
                pass
            mprint("peer offered {}".format(answer.value))
            step = 1
            if answer.value < 1000:
                answer.value += 1
                neg_loop = True
                while neg_loop:
                    answer.value = cbor.dumps(answer.value)
                    _r = graspi.negotiate_step(tagged.source, handle, answer, 1000)
                    if _old_API:
                        err, temp, answer = _r
                        reason = answer
                    else:
                        err, temp, answer, reason = _r
                    mprint("loopcount {}, offered {}".format(answer.loop_count, answer.value))
                    step += 1
                    if answer.value == 1000:
                        err, graspi.end_negotiate(tagged.source, handle, True)
                        if not err:
                            mprint("negotiation successfully done!")
                            neg_loop = False
        else:
            neg_loop = False
            break
        






def listen_neg(tagged):
    while True:
        err, handle, answer = graspi.listen_negotiate(tagged.source, tagged.objective)
        if not err:
            if answer.value != tagged.objective.value:
                threading.Thread(target=negotiate_listener_side, args=[tagged, handle, answer, _old_API]).start()
            else: #answer == obj.value no need for negotiation
                pass #end negotiation
        if err:
            mprint("listen negotiation err {}".format(graspi.etext[err]))
            break

        sleep(3)


def synch(tagged):
    while True:
        err, result = graspi.synchronize(
                    tagged.source,
                    tagged.objective,
                    None, 
                    59000
                    )      
        if not err:
            mprint("synch successful with value {}".format(result.value))
        sleep(3)


if get_name() == 'Dijkstra':
    obj_synch.value = 'Dijkstra_synch'
    obj_neg.value = 1
    threading.Thread(target=flooder,    args = [tagged_synch]).        start()
    threading.Thread(target=listen_neg, args = [tagged_neg])  .        start()

if get_name() == 'Ritchie':
    threading.Thread(target=synch,      args = [tagged_synch]).        start()

if get_name() == 'Gingko':
    tagged_neg.objective.value = 50
    threading.Thread(target=negotiate_request_side, args=[tagged_neg, _old_API]).start()

