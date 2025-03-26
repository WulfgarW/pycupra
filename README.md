# PyCupra

Fork of https://github.com/Farfar/seatconnect which in turn is a fork of:
Fork of https://github.com/lendy007/skodaconnect which in turn is a fork of:
https://github.com/robinostlund/volkswagencarnet
A library to read and send vehicle data via Cupra/Seat portal using the same API calls as the MyCupra/MySeat mobile app.

## Information

Retrieve statistics about your Cupra (Seat) from the Cupra/Seat Connect online service

No licence, public domain, no guarantees, feel free to use for anything. Please contribute improvements/bugfixes etc.

## Breaking changes

## Thanks to

- [RobinostLund](https://github.com/robinostlund/volkswagencarnet) for initial project for Volkswagen Carnet I was able to fork
- [Farfar](https://github.com/Farfar) for modifications related to electric engines
- [tanelvakker](https://github.com/tanelvakker) for modifications related to correct SPIN handling for various actions and using correct URLs also for MY2021

### Example

For an extensive example, please use the code found in example/PyCupra.py.
When logged in the library will automatically create a vehicle object for every car registered to the account. Initially no data is fetched at all. Use the doLogin method and it will signin with the credentials used for the class constructor.
Method get_vehicles will fetch vehicle basic information and create Vehicle class objects for all associated vehicles in account.
To update all available data use the update_all method of the Connect class. This will call the update function for all registered vehicles, which in turn will fetch data from all available API endpoints.


