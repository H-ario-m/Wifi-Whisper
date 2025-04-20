#!/usr/bin/env python3
"""
Wi-Fi Whisperer Backend Server
A Flask-based backend that monitors Wi-Fi connections and serves the frontend
"""

import subprocess
import time
import json
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import sqlite3
import platform

class WiFiMonitor:
    def __init__(self):
        self.current_wifi = None
        self.session_start = None
        self.is_monitoring = False
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for session storage"""
        conn = sqlite3.connect('wifi_sessions.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location TEXT,
                wifi_name TEXT,
                start_time TEXT,
                end_time TEXT,
                duration INTEGER,
                productivity INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def get_current_wifi_windows(self):
        """Get current Wi-Fi network name on Windows"""
        try:
            wifi = subprocess.check_output(['netsh', 'WLAN', 'show', 'interfaces'], 
                                         shell=True, stderr=subprocess.DEVNULL)
            data = wifi.decode('utf-8', errors='ignore')
            for line in data.split('\n'):
                if 'SSID' in line and 'BSSID' not in line:
                    ssid = line.split(':')[1].strip()
                    if ssid and ssid != '':
                        return ssid
        except Exception as e:
            print(f"Error getting WiFi on Windows: {e}")
        return None
    
    def get_current_wifi_mac(self):
        """Get current Wi-Fi network name on macOS"""
        try:
            wifi = subprocess.check_output([
                '/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport',
                '-I'
            ], stderr=subprocess.DEVNULL)
            data = wifi.decode('utf-8')
            for line in data.split('\n'):
                if 'SSID:' in line:
                    return line.split('SSID:')[1].strip()
        except Exception as e:
            print(f"Error getting WiFi on macOS: {e}")
        return None
    
    def get_current_wifi_linux(self):
        """Get current Wi-Fi network name on Linux"""
        try:
            # Try iwgetid first
            wifi = subprocess.check_output(['iwgetid', '-r'], 
                                         stderr=subprocess.DEVNULL)
            return wifi.decode('utf-8').strip()
        except:
            try:
                # Fallback to nmcli
                wifi = subprocess.check_output(['nmcli', '-t', '-f', 'active,ssid', 'dev', 'wifi'], 
                                             stderr=subprocess.DEVNULL)
                for line in wifi.decode('utf-8').split('\n'):
                    if line.startswith('yes:'):
                        return line.split(':', 1)[1]
            except Exception as e:
                print(f"Error getting WiFi on Linux: {e}")
        return None
    
    def get_current_wifi(self):
        """Get current Wi-Fi network name (cross-platform)"""
        system = platform.system().lower()
        
        if system == 'windows':
            return self.get_current_wifi_windows()
        elif system == 'darwin':  # macOS
            return self.get_current_wifi_mac()
        elif system == 'linux':
            return self.get_current_wifi_linux()
        else:
            print(f"Unsupported operating system: {system}")
            return None
    
    def save_session(self, location, wifi_name, start_time, end_time, duration, productivity):
        """Save session to database"""
        conn = sqlite3.connect('wifi_sessions.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sessions (location, wifi_name, start_time, end_time, duration, productivity)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (location, wifi_name, start_time.isoformat(), 
              end_time.isoformat(), duration, productivity))
        conn.commit()
        conn.close()
    
    def get_sessions(self, days=30):
        """Get sessions from the last N days"""
        conn = sqlite3.connect('wifi_sessions.db')
        cursor = conn.cursor()
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute('''
            SELECT * FROM sessions 
            WHERE start_time > ? 
            ORDER BY start_time DESC
        ''', (cutoff_date,))
        sessions = cursor.fetchall()
        conn.close()
        
        return [{
            'id': s[0], 'location': s[1], 'wifi_name': s[2],
            'start_time': s[3], 'end_time': s[4], 'duration': s[5],
            'productivity': s[6], 'created_at': s[7]
        } for s in sessions]

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Initialize WiFi monitor
wifi_monitor = WiFiMonitor()

# Global variable to store current state
app_state = {
    'current_wifi': None,
    'session_active': False,
    'session_start': None,
    'current_location': None,
    'locations': []  # User-defined locations
}

def background_wifi_monitor():
    """Background thread to monitor Wi-Fi changes"""
    print("🔍 Starting Wi-Fi monitoring...")
    
    while True:
        try:
            current_wifi = wifi_monitor.get_current_wifi()
            
            # Only update if the Wi-Fi state has actually changed
            if current_wifi != app_state['current_wifi']:
                print(f"📶 Wi-Fi changed: {app_state['current_wifi']} → {current_wifi}")
                
                # End current session if active
                if app_state['session_active'] and app_state['session_start']:
                    end_session()
                
                app_state['current_wifi'] = current_wifi
                
                # Check if this WiFi matches any saved location
                if current_wifi:
                    matching_location = None
                    for location in app_state['locations']:
                        if current_wifi in location['wifi']:  # Check if Wi-Fi matches any in the list
                            matching_location = location
                            break
                    
                    if matching_location:
                        start_session(matching_location)
            
            time.sleep(5)  # Check every 5 seconds
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error getting WiFi: {e}")
            time.sleep(10)  # Wait longer on error
        except Exception as e:
            print(f"❌ Unexpected error in WiFi monitoring: {e}")
            time.sleep(10)  # Wait longer on error

def start_session(location):
    """Start a new productivity session"""
    app_state['session_active'] = True
    app_state['session_start'] = datetime.now()
    app_state['current_location'] = location
    print(f"🎯 Started session at: {location['name']}")

def end_session():
    """End the current session and save to database"""
    if app_state['session_active'] and app_state['session_start']:
        end_time = datetime.now()
        duration = int((end_time - app_state['session_start']).total_seconds())
        
        # Simulate productivity score (in real app, this would come from user input or other metrics)
        productivity = max(30, min(95, 60 + (duration // 60) % 40))  # Realistic range
        
        wifi_monitor.save_session(
            location=app_state['current_location']['name'],
            wifi_name=app_state['current_wifi'],
            start_time=app_state['session_start'],
            end_time=end_time,
            duration=duration,
            productivity=productivity
        )
        
        print(f"💾 Saved session: {duration}s at {app_state['current_location']['name']}")
        
        app_state['session_active'] = False
        app_state['session_start'] = None
        app_state['current_location'] = None

# API Routes
@app.route('/')
def index():
    """Serve the main application"""
    # Read the HTML file we created earlier
    try:
        with open('wifi_whisperer.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Inject the backend URL into the frontend
        html_content = html_content.replace(
            'simulateWifiDetection()', 
            'getRealWifiData()'
        )
        
        # Add the real WiFi detection function to the JavaScript
        js_injection = """
        <script>
        // Override the simulation with real backend calls
        WiFiWhisperer.prototype.simulateWifiDetection = function() {
            return fetch('/api/current-wifi')
                .then(response => response.json())
                .then(data => data.wifi)
                .catch(() => null);
        };
        
        WiFiWhisperer.prototype.startWifiMonitoring = function() {
            const checkWifi = async () => {
                try {
                    const response = await fetch('/api/status');
                    const data = await response.json();
                    this.handleWifiChange(data.current_wifi);
                    
                    // Update session info if active
                    if (data.session_active) {
                        document.getElementById('currentSession').style.display = 'block';
                        document.getElementById('currentLocation').textContent = data.current_location?.name || '';
                    } else {
                        document.getElementById('currentSession').style.display = 'none';
                    }
                } catch (error) {
                    console.error('Error fetching WiFi status:', error);
                }
            };
            
            // Check immediately, then every 3 seconds
            checkWifi();
            setInterval(checkWifi, 3000);
            
            // Update session timer
            setInterval(() => this.updateSessionTimer(), 1000);
        };
        
        // Override save methods to use backend
        WiFiWhisperer.prototype.saveLocations = function() {
            fetch('/api/locations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.locations)
            });
        };
        
        // Load real session data
        WiFiWhisperer.prototype.loadSessions = async function() {
            try {
                const response = await fetch('/api/sessions');
                this.sessions = await response.json();
                this.updateStats();
                this.updateCharts();
            } catch (error) {
                console.error('Error loading sessions:', error);
            }
        };
        
        // Load locations on init
        WiFiWhisperer.prototype.loadLocations = async function() {
            try {
                const response = await fetch('/api/locations');
                const locations = await response.json();
                if (locations.length > 0) {
                    this.locations = locations;
                }
            } catch (error) {
                console.error('Error loading locations:', error);
            }
        };
        
        // Override init to load real data
        const originalInit = WiFiWhisperer.prototype.init;
        WiFiWhisperer.prototype.init = async function() {
            await this.loadLocations();
            await this.loadSessions();
            originalInit.call(this);
        };
        </script>
        """
        
        html_content = html_content.replace('</body>', js_injection + '</body>')
        
        return html_content
    except FileNotFoundError:
        return """
        <h1>Wi-Fi Whisperer Backend is Running! 🚀</h1>
        <p>Please save the frontend HTML file as 'wifi_whisperer.html' in the same directory as this server.</p>
        <p>Backend API is available at:</p>
        <ul>
            <li><a href="/api/status">/api/status</a> - Current WiFi status</li>
            <li><a href="/api/sessions">/api/sessions</a> - Session history</li>
            <li><a href="/api/locations">/api/locations</a> - Saved locations</li>
        </ul>
        """

@app.route('/api/status')
def get_status():
    """Get current Wi-Fi and session status"""
    return jsonify({
        'current_wifi': app_state['current_wifi'],
        'session_active': app_state['session_active'],
        'session_start': app_state['session_start'].isoformat() if app_state['session_start'] else None,
        'current_location': app_state['current_location'],
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/current-wifi')
def get_current_wifi():
    """Get just the current Wi-Fi network name"""
    return jsonify({
        'wifi': app_state['current_wifi'],
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/sessions')
def get_sessions():
    """Get session history"""
    sessions = wifi_monitor.get_sessions()
    return jsonify(sessions)

@app.route('/api/locations', methods=['GET', 'POST'])
def handle_locations():
    """Get or save location configurations"""
    if request.method == 'GET':
        return jsonify(app_state['locations'])
    elif request.method == 'POST':
        app_state['locations'] = request.json
        # Ensure Wi-Fi is stored as a list for each location
        for location in app_state['locations']:
            if isinstance(location['wifi'], str):
                location['wifi'] = [location['wifi']]
        try:
            with open('locations.json', 'w') as f:
                json.dump(app_state['locations'], f, indent=2)
        except Exception as e:
            print(f"Error saving locations: {e}")
        return jsonify({'status': 'success'})

@app.route('/api/end-session', methods=['POST'])
def api_end_session():
    """Manually end current session"""
    if app_state['session_active']:
        end_session()
        return jsonify({'status': 'session_ended'})
    return jsonify({'status': 'no_active_session'})

def load_locations():
    """Load saved locations from file"""
    try:
        with open('locations.json', 'r') as f:
            app_state['locations'] = json.load(f)
        print(f"📍 Loaded {len(app_state['locations'])} saved locations")
    except FileNotFoundError:
        print("📍 No saved locations found, starting fresh")
    except Exception as e:
        print(f"❌ Error loading locations: {e}")

if __name__ == '__main__':
    print("🚀 Starting Wi-Fi Whisperer Backend Server...")
    print(f"💻 Detected OS: {platform.system()}")
    
    # Load saved locations
    load_locations()
    
    # Start background WiFi monitoring thread
    monitor_thread = threading.Thread(target=background_wifi_monitor, daemon=True)
    monitor_thread.start()
    
    print("🌐 Server starting on http://localhost:5000")
    print("📱 Open your browser and go to: http://localhost:5000")
    print("🔧 Press Ctrl+C to stop the server")
    
    # Start the Flask server
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
        if app_state['session_active']:
            print("💾 Saving current session...")
            end_session()