#IMPORTS
import numpy as np
import matplotlib.pyplot as plt
import zipfile
import pandas as pd
import os
import sys
import gym
import time
import minihack
from minihack import RewardManager
from environment import init_env
from PIL import Image
from datetime import datetime


class NN:
    """
        Nueral Network that is optimised using hueristics
    """

    def __init__(self,shape,create=True):
        """
            Initialises the nueral network
        """
        self.W  = []
        self.shape = shape

        #initialises matrices if create is set to true#
        if create == True: 
            for i in range(1,len(shape),1):
                temp = self.create_weight(shape[i-1],shape[i])
                self.W.append(temp)
    
    def create_weight(self,u,v):
        """
            creates weight matrices including the bias
        """
        if v !=1:
            W = np.random.randn(v,u+1) * np.sqrt(2/(u+v))
        else:
            W = np.random.randn(u+1) * np.sqrt(2/(u+v))
    
        return W
    
    def flatten(self):
        """
            flattens nueral network
        """

        output = []
        shapes = []
        for x in self.W:
            
            if len(x.shape)!=1:
                u,v = x.shape
            else:
                u = 1
                v = len(x)
            
            shapes.append([u,v])

            temp = x.flatten()
            temp = temp.tolist()
            output = output + temp

        return output,shapes
    
    def reconstruct(self,data,shapes):
        """
            Reconstructs Neural network based on
            list of values provided and shapes of 
            weight matrices
        """
        
        #getting rid of all other weights#
        self.W = []
        self.shape = shapes
        
        index = 0

        for u in shapes:
            length = u[0]*u[1]
            x = data[index:index+length].copy()

            W = np.array(x)

            if (u[0]!=1):
                W = W.reshape(u[0],u[1])

            self.W.append(W)
            #updating index#
            index += length

    def save_model(self,filename='output'):
        
        name = filename + '.zip'
        output,shapes = self.flatten()

        #adding shapes to shapes file#
        shapesfile = open('shape.txt','w')

        lines = []

        for u in shapes:
            string = str(u[0])+ ' ' + str(u[1]) + ' \n'
            lines.append(string)

        shapesfile.writelines(lines)
        shapesfile.close()

        #saving weight values#
        #data = np.array(output)
        d = {'values':output}
        data = pd.DataFrame(d)
        data.to_csv('weight.csv')
        #np.savetxt('weight.csv',data,delimiter=",")
        
        #saving model to zip#
        outzip = zipfile.ZipFile(name,'w')
        outzip.write('shape.txt')
        outzip.write('weight.csv')
        os.remove('shape.txt')
        os.remove('weight.csv')
        outzip.close()
    
    def load_model(self,filename='output.zip'):

        with zipfile.ZipFile(filename,'r') as parent_file:
            #getting shape info#
            shapefile = parent_file.open('shape.txt')
            Lines = shapefile.readlines()

            shapes = []

            for line in Lines:
                sent = line.strip()
                data = sent.decode("utf-8")
                x = [int(e) for e in data.split(' ')]
                shapes.append(x)

            #getting weight values#
            W = pd.read_csv( parent_file.open('weight.csv'))
            W = W.to_numpy()[:,1]
            data = W.tolist()

            self.reconstruct(data,shapes)
    
######################################ACTIVATION_FUNCTIONS#################################################
    def sigmoid(self,x):
        
        value = 1/(1+np.exp(-x))
        return value
    
    def relu(self,x):
        value = np.maximum(x, 0)
        return value
    
    def softmax(self,x):
        temp = np.exp(np.abs(x))
        value = temp/np.sum(temp)
        return value

    def activation_function(self,x,func='sigmoid'):
        """
            can choose which activation function to use
            (More to be added)

        """
        if func == 'sigmoid':
            return self.sigmoid(x)
        
        if func== 'relu':
            return self.relu(x)
        
        if func == 'softmax':
            return self.softmax(x)
        
