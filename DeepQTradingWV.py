from SpEnv import SpEnv
from Callback import ValidationCallback
from keras.models import Sequential
from keras.layers import Dense, Activation, Flatten
from keras.layers.advanced_activations import LeakyReLU, PReLU
from keras.optimizers import Adam
from rl.agents.dqn import DQNAgent
from rl.memory import SequentialMemory
from rl.policy import EpsGreedyQPolicy
from math import floor
import pandas as pd
import datetime
import telegram


class DeepQTrading:
    def __init__(self, model, explorations, trainSize, validationSize, testSize, outputFile, begin, end, nbActions, nOutput=1, operationCost=0):
        self.bot = telegram.Bot(token='864997856:AAFjYS9qw9Gd3L_AwYGBPdhE7w-SWxf-JjU')

        self.policy = EpsGreedyQPolicy()
        self.explorations=explorations
        self.nbActions=nbActions
        self.model=model
        """self.memory = SequentialMemory(limit=10000, window_length=50)
        self.agent = DQNAgent(model=self.model, policy=self.policy,  nb_actions=self.nbActions, memory=self.memory, nb_steps_warmup=400, 
                            target_model_update=1e-1, enable_double_dqn=False, enable_dueling_network=False)
        self.agent.compile(Adam(lr=1e-3), metrics=['mae'])
        self.agent.save_weights("q.weights", overwrite=True)"""
        self.currentStartingPoint = begin
        self.trainSize=trainSize
        self.validationSize=validationSize
        self.testSize=testSize
        self.walkSize=trainSize+validationSize+testSize
        self.endingPoint=end
        self.sp = pd.read_csv('./dataset/sp500Hour.csv')
        self.sp['Datetime'] = pd.to_datetime(self.sp['Date'] + ' ' + self.sp['Time'])
        self.sp = self.sp.set_index('Datetime')
        self.sp = self.sp.drop(['Date','Time'], axis=1)
        self.sp = self.sp.index
        self.operationCost = operationCost
        self.trainer=ValidationCallback()
        self.validator=ValidationCallback()
        self.tester=ValidationCallback()
        self.outputFile=[]

        for i in range(0,nOutput):
            self.outputFile.append(open(outputFile+str(i+1)+".csv", "w+"))
            self.outputFile[i].write(
            "Iteration,"+
            "trainAccuracy,"+
            "trainCoverage,"+
            "trainReward,"+
            "trainLong%,"+
            "trainShort%,"+
            "trainLongAcc,"+
            "trainShortAcc,"+
            "trainLongPrec,"+
            "trainShortPrec,"+

            "validationAccuracy,"+
            "validationCoverage,"+
            "validationReward,"+
            "validationLong%,"+
            "validationShort%,"+
            "validationLongAcc,"+
            "validationShortAcc,"+
            "validLongPrec,"+
            "validShortPrec,"+
            
            "testAccuracy,"+
            "testCoverage,"+
            "testReward,"+
            "testLong%,"+
            "testShort%,"+
            "testLongAcc,"+
            "testShortAcc,"+
            "testLongPrec,"+
            "testShortPrec\n")
        

    def run(self):
        trainEnv=validEnv=testEnv=" "

        iteration=-1

        while(self.currentStartingPoint+self.walkSize <= self.endingPoint):
            iteration+=1
            self.bot.send_message(chat_id='@DeepQTrading', text="Iterazione "+str(iteration)+" iniziata.")
            
            """
            del(self.memory)
            del(self.agent)
            """
            self.memory = SequentialMemory(limit=180, window_length=10)
            self.agent = DQNAgent(model=self.model, policy=self.policy,  nb_actions=self.nbActions, memory=self.memory, nb_steps_warmup=200, target_model_update=1000,
                                    enable_double_dqn=True,enable_dueling_network=True)
            self.agent.compile(Adam(lr=1e-3), metrics=['mae'])
            #self.agent.load_weights("q.weights")

            trainMinLimit=None

            while(trainMinLimit is None):
                try:
                    trainMinLimit = self.sp.get_loc(self.currentStartingPoint)
                except:
                    self.currentStartingPoint+=datetime.timedelta(0,0,0,0,0,1,0)
            trainMaxLimit=None

            while(trainMaxLimit is None):
                try:
                    trainMaxLimit = self.sp.get_loc(self.currentStartingPoint+self.trainSize)
                except:
                    self.currentStartingPoint+=datetime.timedelta(0,0,0,0,0,1,0)

            validMinLimit=trainMaxLimit


            validMaxLimit=None
            while(validMaxLimit is None):
                try:
                    validMaxLimit = self.sp.get_loc(self.currentStartingPoint+self.trainSize+self.validationSize)
                except:
                    self.currentStartingPoint+=datetime.timedelta(0,0,0,0,0,1,0)


            testMinLimit=validMaxLimit


            testMaxLimit=None
            while(testMaxLimit is None):
                try:
                    testMaxLimit = self.sp.get_loc(self.currentStartingPoint+self.trainSize+self.validationSize+self.testSize)
                except:
                    self.currentStartingPoint+=datetime.timedelta(0,0,0,0,0,1,0)


            date=self.currentStartingPoint
            for eps in self.explorations:
                self.policy.eps = eps[0]
                del(trainEnv)
                trainEnv = SpEnv(operationCost=self.operationCost,minLimit=trainMinLimit,maxLimit=trainMaxLimit,callback=self.trainer)
                del(validEnv)
                validEnv=SpEnv(operationCost=self.operationCost,minLimit=validMinLimit,maxLimit=validMaxLimit,callback=self.validator)
                del(testEnv)
                testEnv=SpEnv(operationCost=self.operationCost,minLimit=testMinLimit,maxLimit=testMaxLimit,callback=self.tester)

                for i in range(0,eps[1]):
                    self.trainer.reset()
                    self.validator.reset()
                    self.tester.reset()

                    trainEnv.resetEnv()
                    self.agent.fit(trainEnv,nb_steps=floor(self.trainSize.days-self.trainSize.days*0.2),visualize=False,verbose=0)
                    (_,trainCoverage,trainAccuracy,trainReward,trainLongPerc,trainShortPerc,trainLongAcc,trainShortAcc,trainLongPrec,trainShortPrec)=self.trainer.getInfo()
                    print(str(i) + " TRAIN:  acc: " + str(trainAccuracy)+ " cov: " + str(trainCoverage)+ " rew: " + str(trainReward))

                    validEnv.resetEnv()
                    self.agent.test(validEnv,nb_episodes=floor(self.validationSize.days-self.validationSize.days*0.2),visualize=False,verbose=0)
                    (_,validCoverage,validAccuracy,validReward,validLongPerc,validShortPerc,validLongAcc,validShortAcc,validLongPrec,validShortPrec)=self.validator.getInfo()
                    print(str(i) + " VALID:  acc: " + str(validAccuracy)+ " cov: " + str(validCoverage)+ " rew: " + str(validReward))

                    testEnv.resetEnv()
                    self.agent.test(testEnv,nb_episodes=floor(self.validationSize.days-self.validationSize.days*0.2),visualize=False,verbose=0)
                    (_,testCoverage,testAccuracy,testReward,testLongPerc,testShortPerc,testLongAcc,testShortAcc,testLongPrec,testShortPrec)=self.tester.getInfo()
                    print(str(i) + " TEST:  acc: " + str(testAccuracy)+ " cov: " + str(testCoverage)+ " rew: " + str(testReward))

                    print(" ")

                    self.outputFile[iteration].write(
                        str(i)+","+
                        str(trainAccuracy)+","+
                        str(trainCoverage)+","+
                        str(trainReward)+","+
                        str(trainLongPerc)+","+
                        str(trainShortPerc)+","+
                        str(trainLongAcc)+","+
                        str(trainShortAcc)+","+
                        str(trainLongPrec)+","+
                        str(trainShortPrec)+","+
                        
                        str(validAccuracy)+","+
                        str(validCoverage)+","+
                        str(validReward)+","+
                        str(validLongPerc)+","+
                        str(validShortPerc)+","+
                        str(validLongAcc)+","+
                        str(validShortAcc)+","+
                        str(validLongPrec)+","+
                        str(validShortPrec)+","+
                        
                        str(testAccuracy)+","+
                        str(testCoverage)+","+
                        str(testReward)+","+
                        str(testLongPerc)+","+
                        str(testShortPerc)+","+
                        str(testLongAcc)+","+
                        str(testShortAcc)+","+
                        str(testLongPrec)+","+
                        str(testShortPrec)+"\n")

            self.currentStartingPoint+=self.testSize

    def end(self):
        import os 
        for outputFile in self.outputFile:
            outputFile.close() 
        os.remove("q.weights")

