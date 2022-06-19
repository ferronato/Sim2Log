from glob import glob
import math
import os
import statistics
import pandas as pd
import scipy.stats
import random
import re

from django.shortcuts import render
from django.contrib import messages
from django.core.files.storage import FileSystemStorage

import pm4py
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.visualization.petri_net import visualizer as pn_visualizer
from pm4py.objects.conversion.log import converter as log_converter
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.algo.filtering.log.variants import variants_filter
from pm4py.algo.conformance.alignments.edit_distance import algorithm as logs_alignments
from pm4py.algo.evaluation.replay_fitness import evaluator as replay_fitness_evaluator
from pm4py.algo.evaluation.precision import evaluator as precision_evaluator
from pm4py.algo.evaluation.generalization import evaluator as generalization_evaluator
from pm4py.algo.evaluation.simplicity import evaluator as simplicity_evaluator
from pm4py.statistics.traces.generic.log import case_arrival, case_statistics
from pm4py.algo.filtering.log.attributes import attributes_filter
from pm4py.objects.conversion.log import converter as log_converter

from sim2log.configs.settings import MEDIA_ROOT
from sim2log.configs.settings import BASE_DIR

import simulation as sm

processmodel_file = str(BASE_DIR) + "\\static\\results\\graph_model.png"
filelist = [processmodel_file]

'''
Etapas da Geração dos logs sintéticos:
1 - Leitura de um log de eventos
2 - Identificação do Modelo de Processo
3 - Parametrização para geração dos logs sintéticos
4 - Criação do Modelo de Simulação
5 - Execução do modelo de Simulação
6 - Geração dos logs sintéticos
7 - Validação dos logs gerados 
'''


def index(request):
    context = {}
    if request.method == 'POST':
        if request.POST.get("form_type") == 'formupload':
            uploaded_file = request.FILES['document']
            # print("arquivo:: ", uploaded_file)
            file = MEDIA_ROOT + "\\" + str(uploaded_file)
            if os.path.exists(file):
                os.remove(file)
            if uploaded_file.name.endswith('.xes'):
                savefile = FileSystemStorage()
                name = savefile.save(uploaded_file.name, uploaded_file)
                file_directory = MEDIA_ROOT + "\\" + name
                request.session['arquivo_xes'] = file_directory
                # print("file", request.session['arquivo_xes'])
                logGeral = xes_importer.apply(file_directory)
                context = {"valido": "sim"}
                messages.info(request, 'Arquivo xes válido!')
            else:
                messages.warning(
                    request, 'Arquivo inválido. Favor usar arquivo com extensão .xes!')

        elif request.POST.get("form_type") == 'formexec':
            resp = executepm(request)
            context.update(resp)
            context.update({"miner": "sim"})

        elif request.POST.get("form_type") == 'formsim':
            logGeral = xes_importer.apply(request.session['arquivo_xes'])
            txChegLog = getArrivalRate(logGeral)
            prepararAtividades(request, logGeral)
            nroCases = int(request.POST.get("cases"))
            txChegForm = request.POST.get('txcheg')
            # print("txChegForm",txChegForm)
            # print(type(txChegForm))
            # print(len(logGeral))
            # print('nrocases', nroCases)
            # print('txChegLog', txChegLog)
            # print('txChegForm', txChegForm)
            if txChegForm == '':
                txCheg = txChegLog
            else:
                txCheg = float(txChegForm)
            # print("txChegada",txCheg)
            # print(type(txCheg))

            sm.principal(logGeral, nroCases, txCheg)
            convertCsvToXES()
            resp4 = validarModelo(request)
            # print(resp4)
            resp3 = {'result2': 'Geração de logs concluída com sucesso!'}

            context.update(resp3)
            context.update(resp4)

    return render(request, 'pmining/principal.html', context)


def validarModelo(request):
    contextval = {}
    file = request.session.get('arquivo_xes')
    log = xes_importer.apply(file)
    # filesim = request.session.get('arquivo_sim')
    filesim = 'simulated-logs.xes'
    logsim = xes_importer.apply(filesim)
    parameters = {}
    alignments = logs_alignments.apply(log, logsim, parameters=parameters)
    sf = 0
    sc = 0
    for a in alignments:
        for k, v in a.items():
            # if k == 'alignment':
            # print("alinhamento:",a)
            if k == 'fitness':
                sf += v
                # print("chave: ", k, " value: ", v)
            if k == 'cost':
                sc += v
                # print("chave: ", k, " value: ", v)
    fitness = round(sf/len(alignments), 2)
    # print("media fitness",fitness)
    cost = sc/len(alignments)
    # print("media cost",cost)
    contextval = {'fitness': fitness, 'cost': cost}
    return contextval


