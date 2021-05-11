# wazirx_client
A wazirx client written in PyQT5. 

## Features
- you can watch prices of crypto listed on wazirx, using their free json api.
- add favourites that persist
- can add alerts, though not notifications as of now, can use it as a filter
- double clicking on the crypto name will open its daily chart from yfinance.

## todo
- make a proper alerts language
- notifications
- alerts are not persistant, dies on restart of application, making it sort of worthless.
- table crashes on sorting using some tabs. 
- unoptimised code.

## working
- ```python3 client_wazirx```

### alerts:
- $ btc / r / > / 0.1 == alert if btc rate of change in past 24 hours is greater than 10 percent
- $ btc / p / > / 60000 == alert if btc price is more than that range.
- $ * / r / > / 0.1 == list all the crypto more than 10 percent rate of change in past 24 hours.

### add fav:
- write the name of crypto and click add.
- if it starts with "$", it will be taken as an alert.



