from grasp import _initialise_grasp
import threading
def init_grasp():
    while True:
        _initialise_grasp()
        while True:
            pass
threading.Thread(target=init_grasp, args = []).start()
