import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import json
import math
from itertools import islice
from ILP_solver import *


# ILP solver

def get_network_rwa_json(fp: str, n_wavelengths: int) -> nx.Graph:
    with open(fp, mode='r') as file:
        in_data = json.load(file)
    G = nx.node_link_graph(in_data)
    #Initialize an empty dictionary available_wavelengths
    available_wavelengths = {}
    #For each edge in G:
    for i in G.edges:
        #Set available_wavelengths[edge] to an array of ones with length n_wavelengths and data type uint8
        available_wavelengths[i] = np.ones((n_wavelengths,), dtype=np.uint8)
    #Set the "available_wavelengths" attribute for all edges in G to the available_wavelengths dictionary
    nx.set_edge_attributes(G, available_wavelengths, "available_wavelengths")
    #Set the graph attribute "n_wavelengths" in G to n_wavelengths
    G.graph["n_wavelengths"] = n_wavelengths
    #Return the graph G
    return G


num_spectrum = 0
#Set n_wavelengths to 3
n_wavelengths = 4



G = get_network_rwa_json("./nsfnet.json", n_wavelengths=n_wavelengths)

new_dict = {}
new_dict[0] = {'rate': 0.5, 'used_channel': 1, 'max_distance': 1200} #-> Note: normalize the rate to 1 (min value), il resto va di conseguenza
new_dict[1] = {'rate': 0.2, 'used_channel': 1, 'max_distance': 600}
new_dict[2] = {'rate': 1, 'used_channel': 1, 'max_distance': 3000}



demands = [(1,4,2),(3,4,6),(0,7,2)]
solver = pywraplp.Solver.CreateSolver('SCIP')
if not solver:
    print("SCIP solver not found.")

x = ILP_solver(G,demands,4,solver,new_dict)
x.ILP()

used_wav = {}
for e in x.E:
    if e not in used_wav:
        
        used_wav[e] = {}
sum = 0
for e in x.E:
    
    for wav in range(x.n_wavelengths):
        for (src,dst) in x.demands:
        
        
            sum = sum + x.demand_cel[(src,dst)][e][wav] + x.demand_cel[(src,dst)][(e[1],e[0])][wav]
        used_wav[e][wav] = sum
        sum = 0

for e in x.E:
    for wav in range(x.n_wavelengths):
        if e in used_wav:
            x.graph[e[0]][e[1]]['available_wavelengths'][wav] = used_wav[e][wav]

plt_2 = plt.figure(figsize=(16, 9))

nx.draw(x.graph, pos=nx.get_node_attributes(x.graph, "pos"), with_labels=True)
for demand in demands:
    route = demand[-2]
    nx.draw_networkx_edges(x.graph, pos=nx.get_node_attributes(x.graph, "pos"), edgelist=x.used_link, width=10, alpha=0.1/(len(demands)), edge_color='red')  #/len(demands to mantain an equal shade of color between the two graphs)
nx.draw_networkx_edge_labels(
    x.graph, pos=nx.get_node_attributes(x.graph, 'pos'),
    edge_labels=nx.get_edge_attributes(x.graph, 'available_wavelengths'),
    bbox=dict(alpha=0),
    font_size=11,
    font_weight='bold',
    verticalalignment='center');
print(f'Spectrum occupation is: {x.objective_value}')