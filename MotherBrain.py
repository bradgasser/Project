import win32pipe, win32file, time, operator
import UtilityFunctions as uf
import pybrain
import numpy as np
import matplotlib.pyplot as pyp
import time
import pickle
import brainModules as bm

print "Starting Mommy Brain Simulation"

## Set global variables for initialization and checking
GESTURE_THRESHOLD = 10 # SAME VALUR FOR BABY
REACH_THRESHOLD = 8 # SAME VALUE FOR BABY
paramTimer1 = 25 # SAME VALUE FOR BABY; thresholds timer1; used to transition between states reset_arm and end
paramTimer2 = 12 # SAME VALUE FOR BABY; thresholds timer2; used as blank time before new scene file load in animation script
paramContactThreshold = 0.4 # SAME VALUE FOR BABY; if his wrist is within 0.4 units of motherWrist, its 'contact' / 'pull'
paramEpNum = 10 # SAME VALUE FOR MOTHER; runs 10 episodes
#
paramIntThreshold = 12 # signals at what point RNN-integrator reaches threshold; an 'rnn-mediated response'
paramIntIncPull = 0.2 # haptic input; inc of increase in intActivity during pulling; note 'during watching' is computed directly from RNN
paramIKReach1 = 10 # divider before sending motor commands to IK solver; exponential, will want to change...
paramIKReach2 = 5 # results in quicker than above, for 'mid-pull recognition response' in mother; stylistic only
paramIKWalk = 13 # divider before sending motor commands to IK solver; exponential, will want to change...
paramMotherStandDist = 4 # Mother will walk to a point 4 units in front of center of babys head
# ALSO:
# motherRNNFlag -- involved in initializing mother RNN; all a bit touchy here -- need to turn on the RNN at the right time-step
# timer1
# timer2

p = win32pipe.CreateNamedPipe( r'\\.\pipe\MommyBrainPipe',
	win32pipe.PIPE_ACCESS_DUPLEX,
	win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_WAIT,
	1, 65536, 65536, 30000000, None )

win32pipe.ConnectNamedPipe(p, None)
simulationTime = 0
numEpisodes = 0
#
fileObj = open('netFile.txt','r')
net = pickle.load(fileObj)
print "Network Loaded"
motherWeights = np.array([1,1,1])

