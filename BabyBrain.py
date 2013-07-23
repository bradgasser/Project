import win32pipe, win32file, time, operator
import UtilityFunctions as uf
import pybrain
import numpy as np
import matplotlib.pyplot as pyp
import time
import pickle
import brainModules as bm

print "Starting Baby Brain Simulation"

## Set global parameters
GESTURE_THRESHOLD = 10 # SAME VALUR FOR MOTHER
REACH_THRESHOLD = 8 # SAME VALUE FOR MOTHER
paramTimer1 = 25 # SAME VALUE FOR MOTHER; thresholds timer1; used to transition between states reset_arm and end
paramTimer2 = 12 # SAME VALUE FOR MOTHER; thresholds timer2; used as blank time before new scene file load in animation script
paramContactThreshold = 0.4 # SAME VALUE FOR MOTHER; if his wrist is within 0.4 units of motherWrist, its 'contact' / 'pull'
paramEpNum = 10 # SAME VALUE FOR MOTHER; runs 10 episodes
#
paramBabyWalkInc = 0.2 # he walks linearly for now, can be updated; he moves this many units in x-plane every ts
paramBabyRecThreshold = 0.1 # babys threshold for recognizing mother response; she moves >0.1, he 'knows'
paramBabyIKReach = 10 # divider before sending motor commands to IK solver; exponential, will want to change...
paramBabyIKPull = 10 # for now, separate than above, only for flexibility if need be
paramRWInc = 1 # learning increment
paramBabyGestThreshold = 0.8 # when he can 'gesture' in future episodes
# ALSO:
# gestureFlag -- right now, a bool that says whether or not gesture is 'known'; see paramBabyGestThreshold
# babyRecFlag -- bool that says whether baby 'recognizes' mother response; see paramBabyRecThreshold
# timer1
# timer2

p = win32pipe.CreateNamedPipe( r'\\.\pipe\BabyBrainPipe',
	win32pipe.PIPE_ACCESS_DUPLEX,
	win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_WAIT,
	1, 65536, 65536, 30000000, None )

win32pipe.ConnectNamedPipe(p, None)
simulationTime = 0
numEpisodes = 0
#
babyReachWeight = np.array([0.5,0.5])
babyShoulderBias = np.array([0,0,0])
babyVirtualTarget = np.array([0,0,0])
targetCoords1 = np.array([0,0,0])
targetCoords2 = np.array([0,0,0])
gestureFlag = False
#