#############################################################################################################
    def feedfoward(self,x0,round=False):

        #reshaping vector#
        x = np.copy(x0)
        x = np.array(x)
        x = x.reshape(len(x),1)

        #normalising vector#
        x = x/np.linalg.norm(x)

        for i in range(len(self.W)):

            #stacking#
            if len(x.shape)>1:
                v = np.ones((1,len(x[0,:])))
            else:
                v = np.ones(1)
            
            x = np.vstack((v,x))

            z = self.W[i] @ x

            #TODO: relu giving issues
            if i != len(self.W)-1:
                a = self.activation_function(z,func='sigmoid')
            else:
                a = self.activation_function(z,func='softmax')

            # a = self.activation_function(z,func='sigmoid')
            x = np.copy(a)

        if round==True:
            x = np.round(x)

        if len(x.shape) == 1 and (len(x)==1):
            return x[0]
        
        return x.flatten() 

   

    def sim_fitness(self):
        """
            one run of the simulation
        """

        env = init_env() 
        observation = env.reset()

        state  = observation["glyphs"] 
        prev_state = np.copy(state)
        
        score = 0

        # print(env.action_space.n)
        done = False
        
        while not done:
            X = np.hstack((state.flatten(),prev_state.flatten()))
            
            #getting policy from network#
            policy = self.feedfoward(X)
            
            #action = np.argmax(policy)
            action = np.random.choice(np.arange(len(policy)),p=policy)
            
            observation,reward,done,_ = env.step(action)

            score+=reward
            prev_state = np.copy(state)
            state  = observation["glyphs"] 
        
        #closing env#
        env.close()
        
        return score

    def fitness(self,x,shapes,rep=3):
        """
            Determines fitness of the weights

            Parameters:
                x      (list)  : possible solution
                shapes (list)  : shape of weight matrices
            
            Outputs:
                score  (float) : fitness of chromosome x
        """

        self.reconstruct(x, shapes)
        score = 0

        for _ in range(0,rep,1):
            value = self.sim_fitness()
            score+=value
        
        score = score/rep
        return score
    
###################################REAL_CODED_GENETIC_ALGORITHM################################################# 
    def init_chromosome(self,a,b):
        """
            Initialises a possible solution randomly

            Parameters:
                a (list) : set of lower boundaries
                b (list) : set of upper boundaries
            
            Output:
                x (list) : possible solution
        """

        x = []
        n = len(a)

        for i in range(0,n,1):
            r = np.random.uniform(0,1)
            value = a[i] + (b[i]-a[i])*r
            x.append(value)
        
        return x
    
    def init_population(self,a,b,N,shapes):
        """
            Initalises the population of solutions

            Parameters:
                a      (list) : set of lower boundaries
                b      (list) : set of upper boundaries
                N      (int)  : size of population
                shapes (list) : shape of weight matrices
            
            Outputs
                pop    (list) : set of possible solutions
                costs  (list) : list of fitness values corresponding to each solution in pop
        """

        pop = []
        costs = []

        for _ in range(0,N,1):
            x = self.init_chromosome(a, b)
            fx = self.fitness(x, shapes)

            pop.append(x)
            costs.append(fx)
        
        return pop,costs
    
    def elitism(self,pop,costs,k):
        """
            returns the top k possible solutions

            Parameters:
                pop    (list) : set of possible solutions
                costs  (list) : list of fitness values corresponding to each solution in pop
                k      (int)  : number of top solutions to be returned

            Outputs:
                x      (list)  : top k chormosomes
                fx     (float) : fitness of values in x
        """

        x = pop.copy()
        fx = costs.copy()

        self.quickSort(x, fx)
        return x[0:k],fx[0:k]
    
    def blend_crossover(self,p1,p2,shapes,alpha=0.5):
        """
            Performs blended crossover to produce possible
            solution for next generation

            Parameters:
                p1     (list)  : first parent
                p2     (list)  : second parent
                shapes (list)  : shape of weight matrices
                alpha  (float) : blended crossover parameter
            
            Outputs:
                x     (list)  : new possible solution
                fx    (float) : fitness of solution
        """
        n = len(p1)

        x = []

        for i in range(0,n,1):
            a = min(p1[i],p2[i])
            b = max(p1[i],p2[i])

            r = np.random.uniform(0,1)
            dist = b-a
            value = a - alpha*dist + (dist + 2*alpha*dist)*r
            x.append(value)
        
        fx = self.fitness(x,shapes)
        return x,fx

    def tournament_selection(self,pop,costs):
        """
            Determines chromosomes to be used for crossover to produce
            better solutions using tournament selection

            Parameters:
                pop    (list) : set of possible solutions
                costs  (list) : list of fitness values corresponding to each solution in pop
            
            Outputs:
                p      (list) : parent to be used in crossover
        """

        i = 0
        j = 0

        while i==j:
            i = np.random.randint(0,len(pop))
            j = np.random.randint(0,len(pop))

        if costs[i] > costs[i]:
            return pop[i]
        else:
            return pop[j]
    

    def mutation(self,x0,mu,a,b,shapes,std=0.1):
        """
            Mutates the network

            Parameters:
                x0    (list)  : weight parameters of network
                a     (float) : lower boundary
                b     (float) : upper boundary
                shape (list)  : shape of network
                std   (float) : standard deviation in normal distribution
        """

        x = []
        change = False

        for i in range(0,len(x0),1):
            r = np.random.uniform(0,1)

            if r <= mu:
                change = True
                temp = x0[i] + np.random.normal(0,std)

                if not(a[i] <= temp <= b[i]):
                    alpha = np.random.uniform(0,1)
                    temp = a[i] + alpha*(b[i]-a[i])
            else:
                temp = x0[i]
            
            x.append(temp)
        
        fx = None
        if change == True:
            fx = self.fitness(x, shapes)
        
        return x,fx,change


    def GA(self,a,b,shapes,N,k,m,mu,get_iter=False,learn_curve=False,save=10):
        """
            Optimises the Neural Network using 
            Genetic Alogrithm

            Parameters:
                a      (list)  : set of lower boundaries
                b      (list)  : set of upper boundaries
                shapes (list)  : shape of weight matrices
                N      (int)   : population size
                k      (int)   : number of elite solutions
                m      (int)   : number of generations
                mu     (int)   : probability of mutation
            
            Outputs:
                x      (list)  : best weights found
                fx     (float) : fitness of solution x
        """

        #number of new solutions to be created#
        n_children = N-k

        pop,costs = self.init_population(a, b, N, shapes)
        best = [np.max(costs)]
        mean = [np.mean(costs)]

        for count in range(0,m,1):
            x,fx = self.elitism(pop, costs, k)

            #creating children#
            for _ in range(0,n_children,1):
                p1 = self.tournament_selection(pop, costs)
                p2 = self.tournament_selection(pop, costs)
                child,child_cost = self.blend_crossover(p1, p2, shapes)

                #appending to list#
                x.append(child)
                fx.append(child_cost)
            
            #Mutation#
            for i in range(0,len(x),1):

                if mu == 0:
                    break
                
                y,fy,change = self.mutation(x[i], mu, a, b, shapes)

                if change == True:
                    x[i] = y.copy()
                    fx[i] = fy
            
            print("Gen {} fitness: {}".format(count,np.max(fx)))
            #updating generation#
            pop = x.copy()
            costs = fx.copy()
            best.append(np.max(costs))
            mean.append(np.mean(costs))


            #saving models#
            if count % save == 0:
                index = np.argmax(costs)

                self.reconstruct(pop[index], shapes)
                self.save_model(filename='GA_{}'.format(count))
            
            if get_iter==True and np.max(costs) == 500:
                return None, count+1


        if get_iter == True:
            return None,m
        
        if learn_curve == True:
            return best,mean
        
        index = np.argmax(costs)
        return pop[index],costs[index]

    
