# NeuroPark — Smart Urban Parking Management System

A smart parking system with event-driven, minimal-write architecture. Real-time occupancy tracking, intelligent rerouting, and a research-grade implementation for Scopus/SCI journal publication.

**Project:** CSP497 Final Year Capstone, Sharda University, Greater Noida  
**Team:** Shubham Modi (Data/CV/OCR), Shivam Kumar (Full-stack), Vamsi Beniwal (Backend)  
**Target:** Publication in IEEE Access or Expert Systems with Applications

---

## The Innovation

**Event-Driven Minimal-Write Architecture**

Traditional parking systems constantly poll sensors and update databases. NeuroPark updates the database **only on entry and exit events** — exactly 2 writes per vehicle visit, ever.

- Attendant uses PWA on phone → OCR reads number plate → generates QR ticket
- On exit, scan QR → fetch record → calculate price → update database
- Live occupancy maintained entirely in Redis (in-memory, sub-millisecond)
- Walk-in buffer reserves 30% of each lot for non-app users

This is the novel contribution for the research paper.

---

## Architecture

### Three Layers

```
┌─────────────────────────────────────────────┐
│           USER LAYER                        │
├──────────────────┬──────────────────────────┤
│  User App        │  Attendant PWA           │
│  (Map, Search,   │  (Camera OCR, QR        │
│   Rerouting)     │   Ticket)               │
└──────────────────┴──────────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│         BACKEND LAYER (FastAPI)             │
├──────────────────┬──────────────────────────┤
│  MongoDB         │  Redis                   │
│  (History)       │  (Live occupancy)       │
└──────────────────┴──────────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│      DETECTION LAYER (CV Services)          │
├──────────────────┬──────────────────────────┤
│  EasyOCR         │  QR Generation           │
│  (Plate reading) │  (Ticket encoding)      │
└──────────────────┴──────────────────────────┘
```

---

## Project Structure

```
neuropark/
├── backend/                          # FastAPI server
│   ├── main.py                       # Entry point
│   ├── config.py                     # Environment & configuration
│   ├── requirements.txt              # Python dependencies
│   ├── routes/
│   │   ├── vehicles.py               # Entry/exit endpoints
│   │   ├── lots.py                   # Lot management
│   │   └── users.py                  # User/guest auth
│   ├── models/
│   │   ├── vehicle.py                # Pydantic schemas
│   │   ├── lot.py
│   │   └── user.py
│   ├── services/
│   │   ├── ocr_service.py            # EasyOCR integration
│   │   ├── qr_service.py             # QR generation
│   │   ├── redis_service.py          # Live occupancy
│   │   └── routing_service.py        # Rerouting logic
│   └── websocket/
│       └── manager.py                # WebSocket connections
├── attendant-pwa/                    # React PWA for attendants
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── pages/
│       │   ├── EntryPage.jsx         # Camera + OCR
│       │   └── ExitPage.jsx          # QR scan + price
│       └── components/
│           ├── CameraOCR.jsx
│           ├── TicketGenerator.jsx
│           └── QRScanner.jsx
├── user-app/                         # React app for users
│   ├── package.json
│   └── src/
│       ├── App.jsx
│       ├── pages/
│       │   ├── HomePage.jsx          # Map view
│       │   └── SearchPage.jsx        # Search parking
│       └── components/
│           ├── MapView.jsx
│           ├── LotCard.jsx
│           └── RerouteAlert.jsx
├── .env                              # Environment variables (git-ignored)
├── .gitignore
└── README.md
```

---

## Setup

### Prerequisites

- Python 3.12+
- Node.js 16+
- Windows/Mac/Linux
- Antigravity IDE (recommended) or VS Code

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/neuropark.git
cd neuropark
```

### 2. Create Environment File

Create `.env` in root directory:

```env
MONGODB_URI=mongodb+srv://neuropark_user:PASSWORD@cluster0.mongodb.net/neuropark?retryWrites=true&w=majority
REDIS_URL=redis://default:PASSWORD@endpoint:port
GOOGLE_MAPS_API_KEY=your_api_key_here
SECRET_KEY=your_secret_key_here
```

**Get these values:**
- **MongoDB:** From MongoDB Atlas dashboard → Connect → Drivers → copy connection string
- **Redis:** From Redis Cloud dashboard → your database → copy endpoint + password
- **Google Maps:** From Google Cloud console → Credentials → API key
- **Secret Key:** Any random string for JWT (e.g., `neuropark_dev_secret_123`)

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Or (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run backend (port 8000)
python -m uvicorn main:app --reload
```

