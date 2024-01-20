#!/usr/bin/python3

from parameters import *
from network import WLAN, STA_IF
from time import sleep

wlan = WLAN(STA_IF)

from functions import show_on_lcd
show_on_lcd("Starting...", "")
sleep(0.75)
conditions = {'C':'Clear',
              'O':'Overcast',
              'R':'Rain',
               '*':'Snow',
               '!' : 'Weather advisory'}
for key in sorted(conditions):
   show_on_lcd(key,conditions[key])
   sleep(2)
del show_on_lcd, conditions, key

try:
    while True:
            
        while not wlan.isconnected():
            wlan.active(True)
            wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            sleep(4)

        # call weather .gov for the weather report closest to the provided US long and lat
        from functions import makeRequestGetXML
        xmlWeatherResponseLines = makeRequestGetXML(f"https://forecast.weather.gov/MapClick.php?lat={lat}&lon={long}&FcstType=digitalDWML")
        del makeRequestGetXML

        tagsToKeep = ("start-valid-time", "temperature", "probability-of-precipitation", "cloud-amount")
        # Filter down the XML response to only keep rows with tags we are interested in
        xmlWeatherResponseLinesKept = []
        while xmlWeatherResponseLines:
            xmlLine = xmlWeatherResponseLines.pop(0).strip()
            firstBracketIndex = xmlLine.find(">")
            firstSpaceIndex = xmlLine.find(" ")
            tag = xmlLine[1:firstBracketIndex]
            if firstSpaceIndex > 0 and firstSpaceIndex < firstBracketIndex:
                tag = tag[:firstSpaceIndex-1]
            if tag in tagsToKeep and tag != "":
                xmlWeatherResponseLinesKept.append(xmlLine)
        xmlWeatherResponseLines = (xmlWeatherResponseLinesKept)

        del xmlWeatherResponseLinesKept, tag, tagsToKeep, firstSpaceIndex, firstBracketIndex, xmlLine

        from functions import getXMLElements, getXMLValues
        # Extract the start time stamps -- these serve as indecies
        startTimeStamps = getXMLValues("".join(getXMLElements(xmlWeatherResponseLines, "start-valid-time")), valueTag="start-valid-time")
        # Extract the hourly temp
        hourlyTemps = getXMLValues(getXMLElements(xmlWeatherResponseLines, "temperature", ["type"], ["hourly"])[0])
        # Extract probabilty of rain as a percent
        hourlyPrecipitation = getXMLValues(getXMLElements(xmlWeatherResponseLines, "probability-of-precipitation" )[0])
        # Extract cloud coverage percent
        hourlyCloudAmount = getXMLValues(getXMLElements(xmlWeatherResponseLines, "cloud-amount")[0])
        del xmlWeatherResponseLines, getXMLElements, getXMLValues

        # Gather information about weather alerts
        # Define the varible used to show if there is a weather alert
        showCaution = False
        # Using the county code if provided from the paramters file to see if there are any weather alerts for the county
        if county_code != "":

            from functions import makeRequestGetXML
            xmlAlertsResponseLines = makeRequestGetXML(f"https://alerts.weather.gov/cap/wwaatmget.php?x={county_code}&y=1")
            del makeRequestGetXML
            
            # Each weather alert has a summary associated with it
            tagsToKeep = ("summary")
            # Filter down the XML response to only keep rows with tags we are interested in
            xmlAlertsResponseLinesKept = []
            while xmlAlertsResponseLines:
                xmlLine = xmlAlertsResponseLines.pop(0).strip()
                firstBracketIndex = xmlLine.find(">")
                firstSpaceIndex = xmlLine.find(" ")
                tag = xmlLine[1: firstBracketIndex]
                if firstSpaceIndex > 0 and firstSpaceIndex < firstBracketIndex:
                    tag = tag[:firstSpaceIndex-1]
                if tag in tagsToKeep and tag != "":
                    xmlAlertsResponseLinesKept.append(xmlLine)
            xmlAlertsResponseLines = (xmlAlertsResponseLinesKept)

            if len(xmlAlertsResponseLines) > 0:
                showCaution = True

            del tagsToKeep, xmlAlertsResponseLinesKept, xmlAlertsResponseLines, firstBracketIndex, firstSpaceIndex, xmlLine, tag

        # Now we begin analyzing the retrived information
        # Getting the current time
        from functions import getCurrentTime
        currentHour, minuteOfHour = getCurrentTime(timezone_offset)
        del getCurrentTime

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
        forecastString = ' '.join(forecastList[:daySplitIndex]) + '|' + ' '.join(forecastList[daySplitIndex:])

        warningString = ""
        if showCaution:
            warningString = "!"

        line1_part1 = f"{currentTemp} {warningString}"
        spaceCount = 16-len(line1_part1)-len(f"{minTemp},{maxTemp}")
        line1 = line1_part1 + " " * spaceCount + f"{minTemp},{maxTemp}"
        line2 = forecastString

        del n, median_temp, probaility_of_rain, median_cloud_coverage, weather_letter, minTemp, maxTemp, currentTemp, daySplitIndex, forecastString, forecastList, currentHour
        del hourlyCloudAmount, hourlyPrecipitation, hourlyTemps, startTimeStamps, warningString, showCaution

        # Now we can display the weather forecast
        from functions import show_on_lcd
        show_on_lcd(line1, line2)
        del show_on_lcd

        # We can now shut down wifi
        wlan.disconnect()
        wlan.active(False)

        # The internal clock on the raspberry pi pico is not incredibly reliable so the below code will account for drift
        if minuteOfHour != -1: # if we have a set time

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
                
        else: # if we don't have a set time sleep for 10 minutes and try to run the loop again
            sleepTime = 600
                
        sleep(sleepTime)

        del sleepTime, minuteOfHour, deltaFrom5, deltaFrom35, line1_part1, spaceCount, line1, line2
        

except BaseException as e:
    from functions import show_on_lcd
    print(e)
    show_on_lcd(str(e)[:16], str(e)[16:32])
