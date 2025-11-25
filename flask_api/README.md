# SNEP Analytics API

A lightweight Flask API to query historical data from the SNEP Top Singles (2020-2026). This API allows analyzing the performance of artists and producers.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Dependencies listed in `requirements.txt` (including `flask`, `flask-cors`, `psycopg2-binary`, `python-dotenv`).

### Installation
1. Ensure you are at the project root.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Launch
```bash
python flask_api/app.py
```
The API will be accessible at `http://localhost:5001`.

---

## 📡 Endpoints

### 1. Search for an Artist or Producer
Retrieves statistics, list of songs, and rankings.

**URL**: `/api/artist/<name>`
**Method**: `GET`
**Parameters**:
- `type` (optional): `artist` (default) or `producer`.

**Examples**:
- **Artist**:
  ```bash
  curl "http://localhost:5001/api/artist/Jul"
  ```
- **Producer**:
  ```bash
  curl "http://localhost:5001/api/artist/Maximum%20Beats?type=producer"
  ```

### 2. Privacy Policy (GDPR)
Displays information about data processing and user rights.

**URL**: `/api/privacy`
**Method**: `GET`

### 3. Data Export (Portability)
Dedicated endpoint for the full export of an entity's data.

**URL**: `/api/gdpr/export/<name>`
**Method**: `GET`

---

## 🛡️ GDPR Compliance

This API has been designed in compliance with the General Data Protection Regulation (GDPR).

### 1. Transparency and Right to be Informed
The `/api/privacy` endpoint provides a clear statement on:
- The nature of collected data (public music chart data).
- The purpose of processing (statistical analysis).
- The contact details of the data controller.

### 2. Right of Access
Any user can freely access stored data regarding an artist or producer via the search endpoints.

### 3. Right to Data Portability
The `/api/gdpr/export/<name>` endpoint allows retrieving all data associated with a person (artist or producer) in a structured, machine-readable format (JSON), facilitating its transfer.

### 4. Data Minimization
The API returns only information strictly necessary for music analysis (Title, Ranking, Weeks). No sensitive data (private life, contact details, etc.) is processed or exposed.

### 5. Right to Erasure and Rectification
As indicated in the privacy policy, requests for data deletion or rectification must be addressed to the administrator (see `/api/privacy`). Since the API is a read-only interface, modifications are performed at the database level by the DPO.

### 6. Security
- The API operates in read-only mode on the database.
- Database credentials are managed via environment variables (`.env`) and are never exposed in the code.
