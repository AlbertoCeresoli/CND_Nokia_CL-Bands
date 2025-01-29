# Regenerator numbers
import math


#Idea: we start from the path as single links and evaluate the fastest available modulation for this configuration; we then 
#evaluate the cost in terms of number of lightpaths + number of rigenerators used. The we repeated the evaluation, merging
#the two shortest adiacent link in the path till get a single long link as path. If at any point we get a better value of cost,
#we change the modulation used. To keep the evaluation dynamic, we put an increasing weigth on the bandwidth if the recource is scarce;
#The best modulation and wavelength necessary are returned.

#TODO -> the index of the nodes in which is neccessary to put the rigenerator; the lambda actually used and not only the number,
#the function in the cross-bandwidth rigenerator is still to be implemented correctly

def Choosing_modulation(G,path, rate, modTable, available_waves, total_waves):
    link_lens = []
    bestMod = None
    bestModWaves = math.inf
    bestCost = math.inf
    for i in range(len(path) - 1):
        if "length" in G[path[i]][path[i + 1]]:
            link_lens.append(G[path[i]][path[i + 1]]["length"])

        flag = True    

    while flag:   
        

        possible_mods = []
        longest_link = max(link_lens)
        for mod in modTable:
            if longest_link <= mod["Reach (km)"]:
                possible_mods.append(mod)
        for mod in possible_mods:
            modNeededWaves = (math.ceil(rate / mod["Data Rate (Gb/s)"])) * (mod["Channel spacing (Δf) (GHz)"] / 50)
            modNeededReg = len(link_lens) - 1
            cost = modNeededWaves * (total_waves/available_waves) + 3*modNeededReg
            if (cost < bestCost or bestMod == None):
                if(modNeededWaves<available_waves):
                    bestMod = mod
                    bestCost = cost
                    print("Sto modificando il ciclo")
                    print(modNeededWaves)
                    print(modNeededReg)
                    print(bestMod)
                    bestModWaves = modNeededWaves
                    bestModWaves = int(bestModWaves)
        if(len(link_lens)>1):
            # Min adjacent sum
            min_linklens = math.inf
            index = 0
            for i in range(len(link_lens)-1):
                if min_linklens > link_lens[i] + link_lens[i+1]:
                    min_linklens = link_lens[i] + link_lens[i+1]
                    index = i 
            # Modify the list
            link_lens.pop(index+1)
            link_lens.pop(index)
            link_lens.insert(index,min_linklens)
        else:
            flag = False

    return (bestMod,bestModWaves)