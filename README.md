# 🔐 Anti-Theft Alert & Family Notification System

> A smart alert system that notifies your trusted contacts (family or friends) when your phone is **stolen, tampered with, or experiences failed PIN attempts** — using **Python Flask**, **Firebase**, and **Twilio**.

---

## 🚀 Project Overview

When a smartphone is stolen or tampered with, the owner often doesn’t realize it immediately.  
This system bridges that gap — it instantly sends alerts via **push notification**, **SMS**, and optionally **Home Assistant automation** to your trusted contacts.

The system includes:
- A **Python Flask backend** that receives alerts from the user’s mobile app.  
- **Firebase Cloud Messaging (FCM)** for push notifications.  
- **Twilio SMS API** for text alerts.  
- Optional **Home Assistant webhook** to trigger smart-home responses (like lights or speaker alerts).  
- A simple **frontend prototype** (`anti-theft-prototype.html`) for demo or manual testing.

---

## 🧠 Problem Statement

Most users rely only on "Find My Device" after realizing their phone is missing — often too late.  
There is no instant alert to family or friends when theft or tampering first occurs.

### 🧩 Solution
- Detect theft/tamper events via a mobile app.  
- Send the event data to a Flask API.  
- The server instantly notifies trusted contacts through:
  - Push Notifications (Firebase)
  - SMS (Twilio)
  - Optional: IoT triggers via Home Assistant

---

## ⚙️ Features

| Feature | Description |
|----------|-------------|
| 🔔 **Instant Alerts** | Sends push notifications and SMS immediately to all trusted contacts. |
| 📱 **Multi-channel Communication** | Push via Firebase and SMS via Twilio. |
| 🧍‍♂️ **Trusted Contacts** | Add multiple contacts (family/friends) to receive alerts. |
| 🧩 **Tamper Detection Support** | Detect SIM change or repeated failed unlocks (handled on mobile app). |
| 🏠 **Home Assistant Integration** | Triggers smart lights, cameras, or speakers on alert. |
| 🌐 **Web UI (Prototype)** | Simple demo interface included for local testing. |
| 🧰 **Configurable via .env** | Store all credentials securely in environment variables. |

---
💡 Possible Future Upgrades

GPS tracking & map visualization

AI detection of suspicious motion or faces

Multi-device dashboard (family network)

Integration with Apple/Google “Find My” APIs

Support for wearables (smartwatch alert button)
## 🏗️ System Architecture

```text
+--------------------+
|  Android App       |
| (detects event)    |
+---------+----------+
          |
          v
   POST /api/alert
          |
+---------+----------+
| Flask API Server   |
| (Python backend)   |
+---------+----------+
  |           |         \
  v           v          v
Firebase   Twilio     Home Assistant
(Push)     (SMS)      (Webhook trigger)
