def babyMotorControl(babyReachTarget,babyVirtualTarget,babyReachWeight,babyWrist,):
    import numpy as np
    babyReachCoords = np.array([0,0,0])
    babyGestCoords = np.array([0,0,0])
    babyReachCoords = np.array(babyReachTarget - babyWrist) * babyReachWeight[0]
    babyGestCoords = np.array(babyVirtualTarget - babyWrist) * babyReachWeight[1]
    babyMotorError = (babyReachCoords + babyGestCoords)
    return babyMotorError
def babyActionRec(motherWrist,moWristInit,paramBabyRecThreshold):
    b = abs(sum(motherWrist) - sum(moWristInit)) > paramBabyRecThreshold
    return b
def babyPostureLearning(babyReachWeight,paramRWInc):
    import numpy as np
    babyReachWeight[1] = babyReachWeight[1] + paramRWInc
    babyReachWeight = babyReachWeight / np.sum(babyReachWeight)
    return babyReachWeight
