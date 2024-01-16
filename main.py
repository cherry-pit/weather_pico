#!/usr/bin/python3

###
### First we define functions
###

def getXMLElements(xmlInput, tagName, attributeNames=[], attributeValues=[]):

    # - Inputs -
    # xmlInput - list of xml rows split on "\n" - this is more memory efficent
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
    # This function will return a list of strings for all the elements that match in the xmlFileName with the tagname and provided attribute information

    ###################

    #
    # First we will narrow down the file based on tagname alone and create a list of elements of interest
    #

    # the below pattern will pull out all the possible attributes assosiated with a specific tag and append them to the list attributeNames

    from re import compile as regex_compile

    patt = regex_compile(f"<{tagName}(.*?)</{tagName}>")
    elements = []

    for xmlLine in xmlInput:
        n = 0
        while n < len(xmlLine):
            regSearch = patt.search(xmlLine[n:])
            if regSearch != None:
                n += regSearch.end()
                elements.append(regSearch.group(0))
            else:
                break
  
    del xmlInput, regSearch, patt, n, xmlLine 
    
    #
    # Now we iterate over the elements only selected by tagname and check if they have the correct attributes
    #

    badElementIndicies = []

    if attributeNames:
        for k in range(len(elements)):

            correctAttributes = False
            for b in range(len(attributeNames)):

                patt = regex_compile(f"{attributeNames[b]}=\"(.*?)\"")
                searchResult = patt.search(elements[k])

                if searchResult == None:
                    correctAttributes = False
                    break
                elif searchResult.group(1) != attributeValues[b]:
                    correctAttributes = False
                    break
                elif searchResult.group(1) == attributeValues[b]:
                    correctAttributes = True

            if not correctAttributes:
                badElementIndicies.append(k)

            del searchResult, patt, correctAttributes, b, k

    # return a list of elements that have matching input attributes
    return [elements[i] for i in range(len(elements)) if i not in badElementIndicies]

def getXMLValues(xmlInput, valueTag="value"):

    # provide an xml input and this function will return all the entries associated with value tags
    # this function will return a list of values
    # 
    # See the example below
    # '<cloud-amount type="total" units="percent" time-layout="k-p1h-n1-0"><value>71</value><value>75</value><value>84</value><value>88</value><value>91</value>...
    # If the above string is given as the xmlInput the below will be returned
    # ['71','75','84','88','91',]

    from re import compile as regex_compile

    patt = regex_compile(f"<{valueTag}>(.*?)</{valueTag}>")
    values = []
    n = 0
    while n < len(xmlInput):
        regSearch = patt.search(xmlInput[n:])
        if regSearch != None:
            n += regSearch.end()
            values.append(regSearch.group(1))
        else:
            break

    return values

def getCurrentTime(timezone_offset):
    
    # returns a touple of current (hour, minute) based on time server call
    
    from time import localtime
    from ntptime import settime
    
    try:
        settime()
        local_time = localtime()
        hour = local_time[3] + timezone_offset
        
        if hour < 0:
            hour += 24

        return (hour, local_time[4])
    
    except:
        return (-1, -1)
    
def show_on_lcd(line1,line2):

    from machine import I2C
    from lcd_api import LcdApi
    from i2c_lcd import I2cLcd

    I2C_ADDR     = 0x27
    I2C_NUM_ROWS = 2
    I2C_NUM_COLS = 16

    i2c = I2C(0, sda=machine.Pin(0), scl=machine.Pin(1), freq=200000)
    lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)
    lcd.putstr(f'{line1}\n{line2}')

###
###
###

from parameters import *
from network import WLAN, STA_IF
from machine import lightsleep

wlan = WLAN(STA_IF)

while True:
        
    while not wlan.isconnected():
        show_on_lcd("Starting...", "Wifi Pending")
        wlan.active(True)
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        lightsleep(4 * 1000)
    
    show_on_lcd("Wifi Connected", "")


    # call weather .gov for the weather report closest to the provided US long and lat
    
    from requests import get
    
    responseStatusCode = None
    retryCount = 0
    while responseStatusCode != 200:

        # restart the pico if the weather cannon be retrieved after an hour
        if retryCount > 30:
            machine.reset()

        try:
            response = get( f'https://forecast.weather.gov/MapClick.php?lat={lat}&lon={long}&FcstType=digitalDWML' ,
                            headers={'User-agent': 'Mozilla/5.0'} ,
                            timeout=15)
            responseStatusCode = response.status_code
        # catch the request timing out
        except OSError:
            responseStatusCode = 0
        # if we are able to get the weather report from weather.gov then we write the response content to disk
        if 200 == responseStatusCode:
            xmlWeatherResponseLines = response.content.decode().split("\n")
        
        # if we are not able to get the response wait a minute and try again
        else:
            lightsleep(120 * 1000)
            retryCount += 1

    del response, responseStatusCode, retryCount, get

    # Extract the start time stamps -- these serve as indecies
    startTimeStamps = getXMLValues("".join(getXMLElements(xmlWeatherResponseLines, "start-valid-time")), valueTag="start-valid-time")

    # Extract the hourly temp
    hourlyTemps = getXMLValues(getXMLElements(xmlWeatherResponseLines, "temperature", ["type"], ["hourly"])[0])

    # Extract probabilty of rain as a percent
    hourlyPrecipitation = getXMLValues(getXMLElements(xmlWeatherResponseLines, "probability-of-precipitation" )[0])

    # Extract cloud coverage percent
    hourlyCloudAmount = getXMLValues(getXMLElements(xmlWeatherResponseLines, "cloud-amount")[0])


    del xmlWeatherResponseLines

    currentHour = 0

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

            break

    del x, offset

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
    forecastString = ' '.join(forecastList[:daySplitIndex]) + '|' + ' '.join(forecastList[daySplitIndex:])

    line1 = "%-3s" % currentTemp + "% 13s" % f"{minTemp},{maxTemp}"
    line2 = forecastString

    del n, median_temp, probaility_of_rain, median_cloud_coverage, weather_letter, minTemp, maxTemp, currentTemp, daySplitIndex, forecastString, forecastList, currentHour
    del hourlyCloudAmount, hourlyPrecipitation, hourlyTemps, startTimeStamps

    # Now we can display the weather forecast
    show_on_lcd(line1, line2)

    # We can now shut down wifi
    wlan.disconnect()
    wlan.active(False)

    minuteOfHour = getCurrentTime(timezone_offset)[1]
    sleepTime = 600

    # The internal clock on the raspberry pi pico is not incredibly reliable so the below code will account for drift
    if minuteOfHour != -1: # if the function ran with no errors

        deltaFrom5 = 5 - minuteOfHour
        deltaFrom35 = 35 - minuteOfHour

        if minuteOfHour < 5:
            sleepTime = ( deltaFrom5 ) * 60

        elif minuteOfHour > 5 and minuteOfHour < 35:
            sleepTime = ( deltaFrom35 ) * 60

        elif minuteOfHour > 35:
            sleepTime = ( 5 + (60 - minuteOfHour) ) * 60

        elif minuteOfHour == 5 or minuteOfHour == 35:
            sleepTime = 0
            
    lightsleep(sleepTime * 1000) # light sleep is in ms and will retain RAM contents

    del sleepTime, minuteOfHour, deltaFrom5, deltaFrom35
