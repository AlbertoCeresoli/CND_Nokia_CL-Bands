import networkx as nx
from ortools.linear_solver import pywraplp
from math import floor

# Create the SCIP solver.

class ILP_solver:


    solver = None
    amplifier_used = 0
    avalilable_modulations = {} #-> should be a dictionary with element (rate,used_channel,max_distance); for now rate and used channel will be set to 1
    used_link = []
    objective_value = None
    solver = None
    graph = None
    demands = None
    V = []
    E = []
    n_wavelengths = None

    def __init__(self,graph,demands,n_wavelengths, solver, modulations):


        self.solver = solver
        self.graph = graph
        self.demands = demands
        self.n_wavelengths = n_wavelengths
        self.avalilable_modulations = modulations
        self.V = list(graph.nodes)
        E_u = list(graph.edges())
        self.E = []
        for e in E_u:
            self.E.append(e)
            self.E.append((e[1], e[0]))



    

    def ILP(self):

            
        
        C = self.solver.IntVar(0,self.solver.infinity(), 'Number_of_Lband_used') # variable that values the total number of links that needs to use C_band

        demand_cel = {} # variable that has value 1 if connection (src,dst) is routed on link e on wavelength l; 0 otherwise 

        lband_e = {} #variable that has value 1 if more then half the wavelength on link e is used

        v_c = {}    #number of connection for the pair (src,dst)

        Nb_amplifier = self.solver.IntVar(0,self.solver.infinity(), 'Nb_amplifier')

        distances = nx.get_edge_attributes(self.graph,'length')
        
        for e in self.E:
            if e not in distances:
                distances[(e[0],e[1])] = distances[(e[1],e[0])]

        used_modulation_c = {} #modulation used for connection c

        for e in self.E:
            lband_e[e] = self.solver.IntVar(0,1,'demand_{e}')

        for (src,dst) in self.demands:
            used_modulation_c[(src,dst)] = self.solver.IntVar(0,1,'modulation')

        for (src,dst) in self.demands:
            
            if ((src,dst) not in v_c):
                v_c[(src,dst)] = 0
            
            v_c[(src,dst)] = v_c[(src,dst)] + 1



        for (src,dst) in self.demands:
            for e in self.E:
                for wav in range(self.n_wavelengths):
                    
                    if (src, dst) not in demand_cel:
                        demand_cel[(src, dst)] = {}
                    if (e[0], e[1]) not in demand_cel[(src, dst)]:
                        demand_cel[(src, dst)][(e[0], e[1])] = {}
                    if (e[1], e[0]) not in demand_cel[(src, dst)]:
                        demand_cel[(src, dst)][(e[1], e[0])] = {}
                    
                    demand_cel[(src,dst)][(e[0],e[1])][wav] = self.solver.IntVar(0,1,'demand_{src}{dst}{e}{wav}')
                    demand_cel[(src,dst)][(e[1],e[0])][wav] = self.solver.IntVar(0,1,'demand_{src}{dst}{e}{wav}')



        final_list = []
        for demand in self.demands:
            if demand not in final_list:
                final_list.append(demand)
                
        self.demands = final_list

        for (src, dst) in self.demands:
            for v in self.V:
            
                flow_out = sum(demand_cel[(src,dst)][(v,v_i)][wav] for v_i in self.V  if (v,v_i) in self.E for wav in range(self.n_wavelengths))
                flow_in = sum(demand_cel[(src,dst)][(v_j,v)][wav] for v_j in self.V if (v_j,v) in self.E for wav in range(self.n_wavelengths))

                if v == src:
                    self.solver.Add((flow_out - flow_in) == v_c[(src,dst)])

                elif v == dst:
                    self.solver.Add((flow_out - flow_in) == -v_c[(src,dst)])
                
                else:
                    self.solver.Add((flow_out - flow_in) == 0)
            
    # wavelength continuity -> to enforce that the same wavelength for each connection in each link is used, we add this constrain. It only enforce this behaviour on the intermediate node of the connection,
    # but this is enough to force it also on the source and destination node.

        for (src, dst) in self.demands:
            for v in self.V:

                for wav in range(self.n_wavelengths):
                
                    flow_out = sum(demand_cel[(src,dst)][(v,v_i)][wav] for v_i in self.V  if (v,v_i) in self.E )
                    flow_in = sum(demand_cel[(src,dst)][(v_j,v)][wav] for v_j in self.V if (v_j,v) in self.E )

                    if v != src and v != dst:
                        self.solver.Add((flow_out - flow_in) == 0)

        # each demand can only be assigned to one wavelength -> there is the situation in which there is more then a single connection from source src to destination dst; in that case, we have to use
        # more wavelength on the same link for the i-th connection from s to d (set <= to the total number of connection v_c[(s,d)])
                
        for (src,dst) in self.demands:
                for e in self.E:
                    self.solver.Add(sum(demand_cel[(src,dst)][e][wav] for wav in range(self.n_wavelengths)) <= v_c[(src,dst)])
                
        # each link is bidirectional, so there is a different variable to describe the two different direction; but this has the problem of doubling the number of wavelength in each link.
        # Of course, if we are using wavelength 1 in link 0->2, that wavelength is not available for link 2->0 (they are the same link after all!) -> so we need to add this constrain to force wav[1] on 2->0 to zero
        # if wav[1] == 1 on 0->2, and viceversa

        for link1 in self.E:
            for link2 in self.E:
                if(link1[0] == link2[1] and link1[1] == link2[0]):
                    for wav in range(self.n_wavelengths):
                        self.solver.Add(sum(demand_cel[(src,dst)][link1][wav] + demand_cel[(src,dst)][link2][wav] for (src,dst) in self.demands) <= 1)

        # different demands cannot use the same wavelength on the same link -> same reasoning of before; if we have more then 1 connection from the same source to the same destination, we should be able to use more
        # wavelength (one for each connection of the same pair (src,dst))

        for e in self.E:
            for (src,dst) in self.demands:
                self.solver.Add(sum(demand_cel[(src,dst)][e][wav] for wav in range(self.n_wavelengths)) <= v_c[(src,dst)])


        # if we use more then half of the wavelength on a single fiber, it means that we need to use the L band on it

        for e in self.E:
            self.solver.Add(sum(demand_cel[(src,dst)][e][wav] for wav in range(floor(self.n_wavelengths/2)) for (src,dst) in self.demands) <=(lband_e[e]))


        # We now force the number of amplifier to be more then the total path lengths (divided by the modulation max distances) 

        #for (src,dst) in self.demands:
            
        #    self.solver.Add(sum(demand_cel[(src,dst)][e][wav]*distances[e] for e in self.E for wav in range(self.n_wavelengths))<=self.avalilable_modulations[used_modulation_c[(src,dst)]]['max_distance']*Nb_amplifier)
            
        # We force the cost to be more then the sum of all the lband_e variable

        self.solver.Add(sum(lband_e[e] for e in self.E)<=C)

        self.solver.Minimize(100*C+2*Nb_amplifier+sum(demand_cel[(src,dst)][e][wav] for (src,dst) in self.demands for e in self.E for wav in range(self.n_wavelengths)))
        self.solver.Solve()

        self.used_link = []
        for (src,dst) in self.demands:
            for e in self.E:
                for wav in range(self.n_wavelengths):
                        if(demand_cel[(src,dst)][e][wav].solution_value() != 0):
                            self.used_link.append((e))

        self.amplifier_used = Nb_amplifier.solution_value()
                        
        self.objective_value =  C.solution_value()
        
    

