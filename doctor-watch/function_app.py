import azure.functions as func
import datetime
import json
import logging
import os
import requests
from bs4 import BeautifulSoup
import re
from azure.storage.blob import BlobServiceClient
from typing import List, Dict, Optional
import hashlib

app = func.FunctionApp()

class AppointmentMonitor:
    def __init__(self):
        self.target_url = os.getenv("TARGET_URL")
        self.doctor_name = os.getenv("DOCTOR_NAME", "Cornnie").lower()
        self.pushover_token = os.getenv("PUSHOVER_TOKEN")
        self.pushover_user = os.getenv("PUSHOVER_USER")
        self.storage_connection = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.pushover_url = "https://api.pushover.net/1/messages.json"
        
        # Date filtering - only notify for appointments before this date
        not_after_date_str = os.getenv("NOT_AFTER_DATE")
        self.not_after_date = None
        if not_after_date_str:
            try:
                self.not_after_date = datetime.datetime.strptime(not_after_date_str, "%Y-%m-%d").date()
                logging.info(f"Date filter set - only appointments before {self.not_after_date}")
            except ValueError:
                logging.warning(f"Invalid NOT_AFTER_DATE format: {not_after_date_str}. Use YYYY-MM-DD format.")
        
        # Container name for tracking sent notifications
        self.container_name = "appointment-notifications"
        
        # Heartbeat settings
        self.heartbeat_interval_hours = 12
        self.startup_heartbeat_sent = False
        
    def send_pushover_notification(self, message: str, title: str = "Doctor Appointment Available") -> bool:
        """Send notification via Pushover"""
        try:
            if not self.pushover_token or not self.pushover_user:
                logging.warning("Pushover credentials not configured")
                return False
                
            data = {
                "token": self.pushover_token,
                "user": self.pushover_user,
                "message": message,
                "title": title,
                "priority": 1,  # High priority for appointment notifications
                "sound": "magic"  # iOS notification sound
            }
            
            response = requests.post(self.pushover_url, data=data, timeout=10)
            
            if response.status_code == 200:
                logging.info("Pushover notification sent successfully")
                return True
            else:
                logging.error(f"Failed to send Pushover notification: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logging.error(f"Error sending Pushover notification: {str(e)}")
            return False
    
    def get_last_notification_hash(self) -> Optional[str]:
        """Get the hash of the last notification sent to avoid duplicates"""
        try:
            if not self.storage_connection:
                return None
                
            blob_service_client = BlobServiceClient.from_connection_string(self.storage_connection)
            container_client = blob_service_client.get_container_client(self.container_name)
            
            # Create container if it doesn't exist
            try:
                container_client.create_container()
            except Exception:
                pass  # Container might already exist
                
            blob_client = container_client.get_blob_client("last_notification.txt")
            
            try:
                blob_data = blob_client.download_blob().readall()
                return blob_data.decode('utf-8').strip()
            except Exception:
                return None  # Blob doesn't exist yet
                
        except Exception as e:
            logging.error(f"Error getting last notification hash: {str(e)}")
            return None
    
    def save_notification_hash(self, notification_hash: str) -> None:
        """Save the hash of the current notification to avoid duplicates"""
        try:
            if not self.storage_connection:
                return
                
            blob_service_client = BlobServiceClient.from_connection_string(self.storage_connection)
            container_client = blob_service_client.get_container_client(self.container_name)
            blob_client = container_client.get_blob_client("last_notification.txt")
            
            blob_client.upload_blob(notification_hash, overwrite=True)
            
        except Exception as e:
            logging.error(f"Error saving notification hash: {str(e)}")
    
    def get_last_heartbeat_time(self) -> Optional[datetime.datetime]:
        """Get the timestamp of the last heartbeat"""
        try:
            if not self.storage_connection:
                return None
                
            blob_service_client = BlobServiceClient.from_connection_string(self.storage_connection)
            container_client = blob_service_client.get_container_client(self.container_name)
            
            # Create container if it doesn't exist
            try:
                container_client.create_container()
            except Exception:
                pass  # Container might already exist
                
            blob_client = container_client.get_blob_client("last_heartbeat.txt")
            
            try:
                blob_data = blob_client.download_blob().readall()
                timestamp_str = blob_data.decode('utf-8').strip()
                return datetime.datetime.fromisoformat(timestamp_str)
            except Exception:
                return None  # Blob doesn't exist yet
                
        except Exception as e:
            logging.error(f"Error getting last heartbeat time: {str(e)}")
            return None
    
    def save_heartbeat_time(self, timestamp: datetime.datetime) -> None:
        """Save the timestamp of the current heartbeat"""
        try:
            if not self.storage_connection:
                return
                
            blob_service_client = BlobServiceClient.from_connection_string(self.storage_connection)
            container_client = blob_service_client.get_container_client(self.container_name)
            blob_client = container_client.get_blob_client("last_heartbeat.txt")
            
            timestamp_str = timestamp.isoformat()
            blob_client.upload_blob(timestamp_str, overwrite=True)
            
        except Exception as e:
            logging.error(f"Error saving heartbeat time: {str(e)}")
    
    def should_send_heartbeat(self) -> bool:
        """Check if it's time to send a heartbeat"""
        try:
            last_heartbeat = self.get_last_heartbeat_time()
            current_time = datetime.datetime.now(datetime.timezone.utc)
            
            # Send heartbeat if never sent before or if interval has passed
            if last_heartbeat is None:
                logging.info("No previous heartbeat found - sending startup heartbeat")
                return True
            
            # Convert last_heartbeat to UTC if it doesn't have timezone info
            if last_heartbeat.tzinfo is None:
                last_heartbeat = last_heartbeat.replace(tzinfo=datetime.timezone.utc)
            
            time_since_last = current_time - last_heartbeat
            hours_since_last = time_since_last.total_seconds() / 3600
            
            if hours_since_last >= self.heartbeat_interval_hours:
                logging.info(f"Time for heartbeat - {hours_since_last:.1f} hours since last")
                return True
            
            logging.info(f"No heartbeat needed - {hours_since_last:.1f} hours since last (interval: {self.heartbeat_interval_hours}h)")
            return False
            
        except Exception as e:
            logging.error(f"Error checking heartbeat timing: {str(e)}")
            return False
    
    def send_heartbeat(self) -> None:
        """Send a heartbeat notification to confirm the function is alive"""
        try:
            current_time = datetime.datetime.now(datetime.timezone.utc)
            
            # Determine if this is a startup or periodic heartbeat
            last_heartbeat = self.get_last_heartbeat_time()
            is_startup = last_heartbeat is None
            
            if is_startup:
                title = "Doctor Watch - Started"
                message = f"💚 Doctor appointment monitor is now active!\n\n" \
                         f"🔍 Monitoring: Dr. {self.doctor_name.title()}\n" \
                         f"⏰ Check interval: Every 5 minutes\n" \
                         f"💓 Heartbeat: Every {self.heartbeat_interval_hours} hours\n" \
                         f"📅 Started: {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n" \
                         f"🔗 Target: {self.target_url}"
            else:
                hours_since_last = (current_time - last_heartbeat.replace(tzinfo=datetime.timezone.utc)).total_seconds() / 3600
                title = "Doctor Watch - Heartbeat"
                message = f"💓 Doctor appointment monitor is still running!\n\n" \
                         f"🔍 Monitoring: Dr. {self.doctor_name.title()}\n" \
                         f"⏰ Last heartbeat: {hours_since_last:.1f} hours ago\n" \
                         f"📅 Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n" \
                         f"✅ System status: Active and monitoring"
            
            # Send heartbeat with lower priority than appointment alerts
            data = {
                "token": self.pushover_token,
                "user": self.pushover_user,
                "message": message,
                "title": title,
                "priority": 0,  # Normal priority for heartbeats
                "sound": "none" if not is_startup else "pushover"  # Silent for periodic, sound for startup
            }
            
            response = requests.post(self.pushover_url, data=data, timeout=10)
            
            if response.status_code == 200:
                self.save_heartbeat_time(current_time)
                heartbeat_type = "startup" if is_startup else "periodic"
                logging.info(f"Heartbeat sent successfully ({heartbeat_type})")
            else:
                logging.error(f"Failed to send heartbeat: {response.status_code} - {response.text}")
                
        except Exception as e:
            logging.error(f"Error sending heartbeat: {str(e)}")
    
    def parse_date_from_text(self, text: str) -> Optional[datetime.date]:
        """Parse date from text string"""
        try:
            # Common date patterns
            date_patterns = [
                r'(\w{6,9}),?\s*(\w{3,9})\s+(\d{1,2})',  # "Thursday, October 30" or "Thursday October 30"
                r'(\w{3,9})\s+(\d{1,2})',  # "October 30" or "Sep 4"
                r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})',  # "9/4/2025" or "04-09-2025"
                r'(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})',    # "2025-09-04"
            ]
            
            # Month mappings
            months = {
                'jan': 1, 'january': 1,
                'feb': 2, 'february': 2,
                'mar': 3, 'march': 3,
                'apr': 4, 'april': 4,
                'may': 5,
                'jun': 6, 'june': 6,
                'jul': 7, 'july': 7,
                'aug': 8, 'august': 8,
                'sep': 9, 'september': 9,
                'oct': 10, 'october': 10,
                'nov': 11, 'november': 11,
                'dec': 12, 'december': 12
            }
            
            # Day names for filtering out
            weekdays = {'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'}
            
            text_lower = text.lower()
            current_year = datetime.datetime.now().year
            
            for pattern in date_patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                for match in matches:
                    try:
                        if len(match) == 3:
                            if pattern == date_patterns[0]:  # "Thursday, October 30" pattern
                                weekday, month_name, day = match
                                if weekday.lower() in weekdays and month_name.lower() in months:
                                    month = months[month_name.lower()]
                                    day = int(day)
                                    # Assume current year, adjust if date is in the past
                                    year = current_year
                                    date_obj = datetime.date(year, month, day)
                                    if date_obj < datetime.date.today():
                                        date_obj = datetime.date(year + 1, month, day)
                                    return date_obj
                            
                            elif pattern == date_patterns[2]:  # MM/DD/YYYY or DD/MM/YYYY
                                month, day, year = match
                                year = int(year)
                                if year < 100:
                                    year += 2000
                                return datetime.date(year, int(month), int(day))
                            
                            elif pattern == date_patterns[3]:  # YYYY/MM/DD
                                year, month, day = match
                                return datetime.date(int(year), int(month), int(day))
                        
                        elif len(match) == 2:
                            if pattern == date_patterns[1]:  # "October 30" pattern
                                month_name, day = match
                                if month_name.lower() in months:
                                    month = months[month_name.lower()]
                                    day = int(day)
                                    # Assume current year, adjust if date is in the past
                                    year = current_year
                                    date_obj = datetime.date(year, month, day)
                                    if date_obj < datetime.date.today():
                                        date_obj = datetime.date(year + 1, month, day)
                                    return date_obj
                    
                    except (ValueError, TypeError) as e:
                        logging.debug(f"Error parsing date match {match}: {e}")
                        continue
            
            return None
        except Exception as e:
            logging.debug(f"Error parsing date from '{text}': {e}")
            return None
    
    def scrape_appointments(self) -> List[Dict]:
        """Scrape the appointment website for available slots for specific doctor"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(self.target_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            appointments = []
            
            logging.info(f"Searching for appointments with Dr. {self.doctor_name}")
            
            # Find all doctor sections (ocCadreByOptometrist)
            doctor_sections = soup.find_all('div', class_=re.compile(r'ocCadreByOptometrist', re.IGNORECASE))
            
            for section in doctor_sections:
                # Find the doctor image and name within this section
                doctor_img = section.find('img', attrs={'alt': re.compile(r'Dr\..*', re.IGNORECASE)})
                
                if not doctor_img:
                    logging.info("No doctor image found in section")
                    continue

                doctor_name = doctor_img.get('alt', '').strip()
                logging.info(f"Found doctor section: {doctor_name}")
                
                # Check if this is our target doctor (substring match, case-insensitive)
                if self.doctor_name not in doctor_name.lower():
                    logging.info(f"❌ Skipping {doctor_name} (not target doctor)")
                    continue

                logging.info(f"✅ Found target doctor: {doctor_name}")

                # We only want the first 'Next appointment' AFTER the image tag, within this same section.
                # Traverse the section's descendants in document order, starting after the image node.
                descendants = list(section.descendants)
                try:
                    start_idx = descendants.index(doctor_img)
                except ValueError:
                    start_idx = -1

                next_appointment_span = None
                for node in descendants[start_idx + 1:]:
                    # Restrict to tags
                    node_name = getattr(node, 'name', None)
                    if not node_name:
                        continue
                    # Stop if we somehow hit another doctor subsection (safety)
                    node_classes = (node.get('class') or []) if hasattr(node, 'get') else []
                    if node_name == 'div' and any('ocCadreByOptometrist' in cls for cls in map(str, node_classes)):
                        break
                    # Match the "Next appointment" span
                    if node_name == 'span' and any('ocMessageNextAppoiment' in cls for cls in map(str, node_classes)):
                        next_appointment_span = node
                        break

                if not next_appointment_span:
                    logging.info(f"No 'Next appointment' element found after image for {doctor_name}")
                    continue

                text = next_appointment_span.get_text(strip=True)
                text_clean = ' '.join(text.split())  # Normalize whitespace
                logging.info(f"Found appointment element for {doctor_name}: {text_clean}")

                # Parse "Next appointment: Wednesday, September 17" (or similar) format
                match = re.search(r'Next\s+appointment:\s*(.+)', text_clean, re.IGNORECASE)
                if not match:
                    logging.info("'Next appointment' text pattern not matched; skipping")
                    continue

                date_text = match.group(1).strip()
                appointment_date = self.parse_date_from_text(date_text)

                appointments.append({
                    'type': 'next_appointment',
                    'doctor': doctor_name,
                    'text': text_clean,
                    'raw_date': date_text,
                    'date': appointment_date.isoformat() if appointment_date else None,
                    'date_obj': appointment_date,
                    'context': f"Next available appointment for {doctor_name}: {date_text}"
                })
            
            if not appointments:
                logging.info("No appointments found")
            
            # Apply date filtering
            if self.not_after_date and appointments:
                filtered_appointments = []
                for apt in appointments:
                    apt_date = apt.get('date_obj')
                    if apt_date and apt_date <= self.not_after_date:
                        filtered_appointments.append(apt)
                        logging.info(f"Appointment on {apt_date} for {apt.get('doctor', 'Unknown')} is before cutoff - included")
                    elif apt_date and apt_date > self.not_after_date:
                        logging.info(f"Appointment on {apt_date} for {apt.get('doctor', 'Unknown')} is after cutoff - excluded")
                    elif not apt_date:
                        # If we can't parse the date, include it to be safe
                        filtered_appointments.append(apt)
                        logging.info(f"Appointment with unparseable date included")
                
                logging.info(f"Date filter applied: {len(appointments)} -> {len(filtered_appointments)} appointments")
                appointments = filtered_appointments
            
            # Remove duplicates
            unique_appointments = []
            seen_hashes = set()
            
            for apt in appointments:
                content_hash = hash(f"{apt.get('doctor', '')}{apt.get('text', '')}{apt.get('date', '')}")
                if content_hash not in seen_hashes:
                    seen_hashes.add(content_hash)
                    unique_appointments.append(apt)
            
            # Sort by date (earliest first)
            unique_appointments.sort(key=lambda x: x.get('date_obj') or datetime.date.max)
            
            logging.info(f"Found {len(unique_appointments)} unique appointments for Dr. {self.doctor_name}")
            for apt in unique_appointments:
                logging.info(f"  - {apt.get('type')}: {apt.get('doctor', 'Unknown')} ({apt.get('calendar_id', 'N/A')}) - {apt.get('text', 'N/A')[:50]} on {apt.get('date', 'unknown')}")
            
            return unique_appointments
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error while scraping appointments: {str(e)}")
            return []
        except Exception as e:
            logging.error(f"Error scraping appointments: {str(e)}")
            return []
    
    def check_for_appointments(self) -> None:
        """Main function to check for appointments and send notifications"""
        try:
            logging.info(f"Checking appointments for Dr. {self.doctor_name}")
            
            # Check if we should send a heartbeat
            if self.should_send_heartbeat():
                self.send_heartbeat()
            
            appointments = self.scrape_appointments()
            
            if not appointments:
                logging.info("No appointments found in the webpage")
                return
            
            # Create a hash of current appointments to avoid duplicate notifications
            # default=str ensures datetime/date objects (e.g., 'date_obj') serialize cleanly
            appointment_summary = json.dumps(appointments, sort_keys=True, default=str)
            # Use a stable hash across process restarts
            current_hash = hashlib.sha256(appointment_summary.encode("utf-8")).hexdigest()
            last_hash = self.get_last_notification_hash()
            
            if current_hash == last_hash:
                logging.info("No new appointments found since last check")
                return
            
            # Format notification message
            message_lines = [f"🏥 Appointment Alert for Dr. {self.doctor_name.title()}!"]
            
            if self.not_after_date:
                message_lines.append(f"📅 Appointments before: {self.not_after_date}")
            
            message_lines.append(f"\n✅ Found {len(appointments)} available appointment(s):\n")
            
            for i, apt in enumerate(appointments[:5], 1):  # Limit to first 5 results
                if apt.get('type') == 'next_appointment':
                    date_str = apt.get('raw_date', apt.get('date', 'Unknown date'))
                    message_lines.append(f"{i}. 📅 Next available: {date_str}")
                
                elif apt.get('type') == 'time_slot':
                    date_str = apt.get('date', 'Unknown date')
                    times_str = ', '.join(apt.get('times', []))
                    message_lines.append(f"{i}. ⏰ Time slot: {times_str} on {date_str}")
                
                else:
                    # Fallback
                    text = apt.get('text', apt.get('raw_date', 'Check website'))
                    message_lines.append(f"{i}. 📋 {text[:80]}")
            
            message_lines.append(f"\n🔗 Book now: {self.target_url}")
            message = '\n'.join(message_lines)
            
            # Send notification
            if self.send_pushover_notification(message):
                # Save hash to prevent duplicate notifications
                self.save_notification_hash(current_hash)
                logging.info(f"Notification sent for {len(appointments)} appointments")
            else:
                logging.error("Failed to send notification")
                
        except Exception as e:
            logging.error(f"Error in check_for_appointments: {str(e)}")


@app.timer_trigger(schedule="0 */5 * * * *", arg_name="myTimer", run_on_startup=False,
              use_monitor=False) 
def watch(myTimer: func.TimerRequest) -> None:
    """Azure Function timer trigger - runs every 5 minutes"""
    
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Doctor appointment monitor started')
    
    try:
        monitor = AppointmentMonitor()
        monitor.check_for_appointments()
        logging.info('Doctor appointment monitor completed successfully')
        
    except Exception as e:
        logging.error(f'Error in appointment monitor: {str(e)}')