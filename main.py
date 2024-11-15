#!/usr/bin/python3

import gc
import network
from time import sleep
import parameters as params
import machine

gc.enable()

watchdog_timer= None
watchdog_timer = machine.WDT(timeout=8100)  # enable it with a timeout of 8.1 seconds

wlan = network.WLAN(network.STA_IF)

#######################################################
## Define functions to be used throughout the script ##
#######################################################

def limitedGetRequest(url, tagsToKeep=(), timeout=8,  maxConnectionAttempts=10):
    
    import ssl, socket, gc
    global watchdog_timer

    watchdog_timer.feed()    

    scheme, _, host, target = url.split("/",3)

    if scheme == "https:":
        port = 443
    elif scheme == "http:":
        port = 80

    connectionAttempts = 0

    while connectionAttempts <= maxConnectionAttempts:
        connectionAttempts += 1

        try:
            ai = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)[0]
            s = socket.socket(ai[0], socket.SOCK_STREAM, ai[2])
            s.settimeout(timeout) # time for connection to timeout in seconds
            watchdog_timer.feed()
        except:
            #print("Issue setting up socket")
            s.close()
            continue
        
        try:
            s.connect(ai[-1])
            s = ssl.wrap_socket(s, server_hostname=host)
            s.setblocking(True)
            watchdog_timer.feed()
        except:
            #print("Issue connecting to server or wrapping socket")
            s.close()
            continue
    
        try:
            s.write(f"GET /{target} HTTP/1.0\r\nHost: {host}\r\nUser-agent: Weather Pico\r\nConnection: close\r\n\r\n")
            watchdog_timer.feed()
        except:
            #print("Issue writing to socket")
            s.close()
            continue
    
        try:
            keptLines = []
            strBuff = []
            buildString = False
            keepLine = False
            checkStatus = True
            while True:
                
                watchdog_timer.feed()
                buff = s.read(256)
                gc.collect()                
                if buff != b"":
                    
                    if checkStatus:
                        # extract the status code from the http response
                        statusCode = buff.split(b'\r\n',1)[0].split(b' ',2)[1]
                        checkStatus = False
                        if statusCode != b'200':
                            return -1
                    
                    for x in buff:
                        
                        x = chr(x)

                        if buildString:
                            strBuff.append(x)
                        
                        if x == "<" and not buildString:
                            buildString = True
                            strBuff.append(x)
                        
                        elif x == ">" and buildString and not keepLine:
                            bufferTagName = "".join(strBuff[1:-1]).split(" ",1)[0]
                            if any( tag in bufferTagName for tag in tagsToKeep ) and strBuff[1] != "/":
                                keepLine = True
                            else:
                                buildString = False
                                keepLine = False
                                strBuff = []
                            
                        elif x == ">" and buildString and keepLine:
                            closingTag = "</" + bufferTagName + ">"
                            if "".join(strBuff[-len(closingTag):]) == closingTag:
                                keptLines.append( "".join(strBuff) )
                                buildString = False
                                keepLine = False
                                strBuff = []
                            
                else:
                    break

            s.close()
            del s
            gc.collect()
            return (keptLines)

        except:
            #print("Issue reading from socket")
            s.close()
            pass

    raise


