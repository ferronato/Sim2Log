# Sim2Log
Gerador de logs simulados

Este projeto consiste em ferramenta de código aberto que permite ao usuário gerar logs sintéticos a partir de um arquivo no padrão XES. Os logs podem ser validados ao final do processo. Esta ferramenta foi escrita em Python e utiliza as bibliotecas pm4py, django e simpy. As principais funcionalidades são descritas abaixo:

    **Mineração de processos**
       Este módulo permite descobrir o modelo de processo a partir do log fornecido como entrada com uso de técnicas de mineração de processos. A descoberta do modelo é feita com o algoritmo inductive miner e várias estatísticas do log de eventos é utilizada para produzir os logs simulados. O modelo é descoberto utilizando o formalismo de redes de Petri. A rede de Petri permite identificar os fluxos de atividades. A extração da taxa de chegada dos casos no log inserido permite replicar ao comportamento no modelo de simulação criado para gerar logs sintéticos. 
   ** Simulação de eventos discretos**
        Este módulo permite executa a simulação dos logs artificiais com o framework simpy a partir dos atritutos obtidos no módulo de mineração de processos, gerar novos cases com as mesmas características como a distribuição de probabilidade da execução das atividades. O usuário pode alterar os parâmetros identificados se julgar necessário. O módulo permite configurar o número de cases que serão gerados de forma sintétca a partir do modelo identificado.
    **Visualização dos resultados em formato web**
        Este módulo permite a interação com o usuário com um ambiente web desenvolvido com o framework django para escolha do log a ser usado como entrada. A execução dos comandos é realizado com a visualização de cada etapa da geração dos logs. Os logs gerados são armazenados em dois formatos: a) XES - Padrão para uso em ferramentas de mineração de processos e b) CSV - Padrão usado com separador em vírgulas para permitir a rápida interação com ferramentas que utilizam este formato. Depois de gerar os logs, a validação da simulação é feita com o comparativo dos logs dados como entrada e os logs simulados, a nível de percentual de semelhança e também para o custo de alinhamento entre o log real e o log simulado.

Procedimento de configuração

Esta ferramenta é independente de sistema operacional e precisa que alguns pacotes em Python sejam instalados para o correto funcionamento. 

Passos para a instalação no formato convencional.
1) Faça o download do projeto do github
2) Descompacte em uma pasta no sistema operacional
3) Crie o ambiente virtual com o comando: python3 -m venv venv
4) Ative o ambiente virtual: venv\Scripts\activate.bat
5) Instale as bibliotecas requisitos do sistema: pip install -r requirements.txt
6) Execute a aplicação: python .\manage.py runserver
7) Acesse o link web da aplicação: http://127.0.0.1:8000/

Os arquivos dos logs sintéticos são gerados na pasta principal.


