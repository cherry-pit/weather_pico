#!/usr/bin/python3

from urequests import get
from time import localtime, sleep

from xmltok2 import tokenize

from machine import reset
from machine import I2C
from lcd_api import LcdApi
from i2c_lcd import I2cLcd

### Change lat and Long information to where weather should be reported for
#
lat, long =  lat, long
#
###

def show_on_lcd(line1,line2):
    I2C_ADDR     = 0x27
    I2C_NUM_ROWS = 2
    I2C_NUM_COLS = 16

    i2c = I2C(0, sda=machine.Pin(0), scl=machine.Pin(1), freq=200000)
    lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)
    lcd.putstr(f'{line1}\n{line2}')

###

def getCurrentTime():
    
    # the tabular weather that we are scraping deletes outdated data 15 mins after the house
    # this is a workaround to check the time and to update the forecast faster than 15 mins after the hour
    # this can break easily and one should change the time.gov link according to their timezone

    ###

    try:
        url = f'https://timeapi.io/api/Time/current/coordinate?latitude={lat}&longitude={long}'
        user_agent = {'User-agent': 'Mozilla/5.0'}

        resp = get(url, headers = user_agent).json()
        
        return resp['hour'], resp['minute'] # adjusted for chicago time
            # returns hour of day and minute of day
    
    except:
        
        print('error with time.gov scrape')
        return -1, -1

###

def getWeather():

    currentHour = getCurrentTime()[0]
    
    url = f'https://forecast.weather.gov/MapClick.php?lat={lat}&lon={long}&FcstType=digitalDWML'
    user_agent = {'User-agent': 'Mozilla/5.0'}
    resp = get(url, headers = user_agent)

    f = open('_.xml', 'wb')
    f.write(resp.content)
    f.close()

    RawTimestamps = []
    RawTemps = []
    RawProbabilityPrecipitation = []
    RawCloudCoverage = []

    recordRawTimestamps = False
    recordRawTemps = False
    recordRawProbabilityPrecipitation = False
    recordRawCloudCoverage = False
    for n in tokenize(open('_.xml')):

        if n[0] == 'START_TAG' and n[2] == 'start-valid-time':
            recordRawTimestamps = True
        elif n[0] == 'END_TAG' and n[2] == 'start-valid-time':
            recordRawTimestamps = False

        elif n[0] == 'START_TAG' and n[2] == 'temperature':
            recordRawTemps = True
        elif n[0] == 'END_TAG' and n[2] == 'temperature':
            recordRawTemps = False

        if n[0] == 'ATTR' and n[2] == 'type' and n[3] != 'hourly':
            recordRawTemps = False

        elif n[0] == 'START_TAG' and n[2] == 'probability-of-precipitation':
            recordRawProbabilityPrecipitation = True
        elif n[0] == 'END_TAG' and n[2] == 'probability-of-precipitation':
            recordRawProbabilityPrecipitation = False

        elif n[0] == 'START_TAG' and n[2] == 'cloud-amount':
            recordRawCloudCoverage = True
        elif n[0] == 'END_TAG' and n[2] == 'cloud-amount':
            recordRawCloudCoverage = False        

        if recordRawTimestamps and n[0] == 'TEXT':
            RawTimestamps.append(n[1])

        elif recordRawTemps and n[0] == 'TEXT':
            RawTemps.append(int(n[1]))

        elif recordRawProbabilityPrecipitation and n[0] == 'TEXT':
            RawProbabilityPrecipitation.append(int(n[1])        )

        elif recordRawCloudCoverage and n[0] == 'TEXT':
            RawCloudCoverage.append(int(n[1]))

    offset = 0
    if currentHour != -1:
        hourOfFirstTimestamp = int(RawTimestamps[0][11:13])
        if currentHour != hourOfFirstTimestamp:
            offset = 1            
            
    # here we incorperate the workaround for outdated data not being deleted by weather.gov until 15 mins after the hour
    if offset > 0:
        RawTimestamps = RawTimestamps[offset:]
        RawTemps = RawTemps[offset:]
        RawProbabilityPrecipitation = RawProbabilityPrecipitation[offset:]
        RawCloudCoverage = RawCloudCoverage[offset:]

    tempList = []
    forecastList = []
    for n in range(0,len(RawTimestamps[:24]),3):
        median_temp = sorted(RawTemps[n:n+3])[1]
        probaility_of_rain = max(RawProbabilityPrecipitation[n:n+3])
        median_cloud_coverage = sorted(RawCloudCoverage[n:n+3])[1]

        weather_letter = 'O'

        if median_temp > 32 and probaility_of_rain >= 33:
            weather_letter = 'R' # rain
        elif median_temp <= 32 and probaility_of_rain > 33:
            weather_letter = '*' # snow
        elif median_cloud_coverage <= 80 and probaility_of_rain < 33:
            weather_letter = 'C' # Sunny    

        tempList.append(median_temp)
        forecastList.append(weather_letter)

    minTemp = min(RawTemps[:24])
    maxTemp = max(RawTemps[:24])
    currentTemp = RawTemps[0]

    month = int(RawTimestamps[0][5:7])
    day = int(RawTimestamps[0][8:10])
    currentDate = f'{month}/{day}'
                
    
    daySplitIndex = round( ( 24 - currentHour ) / 3 )
    forecastString = ' '.join(forecastList[:daySplitIndex]) + '|' + ' '.join(forecastList[daySplitIndex:])

    return currentTemp, currentDate, minTemp, maxTemp, forecastString

###

show_on_lcd('starting...','')
sleep(1.5)

conditions = {'C':'Clear',
              'O':'Overcast',
              'R':'Rain',
               '*':'Snow'}

for key in sorted(conditions):
   show_on_lcd(key,conditions[key])
   sleep(2)

show_on_lcd('| splits today','and tomorrow')
sleep(2)
   
del conditions

loop_count = 0

try:
    while True:
        
        
        
        retry_count = 0
        line1 = 'error'
        line2 = 'error'
        
        while retry_count < 5:
            
            print('starting')
            weather = getWeather()
            current_temp = str(weather[0])
            current_date = weather[1]
            min_temp = str(weather[2])
            max_temp = str(weather[3])
            forecast = weather[4]

            temp_range = f'{min_temp},{max_temp}'

            while len(current_temp) < 3:
                current_temp += ' '  
            while len(temp_range) < 7:
                temp_range = ' ' + temp_range   

            line1 = f'{current_temp}      {temp_range}'
            line2 = f'{forecast}'

            retry_count = 6
        
        
        show_on_lcd(line1,line2)
        
        minuteOfHour = getCurrentTime()[1]
        sleepTime = 60*10
        if minuteOfHour != -1: # if the function ran with no errors

            deltaFrom5 = 5 - minuteOfHour
            deltaFrom35 = 35 - minuteOfHour

            if minuteOfHour < 5:
                sleepTime = ( deltaFrom5 ) * 60

            if minuteOfHour > 5 and minuteOfHour < 35:
                sleepTime = ( deltaFrom35 ) * 60

            if minuteOfHour > 35:
                sleepTime = ( 5 + (60 - minuteOfHour) ) * 60

            if minuteOfHour == 5 or minuteOfHour == 35:
                sleepTime = 0
                
            del deltaFrom5, deltaFrom35
  

        del minuteOfHour
        
        sleep(sleepTime)
        
        del sleepTime
        
        if loop_count > 144: # reset the pico every 3 days because of memory leaks and to clean up the environment
            loop_count = 0
            machine.reset()
        else:
            loop_count += 1
except:
    machine.reset()
