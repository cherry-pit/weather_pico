# weather_pico

This is designed to run on a raspberry pico w and to display onto a 16x2 lcd display

It pulls data from 'https://forecast.weather.gov/MapClick.php?lat={lat}&lon={long}&FcstType=digitalDWML', is will only support US weather forecasts.

A script will run indefinitely and scrape the weather forecast every 30 minutes to present. Displayed is the following: current temp (F), 24 hr low, 24 hr high, and a 24 hr forecast that is shown in three hr increments.

Legend for 3 hr incremented forecast:

"C - Clear"<br>
"O - Overcast"<br>
"R - Rain"<br>
"* - Snow"
