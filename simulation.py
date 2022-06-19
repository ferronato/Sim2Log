from datetime import datetime, timedelta
import importlib
import sys
import warnings
import csv
from copy import copy
from random import shuffle
import random
import simpy
import pm4py.objects.log.obj as log_instance
from pm4py.objects.petri_net import semantics
from pm4py.util import xes_constants
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
import re
import sys, os

case_id_key = xes_constants.DEFAULT_TRACEID_KEY
activity_key = xes_constants.DEFAULT_NAME_KEY
timestamp_key = datetime.now()
results = []

warnings.filterwarnings('ignore')


def principal(log, nroCases, txCheg):
    nroTraces = nroCases
    net, im, fm = getPetri(log)
    print("Resultado da simulação será armazenado em simulated-logs.csv e simulated-logs.xes")
    random.seed(41)  # Reprodução dos resultados
    env = simpy.Environment()  # Cria o ambiente
    # Cria a configuração
    env.process(setup(env, nroTraces, net, im, txCheg))
    # Executar!
    env.run()

def getPetri(p_log):
    net, im, fm = inductive_miner.apply(p_log)
    return net, im, fm

def setup(env, nroTraces, net, im, txCheg):
    """
    :param env: Ambiente de simulação
    :param nroTraces: Número de traces que serão gerados
    :param net: A rede de Petri que representa o processo
    :param im: A marcação inicial das atividades do modelo
    """
    module = __import__('atividades')
    importlib.reload(sys.modules['atividades'])
    casegen = module.Trace(env)

    # Cria casos enquanto a simulação está sendo executada
    for i in range(1, nroTraces+1):
        yield env.timeout(txCheg)
        env.process(simulation(env, 'Case %d' %
                    i, casegen, net, im, nroTraces))


def simulation(env, case_num, case, net, initial_marking, no_traces):
    """
    :param env: Ambiente da simulação
    :param case_num: ID do case
    :param case: O nome da ativdade para chamar o método específico
    :param net: A rede de Petri que representa o processo
    :param im: A marcação inicial das atividades do modelo
    :param no_traces: Número de traces que serão gerados
    """
    max_trace_length = 1000  # Only traces with length lesser than 1000 are created
    f = open('simulated-logs.csv', 'w', newline='')
    thewriter = csv.writer(f)
    # thewriter.writerow(['case_id', 'activity', 'time:timestamp'])
    thewriter.writerow(['case_id', 'activity', 'time:timestamp'])
    curr_timestamp = datetime.now()
    log = log_instance.EventLog()
    trace = log_instance.Trace()
    trace.attributes[case_id_key] = str(case_num.replace('Case', ''))
    marking = copy(initial_marking)
    while True:
        if not semantics.enabled_transitions(net, marking):
            break
        all_enabled_trans = semantics.enabled_transitions(net, marking)
        all_enabled_trans = list(all_enabled_trans)
        shuffle(all_enabled_trans)
        trans = all_enabled_trans[0]
        if trans.label is not None:
            event = log_instance.Event()
            event[activity_key] = trans.label
            results.append([case_num, event[activity_key],
                           datetime.now() + timedelta(seconds=env.now)])
            label2 = re.sub("[^A-Za-z]", "", trans.label)
            yield env.process(getattr(case, str(label2))())
            event[timestamp_key] = curr_timestamp
            trace.append(event)
        marking = semantics.execute(trans, net, marking)
        if len(trace) > max_trace_length:
            break
    if len(trace) > 0:
        log.append(trace)

        results.append(
            [case_num, "case end", datetime.now() + timedelta(seconds=env.now)])

    for row in results:
        thewriter.writerow(row)

    f.close()
    return log

