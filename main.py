#!/usr/bin/python3

import gc
import network
from time import sleep
import parameters as params
import functions

gc.enable()

wlan = network.WLAN(network.STA_IF)

functions.show_on_lcd("Starting...", "")
sleep(1)
functions.show_on_lcd("| - Separates today", " and tomorrow")
sleep(1.5)
functions.show_on_lcd(". - Shows noon", "")
sleep(1.5)
functions.show_on_lcd("XX", "Current temp")
sleep(1.5)
functions.show_on_lcd("           XX,XX", "Min, Max temp")
sleep(1.5)
functions.show_on_lcd("Next 24 hrs", "X X X X X X X X")
sleep(1.5)
conditions = {'C':'Clear',
              'O':'Overcast',
              'R':'Rain',
               '*':'Snow',
               '! to *!!!!!*' : 'Weather advisory'
              }
for key in sorted(conditions):
   functions.show_on_lcd(key,conditions[key])
   sleep(1.5)
del conditions, key

try:
    
    while True:
            
        wlan.active(True)
        wlan.connect(params.WIFI_SSID, params.WIFI_PASSWORD)            
        while not wlan.isconnected():
            sleep(4)

        # call weather .gov for the weather report closest to the provided US long and lat
        tagsToKeep = ["start-valid-time", "temperature", "probability-of-precipitation", "cloud-amount"]
        xmlWeatherResponseLines = functions.limitedGetRequest(f"https://forecast.weather.gov/MapClick.php?lat={params.lat}&lon={params.long}&FcstType=digitalDWML", tagsToKeep, timeout=60)

        gc.collect()

        # Gather information about weather alerts
        # Define the varible used to show if there is a weather alert
        cautionAlertString = ""
        # Using the county code if provided from the paramters file to see if there are any weather alerts for the county
        if params.county_code != "":
                # https://api.weather.gov/alerts/active?point=41,-87
            tagsToKeep = ["cap:urgency", "cap:severity", "cap:certainty"]
            xmlWeatherAlerts = functions.limitedGetRequest(f"https://api.weather.gov/alerts/active.atom?zone={params.county_code}", tagsToKeep, timeout=60)
            
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

        gc.collect()

        # Extract the start time stamps -- these serve as indecies
        startTimeStamps = functions.getXMLValues("".join(functions.getXMLElements(xmlWeatherResponseLines, "start-valid-time")), valueTag="start-valid-time")
        gc.collect()
        # Extract the     hourly temp
        hourlyTemps = functions.getXMLValues(functions.getXMLElements(xmlWeatherResponseLines, "temperature", ["type"], ["hourly"])[0])
        gc.collect()
        # Extract probabilty of rain as a percent
        hourlyPrecipitation = functions.getXMLValues(functions.getXMLElements(xmlWeatherResponseLines, "probability-of-precipitation" )[0])
        gc.collect() 
        # Extract cloud coverage percent
        hourlyCloudAmount = functions.getXMLValues(functions.getXMLElements(xmlWeatherResponseLines, "cloud-amount")[0])

        del xmlWeatherResponseLines
        gc.collect()

        # Now we begin analyzing the retrived information
        # Getting the current time
        currentHour, minuteOfHour = functions.getCurrentTime(params.timezone_offset)
        
        gc.collect()

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
        functions.show_on_lcd(line1, forecastString)

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

        sleep(sleepTime)


except BaseException as e:
    print(e)
    functions.show_on_lcd(str(e)[:16], str(e)[16:32])
    from random import randint
    numb = randint(0,1000)
    raise
    #with open(f"_{numb}.txt","w") as file:
    #    file.write(str(dir()))
    #    file.write(str(e))