################################ Particle Swarm Optimisation ###########################
    def init_agent(self,a,b):
        """
            Using real coded genetic algorithm, generates values between
            a_i and b_i

            Parameters:
                a (list) : lower boundaries of each axis
                b (list) : upper boundaries of each axis
            
            Outputs:
                x (list) : possible solution
        """

        n = len(a)
        
        x = []

        for i in range(0,n,1):
            r = np.random.uniform(0,1)

            #adding 1 to make it inclusive#
            value = a[i] + (b[i]-a[i])*r
        
            x.append(value)

        return x
    
    
    def PSO_init_population(self,a,b,N,shape):
        """
            Initialises the population of solutions

            Parameters:
                a            (list) : lower boundaries
                b            (list) : upper boundaries
                N            (int)  : population size
            
            Outputs:
                pop         (list)  : population of possible solutions
                local_best  (list)  : list of personal best solutions
                local_cost  (list)  : list of fitness values corresponding to local best
                global_best (list)  : current global best solution
                global_cost (float) : fitness of global best solution
                costs       (list)  : fitness values of each solution in population
        """

        #current location of agents#
        pop = []
        costs = []

        #personal best locations#
        local_best = []
        local_cost = []

        #global best position
        global_best = None
        global_cost = None

        for _ in range(0,N,1):
            x = self.init_agent(a,b)
            fx = self.fitness(x,shape)

            #adding to population#
            pop.append(x)
            costs.append(fx)

            #adding to local best#
            local_best.append(x)
            local_cost.append(fx)

            if global_best == None:
                global_best = x.copy()
                global_cost = fx
            elif fx > global_cost:
                global_best = x.copy()
                global_cost = fx
        
        return pop,costs,local_best,local_cost,global_best,global_cost

    def direction_vector(self,p_best,g_best,pos,c1,c2):
        """
            Computes the direction vector using line search

            Parameters:
                c1      (float) : parameter on first vector
                c2      (float) : parameter on second vector
                p_best  (list)  : personal best location
                g_best  (list)  : global best location
                pos     (list)  : current position
            
            Output
                d       (list)  : direction vector
        """

        #copying values#
        p = np.array(p_best.copy())
        g = np.array(g_best.copy())
        x = np.array(pos.copy())

        #random values#
        r1 = np.random.uniform(0,1)
        r2 = np.random.uniform(0,1)

        u = c1 * r1 * (p-x) 
        v = c2 * r2 * (g-x)

        d = u + v
        return d

    def update_pos(self,p_best,g_best,pos,shape,c1,c2,a,b):
        """
            determines next position using direction vector

            Parameters:
                c1      (float) : parameter on first vector
                c2      (float) : parameter on second vector
                p_best  (list)  : personal best location
                g_best  (list)  : global best location
                pos     (list)  : current position
                a       (list)  : lower boundaries
                b       (list)  : upper boundaries
            
            Output
                x       (list)  : updated position
        """
        x = np.copy(pos.copy())

        #update this for conjugate gradient#
        d = self.direction_vector(p_best,g_best,pos,c1=c1,c2=c2)

        xnew = x + d
        xnew = xnew.tolist()

        #making sure doesnt leave boundaries#
        for i in range(0,len(xnew),1):

            if (xnew[i] < a[i]) or (xnew[i]>b[i]):
                r = np.random.uniform(0,1)
                xnew[i] = a[i] + (b[i]-a[i])*r


        fx = self.fitness(xnew,shape)
        return xnew,fx

    def PSO(self,a,b,M,N,shape,c1=2,c2=2,get_iter=False,learn_curve = False,save=10):
        """
            Optimises function using Particle Swarm Optimisation

            Parameters:
                a      (list) : lower boundaries
                b      (list) : upper boundaries
                M      (int)  : population size
                N      (int)  : number of iterations
                shapes (list) : shapes of weight matrices
        """

        #initalising population#
        iteration = None
        pop,costs,local_best,local_cost,global_best,global_cost = self.PSO_init_population(a, b, M,shape)
        best = [global_cost]
        mean = [np.mean(costs)]

        for count in range(0,N,1):
            
            #updating agents#
            for i in range(0,M,1):

                #new position#
                x,fx = self.update_pos(local_best[i],global_best,pop[i],shape,c1, c2,a,b)

                pop[i] = x.copy()
                costs[i] = fx

                #updating personal best#
                if fx > local_cost[i]:
                    local_best[i] = x.copy()
                    local_cost[i] = fx
                
                #updating global best#
                if fx > global_cost:
                    global_best = x.copy()
                    global_cost = fx
            
            print("Gen {} fitness: {}".format(count,global_cost))

            best.append(global_cost)
            mean.append(np.mean(costs))

            if (get_iter == True) and (global_cost == 500):
                return None,count+1
            
            #saving models#
            if count % save == 0:
                index = np.argmax(costs)

                self.reconstruct(pop[index], shape)
                self.save_model(filename='PSO_{}'.format(count))
        
        if get_iter == True:
            return None,N

        if learn_curve == True:
            return best,mean
        
        return global_best,global_cost
        