def convertCsvToXES():

    event_log = pm4py.format_dataframe(pd.read_csv('simulated-logs.csv', sep=','), case_id='case_id',
                                       activity_key='activity', timestamp_key='time:timestamp')

    log = log_converter.apply(event_log)

    pm4py.write_xes(log, 'simulated-logs.xes')

    with open("simulated-logs.xes", "r") as f:
        contents = f.readlines()

    contents.insert(5, '<classifier name="Activity" keys="concept:name"/>\n')

    with open("simulated-logs.xes", "w") as f:
        contents = "".join(contents)
        f.write(contents)

    # from pm4py.objects.log.exporter.xes import exporter as xes_exporter
    # xes_exporter.apply(event_log, 'simulated-logs.xes')

    # print("tamlog",len(event_log))
    # print(event_log[0]) #prints the first trace of the log
    # print(event_log[0][0]) #prints the first event of the first trace


def prepararAtividades(request, logGeral):
    dicAtvSim = {}
    dicAtv = getTimes(logGeral)
    # print("dicAtv", dicAtv)
    keys = request.POST.keys()
    for ak, av in dicAtv.items():
        for k in keys:
            if k == 'atv-'+ak:
                # print(av, request.POST.get(k) )
                if request.POST.get(k) == '':
                    dicAtvSim.update({ak: av})
                else:
                    # print(ak,'valor novo',float(request.POST.get(k)))
                    dicAtvSim.update({ak: float(request.POST.get(k))})

    attributes = {}
    for trace in logGeral:
        for event in trace:
            if "concept:name" in event:
                attribute = event["concept:name"]
                if attribute not in attributes:
                    attributes[attribute] = math.ceil(dicAtvSim[attribute])
    # print('attributos', attributes)

    f = open("atividades.py", "w")
    f.write('''\
class Trace(object):
    def __init__(self,env):
        self.env = env       
    ''')
    for attribute in attributes:
        attribute2 = re.sub("[^A-Za-z]", "", attribute)
        f.write('''\
def %s(self):
        \tyield self.env.timeout(%d)       
    ''' % (str(attribute2), attributes[attribute]))
    f.close()

    # print(dicAtvSim)
    context = {'result': 'Arquivo preparado para a simulação!'}
    return context


def executepm(request):
    valfiltro = float(request.POST.get('filtro'))
    valfiltro2 = str(int(valfiltro * 100.0))
    request.session['val_filtro'] = valfiltro
    context = {}
    file = request.session.get('arquivo_xes')
    log = xes_importer.apply(file)
    logFilt = variants_filter.filter_log_variants_percentage(
        log, percentage=valfiltro)
    removefiles()
    petri = getPetri(logFilt, processmodel_file)
    variantes = str(len(logFilt)) + " -> " + valfiltro2 + "%"
    ev = evaluatelog(logFilt, petri[0], petri[1], petri[2])
    util = getArrivalRate(log) / getDispersionRate(log)
    txcheg = getArrivalRate(log)
    par = {'Nº de cases (variantes)': variantes,
           'Taxa de dispersão (m)': getDispersionRate(log), 'Uso do sistema': round(util, 2),
           'Duração média dos cases (m)': getduracaocases(log)}
    #    par = {'Nº de cases': len(log), 'Nº de cases (variantes)': variantes, 'Taxa de chegada (m)': pm.getArrivalRate(log),
    #        'Taxa de dispersão (m)': pm.getDispersionRate(log), 'Uso do sistema': round(util, 2),
    #        'Duração média dos cases (m)': pm.getduracaocases(log)}

    atv, rec, atvrec = orgmodel(logFilt)

    dicAtv = getTimes(logFilt)
    context = {'log': log, 'evaluate': ev, 'dic1': dicAtv, 'txcheg': txcheg,
               'parameters': par, 'atv': atv, 'rec': rec, 'atvrec': atvrec}
    return context


def getTimes(log):
    tempobase = {}
    for trace in log:
        length = len(trace)
        for index, event in enumerate(trace):
            if index < (length - 1):
                next_event = trace[index + 1]
                if "concept:name" in event:
                    attribute = event["concept:name"]
                    if "time:complete" in event:
                        if attribute not in tempobase:
                            tempobase[attribute] = [
                                (event["time:complete"] - event["time:timestamp"]).total_seconds()]
                        else:
                            tempobase[attribute].append(
                                (event["time:complete"] - event["time:timestamp"]).total_seconds())
                    else:
                        if "time:timestamp" in event:
                            time = event["time:timestamp"]
                        if "time:timestamp" in next_event:
                            next_time = next_event["time:timestamp"]
                        else:
                            next_time = time
                        if attribute not in tempobase:
                            tempobase[attribute] = [
                                (next_time - time).total_seconds()]
                        else:
                            tempobase[attribute].append(
                                (next_time - time).total_seconds())
            else:
                media = statistics.mean(tempobase[attribute])
                if "concept:name" in event:
                    attribute = event["concept:name"]
                if attribute not in tempobase:
                    tempobase[attribute] = [media]
                else:
                    tempobase[attribute].append(media)

    dfn = pd.DataFrame.from_dict(tempobase, orient='index')
    dfr = dfn.transpose()
    dfr.dropna(inplace=True)

    novoTempo = dfr.to_dict('list')
    distribuicao = {}
    for atributo in novoTempo:
        try:
            dst = Distribution()
            distribuicao[atributo] = dst.Fit(novoTempo[atributo])
        except:
            distribuicao = 'Poucos dados para a distribuição'
        novoTempo[atributo] = random.choice(novoTempo[atributo])

    return novoTempo


