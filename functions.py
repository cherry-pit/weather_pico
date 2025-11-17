def parseTimestamp(inputStringTimestamp):
    
    # example input timestamp = '2025-11-08T22:00:00-06:00'

    year = inputStringTimestamp[0:4]
    month = inputStringTimestamp[5:7]
    day = inputStringTimestamp[8:10]
    hour = inputStringTimestamp[11:13]
    minute = inputStringTimestamp[14:16]
    second = inputStringTimestamp[17:19]

    return tuple([int(x) for x in (year,month,day,hour,minute,second)]) + (None,None)

def convertTimeStampToUTCEpoch(inputTimestamp):

    import time
    
    tzOffset = inputTimestamp[-6:]
    inputTimestampNoTZ = inputTimestamp[:-6]
    offsetDirection = int(tzOffset[0] + '1')
    offsetHours, offsetMinutes = [int(x) * offsetDirection for x in tzOffset[1:].split(':')]
    offsetHours, offsetMinutes = offsetHours * 3600, offsetMinutes * 60
    
    inputTimestampNoTZEpoch = time.mktime(parseTimestamp(inputTimestampNoTZ))
    inputTimestampUTCEpoch = inputTimestampNoTZEpoch - offsetHours - offsetMinutes
    
    return inputTimestampUTCEpoch

def getRequestWrapper(endpoint, headers, buffer):
    
    import urequests

    class BadAPIStatusCode(Exception):
        def __init__(self, message="BadAPIStatusCode"):
            super().__init__(message)
            self.message = message

    response = urequests.get(endpoint, headers=headers, stream=True)
    if response.status_code != 200:
        raise BadAPIStatusCode 
    
    offset = 0
    while True:
        chunk = response.raw.read(1024)
        if not chunk or offset + len(chunk) > len(buffer):
            break
        memoryview(buffer)[offset:offset+len(chunk)] = chunk
        offset += len(chunk)

    response.close()

    return offset

def findallSubStrings(matchString,offsetAhead,buffer,bufferSize):
    offset = 0
    windowSize = len(matchString)
    foundIndicies = []
    while offset+windowSize-1 < bufferSize: 
        searchString = bytes(memoryview(buffer)[offset:offset+windowSize])
        if matchString.upper() == searchString.upper():
            if offsetAhead:
                foundIndicies.append(offset+windowSize)
            else:
                foundIndicies.append(offset)
        offset += 1
    return foundIndicies

def findallRangeGroups(match1, match2, buffer, bufferSize):
    
    startIndicies = findallSubStrings(match1, True, buffer, bufferSize)
    endIndicies = findallSubStrings(match2, False, buffer, bufferSize)
    
    return [x for x in zip(startIndicies,endIndicies)]

def findAllValues(parentTag1, parentTag2, childTag1, childTag2, buffer, bufferSize):

    if not parentTag1 and not parentTag2:
        parentGroups=[(0,bufferSize)]
    else:
        parentGroups = findallRangeGroups(parentTag1, parentTag2, buffer, bufferSize)
        if not parentGroups:
            return []
    
    allChildGroups = []
    for parentGroup in parentGroups:
        childGroups = findallRangeGroups(childTag1, childTag2, memoryview(buffer)[parentGroup[0]:parentGroup[1]],parentGroup[1])
        childGroupsBufferIndexed = [(x[0]+parentGroup[0], x[1]+parentGroup[0]) for x in childGroups]
        childGroupValues = [bytes(memoryview(buffer)[x[0]:x[1]]).decode() for x in childGroupsBufferIndexed]
        allChildGroups.append(childGroupValues)
    
    return allChildGroups

def show_on_lcd(line1,line2):

    # line 1 and line 2 are string inputs that will be displayed accordingly

    from machine import I2C, Pin
    from lcd_api import LcdApi
    from i2c_lcd import I2cLcd

    I2C_ADDR     = 0x27
    I2C_NUM_ROWS = 2
    I2C_NUM_COLS = 16

    i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=200000)
    lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)
    lcd.putstr(f'{line1}\n{line2}')
    
def clearBuffer(buffer):
    for i in range(len(memoryview(buffer))):
        memoryview(buffer)[i] = 0