#################################QUICKSORT#############################################
    def partition(self,x,fx,left:int,right:int):

        pivot = fx[right]
        i = left - 1

        for j in range(left,right,1):
        
            if fx[j] >= pivot:
                i+=1

                temp_x = x[i].copy()
                temp_f = fx[i]

                x[i] = x[j].copy()
                fx[i] = fx[j]

                x[j] = temp_x.copy()
                fx[j] = temp_f 
        
        temp_x = x[i+1].copy()
        temp_f = fx[i+1]

        x[i+1] = x[right].copy()
        fx[i+1] = fx[right]

        x[right] = temp_x.copy()
        fx[right] = temp_f

        return i+1
    
    def q_sort(self,x,fx,left:int,right:int):

        if left < right:
            part_index = self.partition(x, fx, left, right)
            self.q_sort(x, fx, left, part_index-1)
            self.q_sort(x, fx, part_index+1, right)
    
    def quickSort(self,x,fx):
        n = len(x)
        self.q_sort(x, fx,0,n-1)
######################################################################################## 
#####################################Optimiser ########################################## 
    def optimise(self,N=20,k=20,m=100,mu=0,opti="GA",get_iter=False,learn_curve=False):
        """
            Optimises the Neural Network using 
            Genetic Alogrithm

            Parameters:
                N   (int) : population size
                k   (int) : number of elite solutions
                m   (int) : number of generations
                mu  (int) : probability of mutation
        """
        
        a = [] #lower boundaries#
        b = [] #upper boundaries#
        shapes = []

        #getting info#
        for w in self.W:
            
            if len(w.shape)!=1:
                u,v = w.shape
            else:
                u = 1
                v = len(w)

            shapes.append([u,v])

            boundary = np.sqrt(2/(u+v))
            
            for _ in range(0,u*v,1):
                a.append(-boundary)
                b.append(boundary)
        

        if opti == "GA":
            weights,cost = self.GA(a, b, shapes,N,k,m,mu,get_iter=get_iter,learn_curve=learn_curve)
        elif opti == "PSO":
            weights,cost = self.PSO(a, b, N,m, shapes,get_iter=get_iter,learn_curve=learn_curve)
        
        #for analysis#
        if learn_curve == True:
            return weights,cost
        elif get_iter == True:
            return cost
        
        print(cost)
        self.reconstruct(weights, shapes)
        self.save_model()
