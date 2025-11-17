#!/usr/bin/python3

import functions
import parameters
import network
import time
import machine
import re
import gc
import ntptime

gc.enable()

print('Begin script...')

# Allocate our response buffer

responseBuffer = bytearray(110000)

try:
    #####################
    ## Connect to Wifi ##
    #####################
    
    class CannotConnectToWifi(Exception):
        def __init__(self, message="CannotConnectToWifi"):
            super().__init__(message)
            self.message = message

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(parameters.WIFI_SSID, parameters.WIFI_PASSWORD)         

    # Retry connecting to the wifi network for 1 minute
    maxWifiRetryCount = 6
    wifiRetryCount = 0
    while not wlan.isconnected():
        print(f'Trying to connect to wifi {wifiRetryCount} ...')
        if wifiRetryCount > maxWifiRetryCount:
            raise CannotConnectToWifi()    
        time.sleep(10)
        wifiRetryCount += 1

    print('Wifi Connection OK')

    del maxWifiRetryCount, wifiRetryCount

    ######################
    ## Get current time ##
    ######################

    ntptime.timeout = 30
    ntptime.host = "pool.ntp.org"
    settimeAttemptCount = 0
    settimeSuccessful = False
    while settimeAttemptCount < 10:
        try:
            settimeAttemptCount += 1
            ntptime.settime()
            settimeSuccessful = True
            print('Time set OK')
            break
        except:
            print('Time set FAILED')
            time.sleep(10)
            
    class NTPSetTimeFailed(Exception):
        def __init__(self, message="NTPSetTimeFailed"):
            super().__init__(message)
            self.message = message
    
    if not settimeSuccessful:
        raise NTPSetTimeFailed()

    ######################################
    ## Get weather alerts if applicable ##
    ######################################

    cautionAlertString = ""
    if parameters.county_code:

        class CannotGetWeatherAlerts(Exception):
            def __init__(self, message="CannotGetWeatherAlerts"):
                super().__init__(message)
                self.message = message

        header = {'User-Agent':'Weather Pico','Accept':'application/vnd.noaa.dwml+xml'}
        functions.clearBuffer(responseBuffer)
        responseLength = functions.getRequestWrapper(f"https://api.weather.gov/alerts/active.atom?zone={parameters.county_code}"
                                                , header
                                                , responseBuffer)
        print('API alert call OK')
        
        weatherAlertsDict = {}

        weatherAlertsDict['alertUrgencies'] = [x[0] for x in 
                                                functions.findAllValues(b'<entry',b'</entry>'
                                                                    , b'<cap:urgency>', b'</cap:urgency>'
                                                                    , responseBuffer, responseLength)]
        weatherAlertsDict['alertSeverities'] = [x[0] for x in 
                                                functions.findAllValues(b'<entry',b'</entry>'
                                                                    , b'<cap:severity>', b'</cap:severity>'
                                                                    , responseBuffer, responseLength)]
        weatherAlertsDict['alertCertainties'] = [x[0] for x in
                                                functions.findAllValues(b'<entry',b'</entry>'
                                                                        , b'<cap:certainty>', b'</cap:certainty>'
                                                                        , responseBuffer, responseLength)]

        del header

        class UnexpectedNWSAlertLayout(Exception):
            def __init__(self, message="UnexpectedNWSAlertLayout"):
                super().__init__(message)
                self.message = message

        if len(set([len(weatherAlertsDict[key]) for key in weatherAlertsDict])) > 1:
            raise UnexpectedNWSAlertLayout

        for n in range(len(weatherAlertsDict['alertUrgencies'])):
            urgency = weatherAlertsDict['alertUrgencies'][n].upper()
            severity = weatherAlertsDict['alertSeverities'][n].upper()
            certainty = weatherAlertsDict['alertCertainties'][n].upper()

            # Possible severities are "MINOR", "MODERATE", "SEVERE", "EXTREME"
            if "UNLIKELY" not in certainty and "PAST" not in urgency: # Check the the weather alert is valid to consider
                if "MINOR" in severity and len(cautionAlertString) < len("!"):
                    cautionAlertString = "!"
                elif "MODERATE" in severity and len(cautionAlertString) < len("!!"):
                    cautionAlertString = "!!"
                elif "SEVERE" in severity and len(cautionAlertString) < len("!!!"):
                    cautionAlertString = "!!!"
                elif "EXTREME" in severity and len(cautionAlertString) < len("*!!!!!*"):
                    cautionAlertString = "*!!!!!*"

            del n, urgency, severity, certainty

        del weatherAlertsDict

    #######################
    ## Perform API Calls ##
    #######################

    # Now we'll make our second call to get the actual forecast data using the grid and office information we found in our first call
    # We request XML data since the response footprint is smaller
    header = {'User-Agent':'Weather Pico','Accept':'application/vnd.noaa.dwml+xml'}
    functions.clearBuffer(responseBuffer)
    responseLength = functions.getRequestWrapper(f'https://api.weather.gov/gridpoints/{parameters.forecastOffice}/{parameters.gridX},{parameters.gridY}/forecast/hourly'
                                                ,header
                                                ,responseBuffer)
    print('Forecast API call OK')

    del header

    ########################
    ## Parse the forecast ##
    ########################

    class CannotGetNWSTimeLayout(Exception):
        def __init__(self, message="CannotGetNWSTimeLayout"):
            super().__init__(message)
            self.message = message

    forecastDict = {}

    forecastDict['starttimesList'] = functions.findAllValues(b'<time-layout',b'</time-layout>'
                                                            , b'<start-valid-time>', b'</start-valid-time>'
                                                            , responseBuffer, responseLength)[0]
    print('starttimesList OK')
    forecastDict['endtimesList'] = functions.findAllValues(b'<time-layout',b'</time-layout>'
                                                            , b'<end-valid-time>', b'</end-valid-time>'
                                                            , responseBuffer, responseLength)[0]
    print('endtimesList OK')
    forecastDict['temperatureList'] = functions.findAllValues(b'<temperature type=\"hourly\" units=\"Fahrenheit\" ',b'</temperature>'
                                                            , b'<value>', b'</value>'
                                                            , responseBuffer, responseLength)[0]
    print('temperatureList OK')
    forecastDict['precipitationList'] = functions.findAllValues(b'<probability-of-precipitation',b'</probability-of-precipitation>'
                                                            , b'<value>', b'</value>'
                                                            , responseBuffer, responseLength)[0]
    print('precipitationList OK')
    forecastDict['cloudList'] = functions.findAllValues(b'<cloud-amount',b'</cloud-amount>'
                                                            , b'<value>', b'</value>'
                                                            , responseBuffer, responseLength)[0]
    print('cloudList OK')
    #########################################
    ## Check if forecast periods are valid ##
    #########################################

    class UnexpectedForecastLayout(Exception):
        def __init__(self, message="UnexpectedForecastLayout"):
            super().__init__(message)
            self.message = message

    if len(set([len(forecastDict[key]) for key in forecastDict])) > 1:
        raise UnexpectedForecastLayout

    currentUTCEpoch = time.mktime(time.gmtime()) # Current UTC time as seconds from epoch
    endUTCEpoch = currentUTCEpoch + (24*3600) # Current UTC time plus 24 hours from now, we'll only look at the next 24 hours of weather forecast

    cosiderPeriodList = []
    for n in range(len(forecastDict['starttimesList'])):

        periodStartTime = forecastDict['starttimesList'][n]
        periodEndTime = forecastDict['endtimesList'][n]
        periodStartTime_epoch = functions.convertTimeStampToUTCEpoch(periodStartTime)
        periodEndTime_epoch = functions.convertTimeStampToUTCEpoch(periodEndTime)

        if periodEndTime_epoch >= endUTCEpoch: # Too late
            cosiderPeriodList.append(False)
        elif periodEndTime_epoch <= currentUTCEpoch: # Too early
            cosiderPeriodList.append(False)
        elif periodStartTime_epoch <= currentUTCEpoch: # Just right
            cosiderPeriodList.append(True)
        elif periodStartTime_epoch <= endUTCEpoch: # Just right
            cosiderPeriodList.append(True)
        else: # Catch all
            cosiderPeriodList.append(False)

        del n

    forecastDict['cosiderPeriodList'] = cosiderPeriodList

    del currentUTCEpoch, endUTCEpoch, cosiderPeriodList, periodStartTime, periodEndTime, periodStartTime_epoch, periodEndTime_epoch

    #####################################################
    ## Filter our forecasts to only include valid ones ##
    #####################################################

    hourlyTemps = []
    hourlyPrecipitation = []
    hourlyCloudAmount = []

    for period in range(len(forecastDict['cosiderPeriodList'])):
        considerPeriod = forecastDict['cosiderPeriodList'][period]
        if considerPeriod:
            hourlyTemps.append(int(forecastDict['temperatureList'][period]))
            hourlyPrecipitation.append(int(forecastDict['precipitationList'][period]))
            hourlyCloudAmount.append(int(forecastDict['cloudList'][period]))

        del period, considerPeriod

    del forecastDict

    print(hourlyTemps)
    print(hourlyPrecipitation)
    print(hourlyCloudAmount)
    print(cautionAlertString)

    #######################################################
    ## Create the forecast string that will be presented ##
    #######################################################

    currentHour = time.localtime(time.mktime(time.gmtime()) + (parameters.local_timezone_offset*3600))[3]
    print(currentHour)
    forecastList = []

    # Pull in indicies for the next 24 hours of data in steps of 3
    for n in range(0,24,3):
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

    functions.show_on_lcd(line1, forecastString)


    wlan.active(False)
    time.sleep(60*15)

    machine.soft_reset()

except Exception as e:
    print('Error:',e)
    functions.show_on_lcd(str(e)[:15], 'ERROR')
    time.sleep(60*10)
    machine.soft_reset()