def removefiles():
    for f in filelist:
        if os.path.exists(f):
            os.remove(f)


class Distribution(object):
    def __init__(self, dist_name_list=[]):
        self.dist_names = ['norm', 'lognorm', 'expon']
        self.dist_results = []
        self.params = {}

        self.DistributionName = ""
        self.PValue = 0
        self.Param = None

        self.isFitted = False

    def Fit(self, y):
        self.dist_results = []
        self.params = {}
        for dist_name in self.dist_names:
            dist = getattr(scipy.stats, dist_name)
            param = dist.fit(y)
            self.params[dist_name] = param
            # Aplicação do teste de Kolmogorov-Smirnov
            D, p = scipy.stats.kstest(y, dist_name, args=param)
            self.dist_results.append((dist_name, p))
        # Selecionar a melhor distribuição
        sel_dist, p = (max(self.dist_results, key=lambda item: item[1]))
        # Armazenar o nome da melhor distribuição e seu p-value
        self.DistributionName = sel_dist
        self.PValue = p

        self.isFitted = True
        print("A distribuição é: ", self.DistributionName,
              " e seu p-value: ", self.PValue)

        return self.DistributionName, self.PValue


def getduracaocases(p_log):
    median_case_duration = case_statistics.get_median_caseduration(p_log, parameters={
        case_statistics.Parameters.TIMESTAMP_KEY: "time:timestamp"
    })
    return median_case_duration

# Método para extrair a taxa de chegada


def getArrivalRate(par_log):
    case_arrival_ratio = case_arrival.get_case_arrival_avg(par_log, parameters={
        case_arrival.Parameters.TIMESTAMP_KEY: "time:timestamp"})
    return round(case_arrival_ratio/60, 0)

# Método para extrair a taxa de saída


def getDispersionRate(p_log):
    case_dispersion_ratio = case_arrival.get_case_dispersion_avg(p_log, parameters={
        case_arrival.Parameters.TIMESTAMP_KEY: "time:timestamp"})
    return round(case_dispersion_ratio/60, 0)


def getPetri(p_log, processmodel_file):
    net, im, fm = inductive_miner.apply(p_log)
    gviz = pn_visualizer.apply(net, im, fm)
    pn_visualizer.save(gviz, processmodel_file)
    return net, im, fm

 # Avaliar a qualidade do modelo extraído com as medidas Fitness, Precisão, Generalização e Simplificação
def evaluatelog(p_log, p_net, p_im, p_fm):
    fitness = replay_fitness_evaluator.apply(p_log, p_net, p_im, p_fm,
                                             variant=replay_fitness_evaluator.Variants.ALIGNMENT_BASED)
    fitnessR = round(fitness.get('averageFitness'), 2)
    print("Fitness: ", fitnessR)
    precisao = precision_evaluator.apply(p_log, p_net, p_im, p_fm,
                                         variant=precision_evaluator.Variants.ETCONFORMANCE_TOKEN)
    precisaoR = round(precisao, 2)
    print("Precision: ", precisaoR)
    generalizacao = generalization_evaluator.apply(
        p_log, p_net, p_im, p_fm)
    generalizacaoR = round(generalizacao, 2)
    print("Generalization: ", generalizacaoR)
    simplicidade = simplicity_evaluator.apply(p_net)
    simplicidadeR = round(simplicidade, 2)
    print("Simplicity: ", simplicidadeR)
    return({'Fitness': fitnessR, 'Precisão': precisaoR, 'Generalização': generalizacaoR, 'Simplicidade': simplicidadeR})


def orgmodel(p_log):
    atividades = attributes_filter.get_attribute_values(
        p_log, "concept:name")
    # print("Atividades ", atividades)

    recursos = attributes_filter.get_attribute_values(
        p_log, "org:resource")
    # print("Recursos: ", [recursos])

    recursosporAtividade = {}
    for d in atividades:
        tracefilter_log_pos = attributes_filter.apply_events(p_log, d,
                                                             parameters={attributes_filter.Parameters.ATTRIBUTE_KEY: "concept:name", attributes_filter.Parameters.POSITIVE: True})
        resources = attributes_filter.get_attribute_values(
            tracefilter_log_pos, "org:resource")
        recursosporAtividade.update({d: list(resources.keys())})
    # recursosporAtividade2 = list(recursosporAtividade)[:5]
    # print("Recurso/atividade: ", recursosporAtividade)

    return atividades, recursos, recursosporAtividade