##########################################################################################################################################

#############################################VIDEO GENERATION#############################################################################
def save_gif(gif,path):
    '''
    Args:
        gif: a list of image objects
        path: the path to save the gif to
    '''
    path=path+'.gif'
    gif[0].save(path, save_all=True,optimize=False, append_images=gif[1:], loop=0)
    print("Saved Video")

def frames_to_gif(frames):
    gif = []
    for image in frames:
        gif.append(Image.fromarray(image, "RGB"))
    return gif


def generate_video(model,title=None,path='../videos/'):
    frames = []
    env = init_env(pixel=True,custom_reward=True)
    done = False
    obs = env.reset()

    state  = obs["glyphs"] 
    prev_state = np.copy(state)

    while not done:
        del obs['pixel']

        X = np.hstack((state.flatten(),prev_state.flatten()))
            
        #getting policy from network#
        policy = model.feedfoward(X)
    
        #action = np.argmax(policy)
        action = np.random.choice(np.arange(len(policy)),p=policy)
        obs, reward, done, info = env.step(action)
        frames.append(obs["pixel"])

        prev_state = np.copy(state)
        state  = obs["glyphs"] 
        

    if title is None:
        title = datetime.now().strftime("%d-%m-%Y_%H:%M:%S") 

    gif = frames_to_gif(frames)
    save_gif(gif,path+title)


########################################################################################################################################
def get_plot(rep=10):
	models = ["NE_models/GA_0.zip","NE_models/GA_10.zip","NE_models/GA_20.zip","NE_models/GA_30.zip","NE_models/GA_40.zip","NE_models/GA_50.zip","NE_models/GA_60.zip","NE_models/GA_70.zip","NE_models/GA_80.zip","NE_models/GA_90.zip","NE_models/output.zip"]

	X = []

	for _ in range(rep):
		fitness_values = []

		for model_path in models:
			model = NN(shape=[2,1,1])
			model.load_model(model_path)
			x,shapes = model.flatten()
			value = model.fitness(x=x, shapes=shapes)
			fitness_values.append(value)
		
		X.append(fitness_values)

	X = np.array(X)
	data = []
	for i in range(0,len(models),1):
		value = X[:,i].mean()
		data.append(value)
	
	np.savetxt("GA_data.csv",X,delimiter=",")
			
	plt.plot(fitness_values)
	plt.title('Learning Rate',fontsize=15)
	plt.ylabel('Average reward',fontsize=15)
	plt.xlabel('Generations (intervals of 10 generations)',fontsize=15)
	plt.savefig('GA.png')

if __name__ == "__main__":
    
    #training#
    # print("Traaining begins")
    # model = NN(shape=[3318,1500,500,14])
    # model.optimise(opti="PSO")

    #GETTING PERFORMANCE DATA#
    get_plot()

    #GENERATING VIDEO#
    #model = NN(shape=[1,1])
    #model.load_model(filename="NE_models/output.zip")

    #for i in range(100):
    	#generate_video(model)
    