while(numEpisodes < paramEpNum):
    babyFile = open('babyTrajectory_Episode' + str(numEpisodes) + '.txt', 'w')
    numEpisodes = numEpisodes + 1
    babyEpisodeStatus = 'TO_START'
    runEpisode = 1
    episodeTime = 0
    timer1 = 0
    timer2 = 0
    ##########
    # baby specific
    babyRecFlag = True
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
        uf.writeReceivedCoordinatesToFile(babyFile, motherWrist, motherShoulder, motherElbow, motherHead, babyWrist, babyShoulder, babyElbow, babyHead, simulationTime)

        ## Manages decisions
        if(babyEpisodeStatus == 'TO_START'):
            messageToSend = 'INIT '
            babyEpisodeStatus = 'INITIALIZED'
            print "BABY TO_START"
        elif(babyEpisodeStatus == 'INITIALIZED'):
            print "BABY INITIALIZED"
            #makes so baby always must walk at least a little
            if(motherHead[0] - babyHead[0] > GESTURE_THRESHOLD):
                babyEpisodeStatus = 'WALK'
                messageToSend = 'DO_NOTHING'
                moWristInit = np.array([motherWrist[0],motherWrist[1],motherWrist[2]])
        elif(babyEpisodeStatus == 'WALK'):
            print "BABY WALK"
            # indicates max distance can reach from
            if(gestureFlag == True):
                #can gesture, so impose gesture_threshold, not reach_threshold
                if(motherHead[0] - babyHead[0] > GESTURE_THRESHOLD):
                    messageToSend = 'WALK ' + str(babyHead[0] + paramBabyWalkInc) + ' ' + str(babyHead[1]) + ' ' + str(babyHead[2]) + ' ' + str(simulationTime)
                else:
                    messageToSend = 'DO_NOTHING'
                    babyEpisodeStatus = 'REACH'
                    babyReachTarget = motherWrist
                    baWristInit = np.array([babyWrist[0],babyWrist[1],babyWrist[2]])
            elif(motherHead[0] - babyHead[0] > REACH_THRESHOLD):
                messageToSend = 'WALK ' + str(babyHead[0] + 0.2) + ' ' + str(babyHead[1]) + ' ' + str(babyHead[2]) + ' ' + str(simulationTime)
            else:
                messageToSend = 'DO_NOTHING'
                babyEpisodeStatus = 'REACH'
                babyReachTarget = motherWrist
                baWristInit = np.array([babyWrist[0],babyWrist[1],babyWrist[2]])
        elif(babyEpisodeStatus == 'REACH'):
            print "BABY REACH"
            #
            # We will want to clean this up, send off to another function...
            #
            if(babyRecFlag == True) and (babyReachTarget[0] - babyWrist[0] > paramContactThreshold):
                babyWrist = np.array(babyWrist)
                babyReachTarget = np.array(babyReachTarget)
                if(numEpisodes == 1):
                    babyShoulderBias = uf.setShoulderBias(babyShoulderBias,babyReachTarget,babyShoulder,babyWrist,numEpisodes,gestureFlag)
                babyReachCoords = np.array(babyReachTarget - babyWrist) * babyReachWeight[0]
                babyVirtualTarget = uf.virtualMotorCorrection(babyShoulder,babyShoulderBias)
                babyGestCoords = np.array(babyVirtualTarget - babyWrist) * babyReachWeight[1]
                babyMotorError = (babyReachCoords + babyGestCoords)
                #babyMotorError = bm.babyMotorControl(babyReachTarget,babyVirtualTarget,babyReachWeight,babyWrist,)
                messageToSend = 'REACH' + ' ' + str(babyMotorError[0] / paramBabyIKReach) + ' ' + str(babyMotorError[1] /paramBabyIKReach) + ' ' + str(babyMotorError[2] /paramBabyIKReach) + ' ' + str(simulationTime)
                # child knows when mother starts to respond / move arm
                #if(bm.babyActionRec(motherWrist,moWristInit,paramBabyRecThreshold)):
                if(abs(sum(motherWrist) - sum(moWristInit)) > paramBabyRecThreshold):
                    babyRecFlag = False
                    #babyReachWeight = bm.babyPostureLearning(babyReachWeight,paramRWInc)
                    babyReachWeight[1] = babyReachWeight[1] + paramRWInc
                    babyReachWeight = babyReachWeight / np.sum(babyReachWeight)
                    babyShoulderBias = uf.setShoulderBias(babyShoulderBias,babyReachTarget,babyShoulder,babyWrist,numEpisodes,gestureFlag)
                    if(babyReachWeight[1] > paramBabyGestThreshold):
                        gestureFlag = True
            else:
                babyEpisodeStatus = 'RESET_ARM'
                messageToSend = 'DO_NOTHING'
        elif(babyEpisodeStatus == 'RESET_ARM'):
            print "BABY RESET_ARM"
            timer1 = timer1 + 1
            if(timer1 < paramTimer1):
                babyPullCoords = np.array(baWristInit - babyWrist)
                messageToSend = 'RESET_ARM' + ' ' + str(babyPullCoords[0] / paramBabyIKPull) + ' ' + str(babyPullCoords[1] /paramBabyIKPull) + ' ' + str(babyPullCoords[2] /paramBabyIKPull) + ' ' + str(simulationTime)
            else:
                babyEpisodeStatus = 'END'
                messageToSend = 'DO_NOTHING'
        elif(babyEpisodeStatus == 'END'):
            print "BABY END"
            # wait until both stop moving, then end episode
            messageToSend = 'DO_NOTHING'
            timer2 = timer2 + 1
            if(timer2 > paramTimer2):
                runEpisode = 0
                babyFile.close()
        win32file.WriteFile(p, bytearray(messageToSend, 'utf-8'))

##
animMessage = win32file.ReadFile(p, 4096)[1]
win32file.WriteFile(p, bytearray('STOP', 'utf-8'))
print("Last message received")
win32file.CloseHandle(p)