while(numEpisodes < paramEpNum):
    motherFile = open('motherTrajectory_Episode' + str(numEpisodes) + '.txt', 'w')
    numEpisodes = numEpisodes + 1
    motherEpisodeStatus = 'TO_START'
    runEpisode = 1
    episodeTime = 0
    timer1 = 0
    timer2 = 0
    ##########
    # mother specific
    motherRNNFlag = 1
    motherIntFlag = 0
    rnnActivity = np.array([0,0,0])
    rnnActivityAUX = np.array([0,0,0])
    correction = np.array([0,0,0])
    net.reset()
    intActivity = np.array([0,0,0])
    prevHead = [0,0,0]
    while(runEpisode == 1):
        ## Reset / Update
        episodeTime = episodeTime + 1
        simulationTime = simulationTime + 1
        motherWrist = []
        motherShoulder = []
        motherElbow = []
        motherHead = []
        babyWrist = []
        babyShoulder = []
        babyElbow = []
        babyHead = []
        ## Receive / Parse message
        animMessage = win32file.ReadFile(p, 4096)[1]
        uf.parseMessage(animMessage, motherWrist, motherShoulder, motherElbow, motherHead, babyWrist, babyShoulder, babyElbow, babyHead)
        uf.writeReceivedCoordinatesToFile(motherFile, motherWrist, motherShoulder, motherElbow, motherHead, babyWrist, babyShoulder, babyElbow, babyHead, simulationTime)

        if(motherEpisodeStatus == 'TO_START'):
            messageToSend = 'INIT '
            motherEpisodeStatus = 'INITIALIZED'
            print "Mother TO_START"
        elif(motherEpisodeStatus == 'INITIALIZED'):
            messageToSend = 'DO_NOTHING'
            motherEpisodeStatus = 'WATCHING'
            babyReachTarget = motherWrist
            print "Mother INITIALIZED"
        elif(motherEpisodeStatus == 'WATCHING'):
            diffHead = map(operator.sub, babyHead, prevHead)
            if(diffHead[0] != 0 or diffHead[1] != 0 or diffHead[2] != 0):
                prevHead = babyHead
            elif(motherHead[0] - babyHead[0] <= GESTURE_THRESHOLD):
                if(motherRNNFlag == 1):
                    motherRNNFlag = 0
                    correction = np.array([0,0,0]) - babyWrist
                    baWristInit = np.array([babyWrist[0],babyWrist[1],babyWrist[2]])
                else:
                    #
                    # can the below all be bundled off to some function? we will want to expand this in the future...
                    #
                    filteredInput = uf.rnnFilter(babyWrist,correction)
                    rnnActivity = net.activate(filteredInput)
                    tanhRNN = np.tanh(rnnActivity)
                    rnnActivityAUX = np.row_stack((rnnActivityAUX,tanhRNN))
                    rawIntInput = tanhRNN * motherWeights
                    compInput = uf.compInt(rawIntInput)
                    intActivity = compInput + intActivity # intActivity always limited by 'speed' of IK: move too 'fast', not enough time to integrate
                    #pyp.plot(rnnActivityAUX)
                    #pyp.show()
            # To tell mother when to respond
            if(intActivity[0] < paramIntThreshold) and (babyReachTarget[0] - babyWrist[0] > paramContactThreshold):
                messageToSend = 'DO_NOTHING'
            else:
                messageToSend = 'DO_NOTHING'
                motherEpisodeStatus = 'RESPOND'
                baShoulderInit = np.array([babyShoulder[0],babyShoulder[1],babyShoulder[2]])
        elif(motherEpisodeStatus == 'RESPOND'):
            timer1 = timer1 + 1
            print "MOTHER RESPOND"
            if(timer1 < paramTimer1):
                motherWalkResponse = np.array((babyHead[0] + paramMotherStandDist) - motherHead[0])
                # intActivity should still play a role here...
                #
                # can the below (or all of 'RESPOND'?) be sent off to some function?
                #
                if(numEpisodes == 1):
                    motherPullResponse = np.array(baWristInit - motherWrist)
                    messageToSend = 'RESPOND' + ' ' + str(motherWalkResponse /paramIKWalk) + ' ' + str(0) + ' ' + str(0) + ' ' + str(simulationTime) + ' ' + str(motherPullResponse[0] /paramIKReach1) + ' ' + str(motherPullResponse[1] /paramIKReach1) + ' ' + str(motherPullResponse[2] /paramIKReach1)
                elif(intActivity[0] >= paramIntThreshold):
                    motherRecResponse = np.array(baShoulderInit - motherWrist)
                    messageToSend = 'RESPOND' + ' ' + str(motherWalkResponse /paramIKWalk) + ' ' + str(0) + ' ' + str(0) + ' ' + str(simulationTime) + ' ' + str(motherRecResponse[0] /paramIKReach2) + ' ' + str(motherRecResponse[1] /paramIKReach2) + ' ' + str(motherRecResponse[2] /paramIKReach2)
                else:
                    motherPullResponse = np.array(baWristInit - motherWrist)
                    messageToSend = 'RESPOND' + ' ' + str(motherWalkResponse /paramIKWalk) + ' ' + str(0) + ' ' + str(0) + ' ' + str(simulationTime) + ' ' + str(motherPullResponse[0] /paramIKReach1) + ' ' + str(motherPullResponse[1] /paramIKReach1) + ' ' + str(motherPullResponse[2] /paramIKReach1)
                    intActivity[0] = intActivity[0] + paramIntIncPull
            else:
                messageToSend = 'DO_NOTHING'
                motherEpisodeStatus = 'END'
        elif(motherEpisodeStatus == 'END'):
            print "MOTHER END"
            messageToSend = 'DO_NOTHING'
            timer2 = timer2 +1
            if(timer2 > paramTimer2):
                runEpisode = 0
                motherFile.close()
        win32file.WriteFile(p, bytearray(messageToSend, 'utf-8'))
    if(numEpisodes < paramEpNum):
            #pyp.plot(rnnActivityAUX)
            #pyp.show()
            #pyp.plot(intActivity)
            #pyp.show()
            motherWeights = uf.motherLearnWeights(motherWeights) # should be involved in intActivity 'growth' over time

## End program / pipes
animMessage = win32file.ReadFile(p, 4096)[1]
win32file.WriteFile(p, bytearray('STOP', 'utf-8'))
#pyp.plot(rnnActivityAUX)
#pyp.show()
print("Last message received")
win32file.CloseHandle(p)
