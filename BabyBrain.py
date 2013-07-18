import win32pipe, win32file, time, operator
import UtilityFunctions as uf
import pybrain
import numpy as np
import matplotlib.pyplot as pyp
import time

print "Starting Baby Brain Simulation"

## Set global variables for initialization and checking
MOTHER_INITIAL_POSITION = [6.272, 12.511, 8.828]
BABY_INITIAL_POSITION = [-8.595, 7.843, 7.813]
GESTURE_THRESHOLD = 10
REACH_THRESHOLD = 7

p = win32pipe.CreateNamedPipe( r'\\.\pipe\BabyBrainPipe',
	win32pipe.PIPE_ACCESS_DUPLEX,
	win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_WAIT,
	1, 65536, 65536, 30000000, None )

win32pipe.ConnectNamedPipe(p, None)
##
simulationTime = 0
##
numEpisodes = 0
while(numEpisodes < 5):
    numEpisodes = numEpisodes + 1
    babyEpisodeStatus = 'TO_START'
    runEpisode = 1
    flag = True
    timer1 = 0
    timer2 = 0
    timer3 = 0
    episodeTime = 0
    tmp = 1
    tmpStr = 'babyTrajectory_Episode'+str(tmp)+'.txt'
    babyFile = open(tmpStr, 'w')
    #babyFile = open('babyTrajectory_Episode1.txt', 'w')

    ##
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
            messageToSend = 'INIT ' + str(BABY_INITIAL_POSITION[0]) + ' ' + str(BABY_INITIAL_POSITION[1]) + ' ' + str(BABY_INITIAL_POSITION[2]) + ' ' + str(simulationTime)
            babyEpisodeStatus = 'INITIALIZED'

        elif(babyEpisodeStatus == 'INITIALIZED'):
            #makes so baby always must walk at least a little
            if(motherHead[0] - babyHead[0] > GESTURE_THRESHOLD):
                babyEpisodeStatus = 'WALK'
                messageToSend = 'DO_NOTHING'
                #below, save motherWrist init (x,y,z)
                moWristInit = np.array([motherWrist[0],motherWrist[1],motherWrist[2]])
        elif(babyEpisodeStatus == 'WALK'):
            # indicates max distance can reach from
            if(motherHead[0] - babyHead[0] > REACH_THRESHOLD):
                messageToSend = 'WALK ' + str(babyHead[0] + 0.2) + ' ' + str(babyHead[1]) + ' ' + str(babyHead[2]) + ' ' + str(simulationTime)
            else:
                messageToSend = 'DO_NOTHING'
                babyEpisodeStatus = 'REACH'

        elif(babyEpisodeStatus == 'REACH'):
            timer1 = timer1 + 1
            if(timer1 < 30 and flag == True):
                messageToSend = 'MOVE_ARM' + ' ' + str(0) + ' ' + str(0) + ' ' + str(2) + ' ' + str(simulationTime)
                # child knows when mother starts to respond / move arm
                if(abs(sum(motherWrist) - sum(moWristInit)) > 0.2):
                    flag = False
            else:
                babyEpisodeStatus = 'RESET_ARM'
                messageToSend = 'DO_NOTHING'

        elif(babyEpisodeStatus == 'RESET_ARM'):
            timer2 = timer2 + 1
            if(timer2 < 20):
                messageToSend = 'MOVE_ARM' + ' ' + str(0) + ' ' + str(0) + ' ' + str(-2) + ' ' + str(simulationTime)
            else:
                babyEpisodeStatus = 'END'
                messageToSend = 'DO_NOTHING'
        elif(babyEpisodeStatus == 'END'):
            # wait until both stop moving, then end episode
            messageToSend = 'DO_NOTHING'
            timer3 = timer3 + 1
            if(timer3 > 30):
                runEpisode = 0

        win32file.WriteFile(p, bytearray(messageToSend, 'utf-8'))
    if(numEpisodes < 5):
            babyFile.close()

##
uf.parseMessage(animMessage, motherWrist, motherShoulder, motherElbow, motherHead, babyWrist, babyShoulder, babyElbow, babyHead)
uf.writeReceivedCoordinatesToFile(babyFile, motherWrist, motherShoulder, motherElbow, motherHead, babyWrist, babyShoulder, babyElbow, babyHead, simulationTime)
win32file.WriteFile(p, bytearray('STOP', 'utf-8'))
babyFile.close()

win32file.CloseHandle(p)

