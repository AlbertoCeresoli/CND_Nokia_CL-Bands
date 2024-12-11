import networkx as nx
from ortools.linear_solver import pywraplp
from math import floor

# Create the SCIP solver.

class ILP_solver:


    solver = None
    amplifier_used = 0
    available_modulations = {} #-> should be a dictionary with element (rate,used_channel,max_distance); for now rate and used channel will be set to 1
    used_link = []
    objective_value = None
    solver = None
    graph = None
    demands = None
    V = []
    E = []
    n_wavelengths = None
    longest_link = {}


    def __init__(self,graph,demands,n_wavelengths, solver, modulations):


        self.solver = solver
        self.graph = graph
        self.demands = demands
        self.n_wavelengths = n_wavelengths
        self.available_modulations = modulations
        self.V = list(graph.nodes)
        E_u = list(graph.edges())
        self.E = []
        for e in E_u:
            self.E.append(e)
            self.E.append((e[1], e[0]))

        self.used_modulation = {}



    

    def ILP(self):

            
        
        C = self.solver.IntVar(0,self.solver.infinity(), 'Number_of_Lband_used') # variable that values the total number of links that needs to use C_band
        T = self.solver.IntVar(0,self.solver.infinity(), 'T')
        demand_cel = {} # variable that has value 1 if connection (src,dst) is routed on link e on wavelength l; 0 otherwise 

        lband_e = {} #variable that has value 1 if more then half the wavelength on link e is used

        used_channel_cnm = {} #number of channel used for n-th connection of c (src,dst) -> this is useless right now

        used_modulation_cnm = {} #modulation used for n-th connection of c(src,dst) -> this is used just to check the distance

        v_c = {}    #number of connection for the pair (src,dst)

        for (src,dst) in self.demands:
            
            if ((src,dst) not in v_c):
                v_c[(src,dst)] = []
                
            
            v_c[(src,dst)].append(1) #Right now, set to 1 the amount of traffic for each connection; every time the same pair (src,dst) is served, we just add a 1 to the array
 

        for (src,dst) in self.demands:
            for n in range(len(v_c[(src,dst)])):
                for m in range(len(self.available_modulations)):
                    if (src, dst) not in used_modulation_cnm:
                        used_modulation_cnm[(src, dst)] = {}
                    if n not in used_modulation_cnm[(src, dst)]:
                        used_modulation_cnm[(src, dst)][n] = {}

                    used_modulation_cnm[(src,dst)][n][m] = self.solver.BoolVar('used_modulation')


        x_cen = {}   #variable that has value 1 if link e compose path for n-th connection c between the same pair (src,dst)

        for (src,dst) in self.demands:
            for e in self.E:
                for n in range(len(v_c[(src,dst)])):
                    if (src, dst) not in x_cen:
                        x_cen[(src, dst)] = {}
                    if e not in x_cen[(src,dst)]:
                        x_cen[(src,dst)][e] = {} 
                
                    x_cen[(src,dst)][e][n] = self.solver.BoolVar('is_part_of_path{src}{dst}{e}{n}')

        M_cn = {}  #trick to find the longest link of a path

        for (src,dst) in self.demands:
            if(src,dst) not in M_cn:
                M_cn[(src,dst)] = {}
            for n in range(len(v_c[(src,dst)])):
                M_cn[(src,dst)][n] = self.solver.NumVar(0,self.solver.infinity(), 'M_{src}{dst}')



        distances = nx.get_edge_attributes(self.graph,'length')
        
        for e in self.E:
            if e not in distances:
                distances[(e[0],e[1])] = distances[(e[1],e[0])]


        for e in self.E:
            lband_e[e] = self.solver.IntVar(0,1,'demand_{e}')




        for (src,dst) in self.demands:
            for n in range(len(v_c[(src,dst)])):
                for e in self.E:
                    for wav in range(self.n_wavelengths):
                    
                    
                        if (src, dst) not in demand_cel:
                            demand_cel[(src, dst)] = {}
                        if n not in demand_cel[(src,dst)]:
                            demand_cel[(src,dst)][n] = {}
                        if (e[0], e[1]) not in demand_cel[(src, dst)][n]:
                            demand_cel[(src, dst)][n][(e[0], e[1])] = {}
                        if (e[1], e[0]) not in demand_cel[(src, dst)][n]:
                            demand_cel[(src, dst)][n][(e[1], e[0])] = {}
                        
                        demand_cel[(src,dst)][n][(e[0],e[1])][wav] = self.solver.IntVar(0,1,'demand_{src}{dst}{e}{wav}')
                        demand_cel[(src,dst)][n][(e[1],e[0])][wav] = self.solver.IntVar(0,1,'demand_{src}{dst}{e}{wav}')



        final_list = []
        for demand in self.demands:
            if demand not in final_list:
                final_list.append(demand)
                
        self.demands = final_list

        for (src, dst) in self.demands:
            for n in range(len(v_c[(src,dst)])):
                for v in self.V:
            
                    flow_out = sum(demand_cel[(src,dst)][n][(v,v_i)][wav] for v_i in self.V  if (v,v_i) in self.E for wav in range(self.n_wavelengths))
                    flow_in = sum(demand_cel[(src,dst)][n][(v_j,v)][wav] for v_j in self.V if (v_j,v) in self.E for wav in range(self.n_wavelengths))

                    if v == src:
                        self.solver.Add((flow_out - flow_in) == v_c[(src,dst)][n])

                    elif v == dst:
                        self.solver.Add((flow_out - flow_in) == -v_c[(src,dst)][n])
                    
                    else:
                        self.solver.Add((flow_out - flow_in) == 0)
            
    # wavelength continuity -> to enforce that the same wavelength for each connection in each link is used, we add this constrain. It only enforce this behaviour on the intermediate node of the connection,
    # but this is enough to force it also on the source and destination node.

        for (src, dst) in self.demands:
            for n in range(len(v_c[(src,dst)])):
                for v in self.V:

                    for wav in range(self.n_wavelengths):
                
                        flow_out = sum(demand_cel[(src,dst)][n][(v,v_i)][wav] for v_i in self.V  if (v,v_i) in self.E )
                        flow_in = sum(demand_cel[(src,dst)][n][(v_j,v)][wav] for v_j in self.V if (v_j,v) in self.E )

                        if v != src and v != dst:
                            self.solver.Add((flow_out - flow_in) == 0)

        # each demand can only be assigned to one wavelength -> there is the situation in which there is more then a single connection from source src to destination dst; in that case, we have to use
        # more wavelength on the same link for the i-th connection from s to d (set <= to the total number of connection v_c[(s,d)])
                
        for (src,dst) in self.demands:
            for n in range(len(v_c[(src,dst)])):
                for e in self.E:
                    self.solver.Add(sum(demand_cel[(src,dst)][n][e][wav] for wav in range(self.n_wavelengths)) <= v_c[(src,dst)][n])
                
        # each link is bidirectional, so there is a different variable to describe the two different direction; but this has the problem of doubling the number of wavelength in each link.
        # Of course, if we are using wavelength 1 in link 0->2, that wavelength is not available for link 2->0 (they are the same link after all!) -> so we need to add this constrain to force wav[1] on 2->0 to zero
        # if wav[1] == 1 on 0->2, and viceversa

        for link1 in self.E:
            for link2 in self.E:
                if(link1[0] == link2[1] and link1[1] == link2[0]):
                    for wav in range(self.n_wavelengths):
                        self.solver.Add(sum(demand_cel[(src,dst)][n][link1][wav] + demand_cel[(src,dst)][n][link2][wav] for (src,dst) in self.demands for n in range(len(v_c[(src,dst)]))) <= 1)

        # different demands cannot use the same wavelength on the same link -> same reasoning of before; if we have more then 1 connection from the same source to the same destination, we should be able to use more
        # wavelength (one for each connection of the same pair (src,dst))

        for e in self.E:
            for (src,dst) in self.demands:
                for n in range(len(v_c[(src,dst)])):
                    self.solver.Add(sum(demand_cel[(src,dst)][n][e][wav] for wav in range(self.n_wavelengths)) <= v_c[(src,dst)][n])


        # if we use more then half of the wavelength on a single fiber, it means that we need to use the L band on it

        for e in self.E:
            self.solver.Add(sum(demand_cel[(src,dst)][n][e][wav] for wav in range(floor(self.n_wavelengths/2)) for (src,dst) in self.demands for n in range(len(v_c[(src,dst)]))) <=(lband_e[e]))


        # We now get the maximum value of M to be equal to the longest link of each connection

        #First thing first, we set the value of x_ce to 1 if the link e is used by src,dst

        for (src,dst) in self.demands:
            for e in self.E:
                for n in range(len(v_c[(src,dst)])):
                    self.solver.Add(sum(demand_cel[(src,dst)][n][e][wav] for wav in range(self.n_wavelengths)) <= x_cen[(src,dst)][e][n]*v_c[(src,dst)][n])
            
        for (src,dst) in self.demands:
            
            for n in range(len(v_c[(src,dst)])):
                for e in self.E:
                    self.solver.Add(M_cn[(src,dst)][n]>=x_cen[(src,dst)][e][n]*distances[e] ) #-> Now M is forced to be greater then the longest link
        
        #Choosing modulation -> the max length of single link must be lesser than the max distance of the modulation; then, it's best if it occupies the least amount of channels;
        #then, it's best if it has the higher bit rate


        for (src,dst) in self.demands:
            for n in range(len(v_c[(src,dst)])):
                self.solver.Add(sum(used_modulation_cnm[(src,dst)][n][m] for m in range(len(self.available_modulations)))==1)
                self.solver.Add(M_cn[(src,dst)][n]<=sum(used_modulation_cnm[(src,dst)][n][m]*self.available_modulations[m]['max_distance'] for m in range(len(self.available_modulations))))

                
                
        # We force the cost to be more then the sum of all the lband_e variable

        self.solver.Add(sum(lband_e[e] for e in self.E)<=C)

        # We force that the modulation choose the fastest possible, between the possible one

        self.solver.Add(T<=sum(used_modulation_cnm[(src,dst)][n][m] * self.available_modulations[m]['rate'] for (src,dst) in self.demands for n in range(len(v_c[(src,dst)])) for m in range(len(self.available_modulations))))

        self.solver.Minimize(100*C-T+sum(demand_cel[(src,dst)][n][e][wav] for (src,dst) in self.demands for n in range(len(v_c[(src,dst)])) for e in self.E for wav in range(self.n_wavelengths))+sum(M_cn[(src,dst)][n] for (src,dst) in self.demands for n in range(len(v_c[(src,dst)])))/10000)
        self.solver.Solve()

        self.used_link = []
        for (src,dst) in self.demands:
            for n in range(len(v_c[(src,dst)])):
                for e in self.E:
                    for wav in range(self.n_wavelengths):
                            if(demand_cel[(src,dst)][n][e][wav].solution_value() != 0):
                                self.used_link.append((e))

        self.longest_link = {}
        for (src,dst) in self.demands:
            if (src,dst) not in self.longest_link:
                self.longest_link[(src,dst)] = {}
                for n in range(len(v_c[(src,dst)])):
                    self.longest_link[(src,dst)][n] = M_cn[(src,dst)][n].solution_value() #debugging reason

        for (src,dst) in self.demands:
            for n in range(len(v_c[(src,dst)])):
                for m in range(len(self.available_modulations)):
                    if (src,dst) not in self.used_modulation:
                        self.used_modulation[(src,dst)] = {}
                    if n not in self.used_modulation[(src,dst)]:
                         self.used_modulation[(src,dst)][n] = {}
                    self.used_modulation[(src,dst)][n][m] = used_modulation_cnm[(src,dst)][n][m].solution_value()
        self.objective_value =  C.solution_value()
        
    

