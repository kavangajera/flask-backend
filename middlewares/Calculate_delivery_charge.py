def calculateDelivery(amount):
    if (amount <= 999):
        return 0
    elif (amount<=5000):
        return 90
    elif (amount<=10000):
        return 180
    elif (amount<=20000):
        return 240
    elif (amount<=30000):
        return 560
    else :
        return 850
    