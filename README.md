# GlucoTop

A lightweight Windows desktop widget that displays your current Dexcom glucose reading directly on the desktop.

The widget stays fixed in the bottom-right corner and automatically refreshes the glucose value every 5 minutes.

## Features

* Current Dexcom glucose value
* Supports `mg/dL` and `mmol/L`
* Glucose trend arrow
* Reading age displayed above the glucose value
* Color-coded glucose levels
* Stale reading detection
* Automatic refresh every 5 minutes
* Fixed bottom-right desktop position
* Remains visible when using `Win + D`
* Right-click context menu
* Change glucose unit at any time
* Lightweight and unobtrusive

## Requirements

* Windows 10 or Windows 11
* Python 3.12 or newer
* A Dexcom account with access to glucose data

## Installation

Clone the repository:

```powershell
git clone https://github.com/YOUR_USERNAME/GlucoTop.git
cd GlucoTop
```

Create a virtual environment:

```powershell
py -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\activate
```

Install the dependencies:

```powershell
py -m pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project directory.

You can use `.env.example` as a template:

```powershell
copy .env.example .env
```

Then edit `.env`:

```env
DEXCOM_USERNAME=your_dexcom_email
DEXCOM_PASSWORD=your_dexcom_password
DEXCOM_REGION=ous
```

**Never commit your `.env` file to GitHub.**

The `.gitignore` file is configured to exclude it from the repository.

## Run

With the virtual environment activated:

```powershell
py widget.py
```

On the first launch, GlucoTop asks you to choose your preferred glucose unit.

Your choice is stored locally in `config.json`.

## Context Menu

Right-click GlucoTop to access:

* **Change unit**
* **Refresh now**
* **Exit**

## Glucose Colors

The widget uses the following thresholds:

| Glucose         | Display |
| --------------- | ------- |
| Below 70 mg/dL  | Red     |
| 70–180 mg/dL    | Green   |
| Above 180 mg/dL | Yellow  |
| Stale reading   | Orange  |

Glucose thresholds are always evaluated using mg/dL, regardless of the selected display unit.

## Reading Age

GlucoTop displays how old the current Dexcom reading is.

Example:

```text
just now
105 mg/dL
→
```

or:

```text
7 min ago
105 mg/dL
→
```

Older readings are visually highlighted so you can immediately see when the displayed value may not be recent.

## Project Structure

```text
GlucoTop/
│
├── widget.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
│
└── .venv/
```

Local files that contain user-specific information are intentionally excluded from Git:

```text
.env
config.json
widget.lock
.venv/
```

## Disclaimer

GlucoTop is an unofficial desktop utility and is not affiliated with or endorsed by Dexcom.

It is intended for informational and personal-use purposes only.

Do not use GlucoTop as a replacement for the official Dexcom application, receiver, or other medical device.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
