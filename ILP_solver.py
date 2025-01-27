import networkx as nx
from ortools.linear_solver import pywraplp
from math import floor
import gc

# Create the SCIP solver.

class ILP_solver:


    solver = None
    amplifier_used = 0
    available_modulations = {} #-> should be a dictionary with element (rate,used_channel,max_distance); for now rate and used channel will be set to 1
    used_link = []
    objective_value = None
    solver = None
    graph = None
    demands = None #-> should be in format (src,dst,quantity of traffic)
    quantities = {} #-> should have amount of demands for connection (src,dst) at index (src,dst)
    V = []
    E = []
    n_wavelengths = None
    longest_link = {}

    used_channel_c = {}
    wav_used = {}
    solution_value = 0

    demand_cel = {}
    count_routed_on_c = 0
    count_routed_on_l = 0
    count_routed_on_both = 0

    connection_on_c = []
    connection_on_l = []
    connection_on_cross = []

    status = None





    def __init__(self,graph,demands,n_wavelengths, solver, modulations):


        self.solver = solver
        self.graph = graph
        self.n_wavelengths = n_wavelengths
        self.available_modulations = modulations
        self.V = list(graph.nodes)
        E_u = list(graph.edges())
        self.E = []
        for e in E_u:
            self.E.append(e)
            self.E.append((e[1], e[0]))

        self.used_modulation = {}
        for (src,dst,quantity) in demands:
            self.quantities[(src,dst)] = quantity
        for i in range(len(demands)):
            (src,dst,quantity) = demands[i]
            demands[i] = (src,dst)

        self.demands = demands

        for e in self.E:
            if e not in self.wav_used:
                    self.wav_used[e] = [0]*self.n_wavelengths
        self. connection_on_c = []
        self.connection_on_l = []
        self.connection_on_cross = []

    

    def destroy(self):
        # Cancella gli attributi dell'istanza
        self.__dict__.clear()
        del self
        gc.collect()

        # Forza la garbage collection
        
            



    

    def ILP(self):

            
        
        C = self.solver.IntVar(0,self.solver.infinity(), 'Number_of_Lband_used') # variable that values the total number of links that needs to use C_band
        T = self.solver.IntVar(0,self.solver.infinity(), 'T')
        demand_cel = {} # variable that has value N if connection (src,dst) is routed on link e on wavelength l and occupies N lightpath; 0 otherwise 

        lband_e = {} #variable that has value 1 if more then half the wavelength on link e is used

        used_channel_cnm = {} #number of channel used for n-th connection of c (src,dst) -> this is useless right now

        used_modulation_cm = {} #modulation used for connection c(src,dst) 



        v_c = {}    #number of ligthpath needed for connection between (src,dst) 

        for (src,dst) in self.demands:
            
            v_c[(src,dst)] = self.solver.IntVar(0,self.solver.infinity(), 'nb_of_ligthpath_needed_for_{src}{dst}')
 

        for (src,dst) in self.demands:
            for m in range(len(self.available_modulations)):
                if (src, dst) not in used_modulation_cm:
                    used_modulation_cm[(src, dst)] = {}

                used_modulation_cm[(src,dst)][m] = self.solver.BoolVar('used_modulation')


        x_ce = {}   #variable that has value 1 if link e compose path for n-th connection c between the same pair (src,dst)

        for (src,dst) in self.demands:
            for e in self.E:
                
                if (src, dst) not in x_ce:
                    x_ce[(src, dst)] = {}
            
                x_ce[(src,dst)][e] = self.solver.BoolVar('is_part_of_path{src}{dst}{e}')

        M_c = {}  #trick to find the longest link of a path

        for (src,dst) in self.demands:
            
            M_c[(src,dst)] = self.solver.NumVar(0,self.solver.infinity(), 'M_{src}{dst}')



        distances = nx.get_edge_attributes(self.graph,'length')
        
        for e in self.E:
            if e not in distances:
                distances[(e[0],e[1])] = distances[(e[1],e[0])]


        for e in self.E:
            lband_e[e] = self.solver.IntVar(0,self.solver.infinity(),'demand_{e}')




        for (src,dst) in self.demands:
            for e in self.E:
                for wav in range(self.n_wavelengths):
                
                
                    if (src, dst) not in demand_cel:
                        demand_cel[(src, dst)] = {}
                    if (e[0], e[1]) not in demand_cel[(src, dst)]:
                        demand_cel[(src, dst)][(e[0], e[1])] = {}
                    if (e[1], e[0]) not in demand_cel[(src, dst)]:
                        demand_cel[(src, dst)][(e[1], e[0])] = {}
                    
                    demand_cel[(src,dst)][(e[0],e[1])][wav] = self.solver.IntVar(0,self.solver.infinity(),'demand_{src}{dst}{e}{wav}')
                    demand_cel[(src,dst)][(e[1],e[0])][wav] = self.solver.IntVar(0,self.solver.infinity(),'demand_{src}{dst}{e}{wav}')



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

    #Note -> to allow crossband, this is not required anymore

        #for (src, dst) in self.demands:
            
        #    for v in self.V:

        #        for wav in range(self.n_wavelengths):
            
        #            flow_out = sum(demand_cel[(src,dst)][(v,v_i)][wav] for v_i in self.V  if (v,v_i) in self.E )
        #            flow_in = sum(demand_cel[(src,dst)][(v_j,v)][wav] for v_j in self.V if (v_j,v) in self.E )

        #            if v != src and v != dst:
        #                self.solver.Add((flow_out - flow_in) == 0)

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
                        self.solver.Add(sum(demand_cel[(src,dst)][link1][wav] + demand_cel[(src,dst)][link2][wav] for (src,dst) in self.demands ) <= 1)

        # different demands cannot use the same wavelength on the same link -> same reasoning of before; if we have more then 1 connection from the same source to the same destination, we should be able to use more
        # wavelength (one for each connection of the same pair (src,dst))

        for e in self.E:
            for (src,dst) in self.demands:

                self.solver.Add(sum(demand_cel[(src,dst)][e][wav] for wav in range(self.n_wavelengths)) <= v_c[(src,dst)])


        # if we use more then half of the wavelength on a single fiber, it means that we need to use the L band on it

        for e in self.E:
            self.solver.Add(sum(demand_cel[(src,dst)][e][wav] for wav in range(floor(self.n_wavelengths/2)) for (src,dst) in self.demands) <=(lband_e[e]))


        # We now get the maximum value of M to be equal to the longest link of each connection

        #First thing first, we set the value of x_ce to 1 if the link e is used by src,dst

        for (src,dst) in self.demands:
            for e in self.E:
                self.solver.Add(sum(demand_cel[(src,dst)][e][wav] for wav in range(self.n_wavelengths)) <= 100 * x_ce[(src,dst)][e]) #-> NOW v_c is a variable and not a constant! To overcome, we take out it and put a big number
            

        #Now, we forced the modulation to be the best of the packet for the distance; the number of ligthpath are equal to
        #v_c[(src,dst)] = self.quantities[(src,dst)]/(used_modulation_cm[(src,dst)][m]*self.available_modulation[m]['rate'])

        for (src,dst) in self.demands:
            self.solver.Add(sum(used_modulation_cm[(src,dst)][m]*self.available_modulations[m]['rate'] for m in range(len(self.available_modulations)))*self.quantities[(src,dst)]<=v_c[(src,dst)])

        

        for (src,dst) in self.demands:
            
            
            for e in self.E:
                self.solver.Add(M_c[(src,dst)]>=x_ce[(src,dst)][e]*distances[e] ) #-> Now M is forced to be greater then the longest link
        
        #Choosing modulation -> the max length of single link must be lesser than the max distance of the modulation; then, it's best if it occupies the least amount of channels;
        #then, it's best if it has the higher bit rate


        for (src,dst) in self.demands:
            
            self.solver.Add(sum(used_modulation_cm[(src,dst)][m] for m in range(len(self.available_modulations)))==1)
            self.solver.Add(M_c[(src,dst)]<=sum(used_modulation_cm[(src,dst)][m]*self.available_modulations[m]['max_distance'] for m in range(len(self.available_modulations))))

                
                
        # We force the cost to be more then the sum of all the lband_e variable

        self.solver.Add(sum(lband_e[e] for e in self.E)<=C)

        self.solver.Minimize(10*C+sum(demand_cel[(src,dst)][e][wav] for (src,dst) in self.demands for e in self.E for wav in range(self.n_wavelengths)))
        self.status = self.solver.Solve()

        self.used_link = []
        for (src,dst) in self.demands:
            for e in self.E:
                for wav in range(self.n_wavelengths):
                        if(demand_cel[(src,dst)][e][wav].solution_value() != 0):
                            self.used_link.append((e))

        self.longest_link = {}
        for (src,dst) in self.demands:
            if (src,dst) not in self.longest_link:
                self.longest_link[(src,dst)] = {}
            self.longest_link[(src,dst)] = M_c[(src,dst)].solution_value() #debugging reason


        self.used_modulation = {}
        for (src,dst) in self.demands:
            
            for m in range(len(self.available_modulations)):
                if (src,dst) not in self.used_modulation:
                    self.used_modulation[(src,dst)] = {}
                self.used_modulation[(src,dst)][m] = used_modulation_cm[(src,dst)][m].solution_value()
        
        self.used_channel_c = {}
        for (src,dst) in self.demands:
            
            self.used_channel_c[(src,dst)] = v_c[(src,dst)].solution_value()
        
        self.objective_value =  C.solution_value()


        for (src,dst) in self.demands:
            for e in self.E:
           
                for wav in range(self.n_wavelengths):
                    if (src,dst) not in self.demand_cel:
            
                        self.demand_cel[(src, dst)] = {}
                    
                    if (e[0], e[1]) not in self.demand_cel[(src, dst)]:
                        self.demand_cel[(src, dst)][(e[0], e[1])] = {}
                    if (e[1], e[0]) not in self.demand_cel[(src, dst)]:
                        self.demand_cel[(src, dst)][(e[1], e[0])] = {}
                    
                
                    
                    self.demand_cel[(src,dst)][e][wav] = demand_cel[(src,dst)][e][wav].solution_value()
                            

        flag_route_c = False
        flag_route_l = False

        for (src,dst) in self.demands:
            flag_route_c = False
            flag_route_l = False
            for e in self.E:
                for wav in range(self.n_wavelengths):
                    if self.demand_cel[(src,dst)][e][wav] == 1:
                        if wav >= floor (self.n_wavelengths/2):
                            flag_route_c = True
                        else:
                            flag_route_l = True
            if (flag_route_c):
                if (flag_route_l):
                    self.count_routed_on_both = self.count_routed_on_both +1
                    self.connection_on_cross.append(tuple((src,dst)))
                else:
                    self.count_routed_on_c = self.count_routed_on_c + 1
                    self.connection_on_c.append(tuple((src,dst)))

            else:
                if(flag_route_l):
                    self.count_routed_on_l = self.count_routed_on_l + 1
                    self.connection_on_l.append(tuple((src,dst)))
        
        
    
    

