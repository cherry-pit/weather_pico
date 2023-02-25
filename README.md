# weather_pico

![](https://user-images.githubusercontent.com/97217071/221383605-ea1f1f48-6270-4ca0-b4ba-6b4d759e79cf.jpg =250x250)

This is designed to run on a raspberry pico w and to display onto a 16x2 lcd display

It pulls data from 'https://forecast.weather.gov/MapClick.php?lat={lat}&lon={long}&FcstType=digitalDWML', is will only support US weather forecasts.

All temperatures are in fahrenheit

A script will run indefinitely and scrape the weather forecast every 30 minutes to present. Displayed is the following: current temp, 24 hr low, 24 hr high, and a 24 hr forecast that is shown in three hr increments.

Legend for 3 hr incremented forecast:

"C - Clear"<br>
"O - Overcast"<br>
"R - Rain"<br>
"* - Snow"

# How to use
Connect your 16x2 I2C display to your Raspi Pico W and write all files in this repo to your pico using Thonny.
Finally update the secrets.py on your pico accordingly and enjoy!

#
xmltok2.py source: https://github.com/pfalcon/pycopy-lib<br>
i2c_lcd.py source: https://github.com/dhylands/python_lcd/blob/master/lcd/i2c_lcd.py<br>
lcd_api.py source: https://github.com/dhylands/python_lcd/blob/master/lcd/lcd_api.py
