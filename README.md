# plugin-api-otel
A RESTful API for dynamically managing **OpenTelemetry Collector** configurations in Kubernetes environments.  
Enables central control over pipelines via HTTP, including configuration updates, deletions, and live reloads.

---

## 📦 Features

- API endpoints to:
  - Create or replace configurations (`POST`)
  - Update specific processors (`PUT`)
  - Remove parts of the pipeline (`DELETE`)
  - Trigger live reload in the OpenTelemetry pod (`POST /reload`)
- Designed for Kubernetes clusters
- DEBUG mode support for testing without persistence
- Fully tested with `pytest`

---

## 🚀 Installation

```bash
# Clone the repository
git clone https://ants-gitlab.inf.um.es/telemetry/plugin-api-otel.git
cd plugin-api-otel

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🧪 Running Tests

To run the full test suite:

```bash
cd plugin-api-otel

# Run tests
pytest
```

---

## 🧰 Basic Usage

Run the development server:

```bash
uvicorn agent:app --host 0.0.0.0 --port 8000
```

Visit the interactive Swagger docs:

- [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📡 API Endpoints

| Method | Endpoint           | Description                                   |
|--------|--------------------|-----------------------------------------------|
| PUT    | `/configurations`  | Update parts of the pipeline                  |
| POST   | `/configurations`  | Create or replace full configuration          |
| DELETE | `/configurations`  | Delete specific pipeline elements             |
| POST   | `/reload`          | Reload OpenTelemetry Collector via `kubectl debug` and `SIGHUP`  |

---

## 📁 Project Structure

```
plugin-api-otel/
├── agent.py                # Main FastAPI application
├── Dockerfile              # Container definition
├── helm/
├── k8s/
│   ├── deployment.yaml     # Kubernetes agent-api deployment manifest
│   └── service.yaml        # Kubernetes agent-api service definition
├── requirements.txt        # Python dependencies
├── test/                   # Test suite
│   ├── curl/               # Example curl commands
│   ├── template.yaml       # Test ConfigMap template
│   ├── test_configurations.py  # Unit tests for /configurations endpoints (PUT, POST, DELETE)
│   └── test_reload.py          # Unit tests for /reload endpoint with mocked k8s operations
└── README.md
```

---

## ✅ Requirements

- Python 3.11 or newer
- Kubernetes environment with `kubectl` access
- Sufficient privileges to execute `kubectl debug`

---

## 🤝 Contributing

Contributions are welcome!

1. Create a new branch:  
   `git checkout -b feature-branch`
2. Commit your changes:  
   `git commit -m 'Clear description of your change'`
3. Push to remote:  
   `git push origin feature-branch`
4. Open a Merge Request in GitLab

---

## 👥 Authors

**José Manuel Bernabé Murcia**  
**José Luis Sánchez Fernández**  
University of Murcia