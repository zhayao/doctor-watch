# Doctor Appointment Monitor

An Azure Function that monitors appointment availability for Dr. Cornnie at Marpole Optometry Clinic and sends iOS notifications via Pushover when slots become available.

## Features

- ⏰ Runs every 5 minutes to check for appointment availability
- 🔍 Intelligently scrapes the appointment booking website
- 📱 Sends iOS notifications via Pushover with high priority
- 🚫 Prevents duplicate notifications using Azure Blob Storage
- 📝 Comprehensive logging for troubleshooting
- ⚡ Robust error handling and retry logic

## Configuration

### 1. Pushover Configuration

## Quick Setup

For a completely automated setup, run:

```bash
./setup.sh
```

Then activate the development environment:

```bash
source activate.sh
```

## Project Structure

```
doctor-watch/
├── README.md                    # This file
├── setup.sh                     # Automated setup script
├── activate.sh                  # Development environment activation
├── deploy.sh                    # Azure deployment script
├── test_monitor.py             # Local testing script
├── requirements-dev.txt        # Development dependencies
├── .env.example               # Environment template
├── .gitignore                # Git ignore file
├── venv/                     # Python virtual environment
├── config/
│   └── local.settings.json   # Local Azure Function settings
└── doctor-watch/             # Azure Function code
    ├── function_app.py       # Main function code
    ├── requirements.txt      # Production dependencies
    └── host.json            # Azure Function configuration
```

1. Sign up for [Pushover](https://pushover.net/)
2. Create a new application to get your app token
3. Note your user key from the dashboard

### 2. Environment Variables

Update the values in `config/local.settings.json`:

```json
{
  "Values": {
    "TARGET_URL": "https://booking.opto.com/5d71635fb4fd7/marpole-optometry-clinic/schedules/87545935-0F15-4210-8F45-CDDC6C7F2395/",
    "DOCTOR_NAME": "Cornnie",
    "PUSHOVER_TOKEN": "your_actual_pushover_app_token",
    "PUSHOVER_USER": "your_actual_pushover_user_key",
    "AZURE_STORAGE_CONNECTION_STRING": "your_storage_connection_string"
  }
}
```

### 3. Local Development

1. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   # Production dependencies
   pip install -r doctor-watch/requirements.txt
   
   # Development dependencies (for testing)
   pip install -r requirements-dev.txt
   ```

3. Install Azure Functions Core Tools:
   ```bash
   npm install -g azure-functions-core-tools@4 --unsafe-perm true
   ```

4. Create environment file:
   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials
   ```

5. Test the setup:
   ```bash
   python test_monitor.py
   ```

6. Run locally:
   ```bash
   cd doctor-watch
   func start
   ```

### 4. Azure Deployment

1. Create an Azure Function App:
   ```bash
   az functionapp create \
     --resource-group your-resource-group \
     --consumption-plan-location eastus \
     --runtime python \
     --runtime-version 3.11 \
     --functions-version 4 \
     --os-type Linux \
     --name doctor-watch-function \
     --storage-account your-storage-account
   ```

2. Deploy the function:
   ```bash
   func azure functionapp publish doctor-watch-function --publish-local-settings --python
   ```

3. Set environment variables in Azure:
   ```bash
   az functionapp config appsettings set \
     --name doctor-watch-function \
     --resource-group your-resource-group \
     --settings \
     "TARGET_URL=https://booking.opto.com/5d71635fb4fd7/marpole-optometry-clinic/schedules/87545935-0F15-4210-8F45-CDDC6C7F2395/" \
     "DOCTOR_NAME=Cornnie" \
     "PUSHOVER_TOKEN=your_token" \
     "PUSHOVER_USER=your_user_key" \
     "AZURE_STORAGE_CONNECTION_STRING=your_connection_string"
   ```

## How It Works

1. **Timer Trigger**: The function runs every 5 minutes (configurable in the cron expression)

2. **Web Scraping**: Uses BeautifulSoup to parse the appointment booking website looking for:
   - Doctor name mentions
   - Available appointment slots
   - Clickable booking elements
   - Availability indicators

3. **Duplicate Prevention**: Creates a hash of found appointments and compares with the last notification to avoid spam

4. **Notification**: Sends formatted messages to iOS via Pushover with:
   - High priority for immediate delivery
   - Custom sound
   - Direct booking link
   - Summary of available slots

## Monitoring

- Check Azure Function logs for execution details
- Pushover provides delivery confirmation
- Function runs every 5 minutes automatically

## Customization

### Change Check Frequency

Edit the cron expression in `function_app.py`:

```python
@app.timer_trigger(schedule="0 */5 * * * *", ...)  # Every 5 minutes
@app.timer_trigger(schedule="0 */2 * * * *", ...)  # Every 2 minutes
@app.timer_trigger(schedule="0 */10 * * * *", ...) # Every 10 minutes
```

### Monitor Different Doctor

Update the `DOCTOR_NAME` environment variable to match the doctor you want to monitor.

### Different Website

Update the `TARGET_URL` environment variable and potentially adjust the scraping logic in the `scrape_appointments` method.

## Troubleshooting

1. **No notifications received**: Check Pushover credentials and test with a manual API call
2. **Function not running**: Verify the timer trigger cron expression and Azure Function app status
3. **Website changes**: The scraping logic may need updates if the website structure changes
4. **Storage errors**: Ensure the Azure Storage connection string is correct

## Cost Estimation

- Azure Function (Consumption Plan): ~$0.20-0.40/month for 5-minute intervals
- Azure Storage: ~$0.05/month for notification tracking
- Pushover: Free for 10,000 notifications/month

Total estimated cost: Under $1/month
