# In this script we will define functions used throughout the main script

###
### First we define functions
###

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
    return tuple([elements[i] for i in range(len(elements)) if i not in badElementIndicies])

def getXMLValues(xmlInput, valueTag="value"):
    
    # xmlInput - tuple or list
    # valueTag - string
    # provide an xml input and this function will return all the entries associated with value tags
    # this function will return a tuple of values
    # 
    # See the example below
    # '<cloud-amount type="total" units="percent" time-layout="k-p1h-n1-0"><value>71</value><value>75</value><value>84</value><value>88</value><value>91</value>...
    # If the above string is given as the xmlInput the below will be returned
    # ()'71','75','84','88','91')

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

    return tuple(values)

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

    from machine import I2C, Pin
    from lcd_api import LcdApi
    from i2c_lcd import I2cLcd

    I2C_ADDR     = 0x27
    I2C_NUM_ROWS = 2
    I2C_NUM_COLS = 16

    i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=200000)
    lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)
    lcd.putstr(f'{line1}\n{line2}')