Backend will be available at `http://localhost:8000`

### 4. Attendant PWA Setup

```bash
cd attendant-pwa

# Install dependencies
npm install

# Run development server (port 5173)
npm run dev
```

Open `http://localhost:5173` on your phone (via your computer's IP) or desktop browser.

### 5. User App Setup

```bash
cd user-app

# Install dependencies
npm install

# Run development server (port 5174)
npm run dev
```

Open `http://localhost:5174`

---

## API Endpoints

### Vehicles

**POST /vehicles/entry**
- Body: `{ vehicle_number, lot_id, slot_id }`
- Response: `{ qr_token, entry_time }`
- Action: INSERT vehicle, increment Redis count, generate QR ticket

**POST /vehicles/exit**
- Body: `{ qr_token }`
- Response: `{ duration_minutes, amount_charged, vehicle_number }`
- Action: UPDATE vehicle record, decrement Redis count, calculate price

### Occupancy

**GET /lots/occupancy**
- Response: All lots with current occupancy from Redis
- `[ { lot_id, name, occupancy_count, capacity, occupancy_percent } ]`

**GET /lots/nearby?lat=X&lng=Y**
- Response: Lots sorted by distance from user coordinates
- Used by user app to show "nearest parking"

### OCR & QR

**POST /ocr/read-plate**
- Body: `image` file upload
- Response: `{ vehicle_number, confidence }`
- Action: Run EasyOCR on uploaded image

**POST /qr/generate**
- Body: `{ vehicle_id }`
- Response: QR code image (PNG)

### WebSocket

**WS /ws**
- Real-time occupancy updates pushed to connected clients
- Rerouting alerts sent when lot >80% full

---

## Database Schema

### MongoDB

**lots** collection:
```json
{
  "lot_id": "LOT001",
  "name": "Sector 63 Parking",
  "location": { "lat": 28.6139, "lng": 77.2090 },
  "total_capacity": 100,
  "walk_in_buffer": 0.30,
  "app_capacity": 70,
  "price_per_hour": 30,
  "address": "Sector 63, Noida"
}
```

**vehicles** collection:
```json
{
  "vehicle_number": "UP16AB1234",
  "lot_id": "LOT001",
  "slot_id": "A-12",
  "entry_time": "2024-01-15T09:00:00Z",
  "exit_time": "2024-01-15T15:00:00Z",
  "duration_minutes": 360,
  "amount_charged": 180,
  "status": "completed",
  "qr_token": "uuid-string"
}
```

**users** collection:
```json
{
  "name": "John Doe",
  "phone": "9876543210",
  "email": "john@example.com",
  "is_guest": false,
  "created_at": "2024-01-15T08:00:00Z"
}
```

### Redis

```
lot:LOT001:count = 47           # current occupancy
lot:LOT001:capacity = 100       # total capacity
user:user_id:location = {...}   # JSON: {lat, lng, destination}
```

---

## Features

### Attendant PWA

- **Entry:** Camera → OCR plate reading → auto-fill form → generate printable QR ticket
- **Exit:** Scan QR ticket → fetch entry record → calculate & show price → confirm exit
- **Mobile-first:** Works on Chrome Android, no app installation needed
- **Offline-aware:** Can work even if backend temporarily unavailable

### User App

- **Home:** Google Maps showing nearby parking lots with real-time occupancy
- **Search:** "Find parking near Indirapuram mall" → shows lots in area with prices
- **Rerouting:** When lot >80% full AND user >1km away → WebSocket alert suggests alternative
- **Guest mode:** Browse without login (temporary UUID session, 4-hour expiry)
- **Navigation:** One-click Google Maps directions to selected lot

### Backend

- **Real-time:** WebSocket push for live occupancy updates
- **Rerouting algorithm:** Smart suggestion based on occupancy threshold (80%) and distance (>1km)
- **Walk-in buffer:** Reserve 30% of each lot for non-app users
- **Error handling:** Explicit error messages for all failures
- **Logging:** Complete audit trail of all entry/exit events

---

## Rerouting Algorithm

```
IF lot_occupancy > 80% AND user_distance > 1km:
  FIND nearest alternative lot WITH occupancy < 70%
  PUSH WebSocket alert to user app WITH:
    - Current lot (name, occupancy %)
    - Suggested alternative (name, distance, occupancy %)
    - "Reroute?" button
ELSE:
  No rerouting needed
```

Walk-in buffer ensures app users never fill more than 70% of any lot.

---

## Testing

### Manual Testing Checklist

**Backend:**
- [ ] `python -m uvicorn main:app --reload` starts without errors
- [ ] POST `/ocr/read-plate` with test image returns vehicle number
- [ ] POST `/vehicles/entry` creates record and increments Redis count
- [ ] POST `/vehicles/exit` updates record and decrements Redis count
- [ ] GET `/lots/occupancy` returns all lots with current counts

**Attendant PWA:**
- [ ] Camera opens and captures image
- [ ] OCR reads plate and fills vehicle_number field
- [ ] QR ticket generates and displays
- [ ] QR scanner reads back the ticket
- [ ] Price calculation is correct

**User App:**
- [ ] Google Maps loads and shows lot pins
- [ ] Clicking lot shows details (name, occupancy, price)
- [ ] Search works and returns nearby lots
- [ ] WebSocket receives real-time occupancy updates
- [ ] Rerouting alert appears when lot >80% full

---

## Deployment (Week 7+)

### Heroku Deployment (Optional)

Backend:
```bash
heroku login
heroku create neuropark-backend
git push heroku main
heroku config:set MONGODB_URI=...
```

Frontend (Vercel):
```bash
npm install -g vercel
vercel
```

---

## Research Paper

**Novel Contribution:** Event-driven minimal-write architecture with walk-in demand buffer for parking management.

**Evaluation:** Synthetic data generated for 7 days across 2 lots with realistic Noida parking patterns (peak hours: 9-11am, 2-3pm, 6-8pm).

**Metrics:**
- Database write frequency (2 writes per vehicle vs 10+ for traditional systems)
- Occupancy accuracy (how well Redis stays synchronized with real data)
- Rerouting efficiency (user distance savings when rerouted)
- System latency (occupancy query response time)

**Target Journals:**
- IEEE Access (Scopus + SCI)
- Expert Systems with Applications (Scopus + SCI)
- Journal of Intelligent Transportation Systems (Scopus + SCI)

---

## Known Limitations

- **MVP scope:** No YOLOv8 automated detection yet (future enhancement)
- **Attendant workflow:** Assumes cooperative attendants (no anti-tampering in this version)
- **Synthetic data:** Paper evaluation uses generated data, not real-world parking patterns
- **Scale:** Tested for 2-3 lots; larger deployments may need database optimization

---

## Future Enhancements

1. **YOLOv8 integration:** Automated vehicle detection via CCTV at entry/exit gates
2. **Occupancy prediction:** ML model to forecast lot fill-rate (Prophet/LSTM)
3. **Dynamic pricing:** Adjust rates based on occupancy and demand
4. **Mobile app:** Native iOS/Android instead of PWA
5. **Payment integration:** Razorpay/Stripe for in-app checkout
6. **Operator dashboard:** Analytics and reporting for lot owners

---

## Contributing

This is a student capstone project. For queries or suggestions:
- Shubham Modi
- Shivam Kumar
- Vamsi Beniwal

---

## License

Educational use only. Not for commercial deployment without permission.

---

## Acknowledgments

- Literature survey: 8 relevant papers on smart parking systems (see paper)
- Inspiration: Greater Noida parking challenges and student mobility needs
- Technology: MongoDB Atlas, Redis Cloud, Google Cloud, FastAPI, React community

---

