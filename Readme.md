# Wi-Fi Whisperer

Wi-Fi Whisperer is a productivity tracker that maps and remembers all Wi-Fi networks you've connected to. It visualizes time spent at each location (e.g., home, office, café) and draws productivity patterns based on the location.

## Features
- Detects Wi-Fi changes and associates them with predefined locations.
- Tracks productivity sessions based on Wi-Fi connections.
- Visualizes time distribution and productivity by location using charts.
- Allows users to configure multiple Wi-Fi networks for each location.

## Screenshots


## Getting Started

Follow these instructions to set up and run the project locally.

### Prerequisites
- Python 3.8 or higher
- Node.js (for frontend development, if needed)
- Git

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/H-ario-m/Wifi-Whisper.git
   cd wifi-whisperer
   ```

2. Install Python dependencies:
   ```bash
   pip install flask flask-cors
   ```

3. Create the SQLite database:
   ```bash
   python -c "import sqlite3; sqlite3.connect('wifi_sessions.db').close()"
   ```

4. (Optional) Install a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

---

## Running the Application

1. Start the backend server:
   ```bash
   python wifi_server.py
   ```

   The server will start at `http://localhost:5000`.

2. Open the frontend:
   - Open `wifi_whisperer.html` in your browser.

---

## Usage

1. **Add Locations**:
   - Use the "Add New Location" button to configure locations and associate Wi-Fi networks.

2. **Track Productivity**:
   - Connect to a saved Wi-Fi network to start tracking productivity automatically.

3. **View Charts**:
   - Check the time distribution and productivity charts for insights.

---

## Folder Structure

```
wifi-whisperer/
├── wifi_server.py          # Backend server
├── wifi_whisperer.html     # Frontend
├── README.md               # Documentation
├── screenshots/            # Screenshots for the README
└── wifi_sessions.db        # SQLite database (auto-created)
```

---