def getXMLElements(xmlInput, tagName, attributeNames=[], attributeValues=[]):

    # - Inputs -
    # xmlInput - list or tuple of xml rows split on "\n" 
    # 
    # tagName - string tagename that this function will look for
    #                   tagName example
    # <temperature type="dew point" time-layout="k-p1h-n1-0"><value>-7</value><value>-7</value><value>-6</value><value>-7...
    # temperature would be the tagname you would want to provide if you want this function to return this row
    #
    # attributeNames - list of strings that are attributes you would like to match, the order must correspond with the order of the attributeValues, optional
    #                    attributeNames example
    # attributeNames = ["type","time-layout"]
    # type and time-layout would be matched with the first and second entires in the attributeValues list
    #
    # attributeValues - a list of strings that corresponds to the order of attributes in attributeNames, this is optional
    #                     attributeNames example
    # attributeNames = ["dew point", "k-p1h-n1-0"]
    #
    # This function will return a tuple of strings for all the elements that match in the xmlFileName with the tagname and provided attribute information

    ###################

    #
    # First we will narrow down the file based on tagname alone and create a list of elements of interest
    #

    # the below pattern will pull out all the possible attributes assosiated with a specific tag and append them to the list attributeNames

    import re
    import gc

    patt = re.compile(f"<{tagName}(.*?)</{tagName}>")
    elementsFiltered = []

    for xmlLine in xmlInput:
        n = 0
        while n < len(xmlLine):
            regSearch = patt.search(xmlLine[n:])
            if regSearch != None:
                n += regSearch.end()
                elementsFiltered.append(regSearch.group(0))
            else:
                break
  
    del regSearch, patt, n, xmlLine 

    elementsFiltered2 = []

    if attributeNames:
        while elementsFiltered:
            element = elementsFiltered.pop()
            correctAttributes = False
            
            for b in range(len(attributeNames)):

                patt = re.compile(f"{attributeNames[b]}=\"(.*?)\"")
                searchResult = patt.search(element)

                if searchResult == None:
                    correctAttributes = False
                    break
                elif searchResult.group(1) != attributeValues[b]:
                    correctAttributes = False
                    break
                elif searchResult.group(1) == attributeValues[b]:
                    correctAttributes = True

            if correctAttributes:
                elementsFiltered2.append(element)

            del searchResult, patt, correctAttributes, b, element

        return (elementsFiltered2)

    else:
        return (elementsFiltered)

def getXMLValues(xmlInput, valueTag="value"):
    
    # xmlInput - tuple or list
    # valueTag - string
    # provide an xml input and this function will return all the entries associated with value tags
    # this function will return a tuple of values
    # 
    # See the example below
    # '<cloud-amount type="total" units="percent" time-layout="k-p1h-n1-0"><value>71</value><value>75</value><value>84</value><value>88</value><value>91</value>...
    # If the above string is given as the xmlInput the below will be returned
    # ('71','75','84','88','91')

    import re

    patt = re.compile(f"<{valueTag}>(.*?)</{valueTag}>")
    values = []
    n = 0
    while n < len(xmlInput):
        regSearch = patt.search(xmlInput[n:])
        if regSearch != None:
            n += regSearch.end()
            values.append(regSearch.group(1))
        else:
            break

    return tuple(values)

def getCurrentTime(timezone_offset, maxConnectionAttempts=10):
    
    # returns a touple of current (hour, minute) based on time server call
    # timezone_offset should be given as an integer for hours difference from GMT
    
    import time
    import ntptime
    
    ntptime.timeout = 15
    ntptime.host = "pool.ntp.org"

    connectionAttempts = 0
    while connectionAttempts < maxConnectionAttempts:
        connectionAttempts += 1

        try:
            ntptime.settime()
            local_time = time.localtime()
            hour = local_time[3] + timezone_offset
            
            if hour < 0:
                hour += 24

            return (hour, local_time[4])
        
        except:
            #print("Failed to set time")
            pass
        
    return (-1, -1)
    
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

#######################################################
#######################################################
#######################################################

# Display information to the user

show_on_lcd("Starting...", "")
sleep(1)
watchdog_timer.feed()
show_on_lcd("| - Separates today", " and tomorrow")
sleep(1.5)
watchdog_timer.feed()
show_on_lcd(". - Shows noon", "")
sleep(1.5)
watchdog_timer.feed()
show_on_lcd("XX", "Current temp")
sleep(1.5)
watchdog_timer.feed()
show_on_lcd("           XX,XX", "Min, Max temp")
sleep(1.5)
watchdog_timer.feed()
show_on_lcd("Next 24 hrs", "X X X X X X X X")
sleep(1.5)
conditions = {'C':'Clear',
              'O':'Overcast',
              'R':'Rain',
               '*':'Snow',
               '! to *!!!!!*' : 'Weather advisory'
              }
for key in sorted(conditions):
   show_on_lcd(key,conditions[key])
   sleep(1.5)
   watchdog_timer.feed()
del conditions, key

