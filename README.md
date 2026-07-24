# Nana's Scheduler

## Requirements
- Python 3.9 or newer must be installed on this computer
  Download from: https://www.python.org/downloads/
  During installation, CHECK the box that says "Add Python to PATH" — this is important

## How to run
1. Double-click `start.bat`
2. The first time, setup will take a minute while it installs dependencies
3. The scheduler will open in your browser automatically at http://127.0.0.1:5001
4. Do not close the black terminal window while using the scheduler — it is running the app

## How to use
- View Schedule: the home page shows the generated schedule
- Manage Employees: add/edit/remove employees, set availability and preferences
- Staffing Requirements: set how many staff are needed per hour at each location
- Print: click "Print Schedule" on the home page
- Export to Excel: click "Export to Excel" on the home page

## If the schedule says "no feasible schedule"
The page will explain exactly why and what to fix.

## Important
- Do NOT delete nana_scheduler.db — this file contains all your data
- Do NOT run seed.py — this will overwrite your data with test data
- If the browser does not open automatically, go to http://127.0.0.1:5001 manually