try:
    
    while True:
        
        watchdog_timer.feed()

        wlan.active(True)
        wlan.connect(params.WIFI_SSID, params.WIFI_PASSWORD)         
        while not wlan.isconnected():
            sleep(4)
            watchdog_timer.feed()
        
        # call weather .gov for the weather report closest to the provided US long and lat
        tagsToKeep = ["start-valid-time", "temperature", "probability-of-precipitation", "cloud-amount"]
        xmlWeatherResponseLines = limitedGetRequest(f"https://forecast.weather.gov/MapClick.php?lat={params.lat}&lon={params.long}&FcstType=digitalDWML", tagsToKeep, 60)
        watchdog_timer.feed()
        gc.collect()

        # Gather information about weather alerts
        # Define the varible used to show if there is a weather alert
        cautionAlertString = ""
        # Using the county code if provided from the paramters file to see if there are any weather alerts for the county
        if params.county_code != "":
                # https://api.weather.gov/alerts/active?point=41,-87
            tagsToKeep = ["cap:urgency", "cap:severity", "cap:certainty"]
            xmlWeatherAlerts = limitedGetRequest(f"https://api.weather.gov/alerts/active.atom?zone={params.county_code}", tagsToKeep, timeout=60)
            watchdog_timer.feed()
            
            if xmlWeatherAlerts:
                for n in range(0, len(xmlWeatherAlerts), 3):
                    urgency = xmlWeatherAlerts[n].upper()
                    severity = xmlWeatherAlerts[n+1].upper()
                    certainty = xmlWeatherAlerts[n+2].upper()
                    
                    # Possible severities are "MINOR", "MODERATE", "SEVERE", "EXTREME"
                    if "UNLIKELY" not in certainty and "PAST" not in urgency:
                        if "MINOR" in severity and len(cautionAlertString) < len("!"):
                            cautionAlertString = "!"
                        elif "MODERATE" in severity and len(cautionAlertString) < len("!!"):
                            cautionAlertString = "!!"
                        elif "SEVERE" in severity and len(cautionAlertString) < len("!!!"):
                            cautionAlertString = "!!!"
                        elif "EXTREME" in severity and len(cautionAlertString) < len("*!!!!!*"):
                            cautionAlertString = "*!!!!!*"
                
                del xmlWeatherAlerts, urgency, severity, certainty

        del tagsToKeep

        watchdog_timer.feed()
        gc.collect()

        # Extract the start time stamps -- these serve as indecies
        startTimeStamps = getXMLValues("".join(getXMLElements(xmlWeatherResponseLines, "start-valid-time")), valueTag="start-valid-time")
        gc.collect()
        # Extract the     hourly temp
        hourlyTemps = getXMLValues(getXMLElements(xmlWeatherResponseLines, "temperature", ["type"], ["hourly"])[0])
        gc.collect()
        # Extract probabilty of rain as a percent
        hourlyPrecipitation = getXMLValues(getXMLElements(xmlWeatherResponseLines, "probability-of-precipitation" )[0])
        gc.collect() 
        # Extract cloud coverage percent
        hourlyCloudAmount = getXMLValues(getXMLElements(xmlWeatherResponseLines, "cloud-amount")[0])

        del xmlWeatherResponseLines
        gc.collect()
        watchdog_timer.feed()

        # Now we begin analyzing the retrived information
        # Getting the current time
        currentHour, minuteOfHour = getCurrentTime(params.timezone_offset)
        
        gc.collect()
        watchdog_timer.feed()

        # we want to treat the current hour as the first starting index for all the lists of values
        # here we check for what index we should use for this offset and assing it to the varible offset
        for x in startTimeStamps:
            if int(x[11:13]) == currentHour:
                offset = startTimeStamps.index(x)
                # trim down all the lists of values to account for the found offset
                if offset != 0:
                    startTimeStamps = startTimeStamps[offset:]
                    hourlyTemps = hourlyTemps[offset:]
                    hourlyPrecipitation = hourlyPrecipitation[offset:]
                    hourlyCloudAmount = hourlyCloudAmount[offset:]
                del offset
                break
        del x

        hourlyTemps = [int(x) for x in hourlyTemps]
        hourlyPrecipitation = [int(x) for x in hourlyPrecipitation]
        hourlyCloudAmount = [int(x) for x in hourlyCloudAmount]
        
        forecastList = []
        # Pull in indicies for the next 24 hours of data in steps of 3
        for n in range(0,len(startTimeStamps[:24]),3):
            median_temp = sorted(hourlyTemps[n:n+3])[1]
            probaility_of_rain = max(hourlyPrecipitation[n:n+3])
            median_cloud_coverage = sorted(hourlyCloudAmount[n:n+3])[1]

            weather_letter = 'O'
            if median_temp > 32 and probaility_of_rain >= 33:
                weather_letter = 'R' # rain
            elif median_temp <= 32 and probaility_of_rain > 33:
                weather_letter = '*' # snow
            elif median_cloud_coverage <= 80 and probaility_of_rain < 33:
                weather_letter = 'C' # Sunny

            forecastList.append(weather_letter)

        minTemp = min(hourlyTemps[:24])
        maxTemp = max(hourlyTemps[:24])
        currentTemp = hourlyTemps[0]

        daySplitIndex = round( ( 24 - currentHour ) / 3 )
        # this string will function as the second displayed line
        #forecastString = ' '.join(forecastList[:daySplitIndex]) + '|' + ' '.join(forecastList[daySplitIndex:])
        if currentHour <= 12:
            noonSplitIndex = round( ( 12 - currentHour ) / 3 )
        else:
            noonSplitIndex = daySplitIndex + 4

        if noonSplitIndex < daySplitIndex:
            forecastString = \
            ' '.join(forecastList[:noonSplitIndex]) + "." + \
            ' '.join(forecastList[noonSplitIndex:daySplitIndex]) + "|" + \
            ' '.join(forecastList[daySplitIndex:])
        else:
            forecastString = \
            ' '.join(forecastList[:daySplitIndex]) + "|" + \
            ' '.join(forecastList[daySplitIndex:noonSplitIndex]) + "." + \
            ' '.join(forecastList[noonSplitIndex:])

        line1_part1 = f"{currentTemp} {cautionAlertString}"
        spaceCount = 16-len(line1_part1)-len(f"{minTemp},{maxTemp}")
        line1 = line1_part1 + " " * spaceCount + f"{minTemp},{maxTemp}"

        del n, median_temp, probaility_of_rain, median_cloud_coverage, weather_letter, minTemp, maxTemp, currentTemp, daySplitIndex, \
              forecastList, currentHour, hourlyCloudAmount, hourlyPrecipitation, hourlyTemps, \
                startTimeStamps, noonSplitIndex

        # Now we can display the weather forecast
        show_on_lcd(line1, forecastString)

        # We can now shut down wifi
        wlan.disconnect()
        wlan.active(False)

        # The internal clock on the raspberry pi pico is not incredibly reliable so the below code will account for drift
        if minuteOfHour != -1: # if we have a set time

            deltaFrom5 = 5 - minuteOfHour
            deltaFrom35 = 35 - minuteOfHour

            if minuteOfHour < 5:
                sleepTime = (( deltaFrom5 ) * 60 ) + 60
            elif minuteOfHour > 5 and minuteOfHour < 35:
                sleepTime = (( deltaFrom35 ) * 60 ) + 60
            elif minuteOfHour > 35:
                sleepTime = (( 5 + (60 - minuteOfHour) ) * 60 ) + 60
            elif minuteOfHour == 5 or minuteOfHour == 35:
                sleepTime = 60

            del deltaFrom5, deltaFrom35

        else: # if we don't have a set time sleep for 10 minutes and try to run the loop again
            sleepTime = 600

        del minuteOfHour, line1_part1, spaceCount, line1, forecastString

        gc.collect()
        watchdog_timer.feed()
        
        for n in range(sleepTime/2):
            sleep(2)
            watchdog_timer.feed()

except BaseException as e:
    print(e)
    show_on_lcd(str(e)[:16], str(e)[16:32])
    from random import randint
    numb = randint(0,1000)
    raise

