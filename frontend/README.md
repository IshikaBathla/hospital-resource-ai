# AI Hospital Resource Coordination System

An AI-assisted hospital operations platform that simulates resource allocation, identifies capacity bottlenecks, and generates explainable, patient-level operational recommendations.

## Overview

Hospitals must coordinate beds, clinical staff, diagnostic equipment, and emergency capacity while responding to changing demand. This project provides a simulated environment for analyzing resource availability and exploring alternative allocation scenarios.

The system supports operational decision-making through resource coordination, optimization, forecasting, and What-If simulation, with human decision-makers retaining final authority.

## Key Features

- **Hospital Resource Management:** Manage and monitor beds, ICU capacity, staff, and diagnostic equipment.
- **Patient Management:** Maintain patient and admission-related operational information.
- **Personalized Recommendations:** Generate patient-level resource allocation recommendations with reasons and expected operational impact.
- **What-If Simulation:** Explore hypothetical changes in patient demand, bed availability, staff availability, and equipment requirements.
- **Resource Optimization:** Use optimization techniques to evaluate allocation options under resource constraints.
- **Bottleneck Identification:** Highlight potential resource shortages and capacity constraints.
- **Human-in-the-Loop Decisions:** Keep recommendations subject to human review rather than automatic clinical decisions.
- **Authentication:** Provide registration, email OTP verification, and login functionality.
- **Alerts and Notifications:** Present operational alerts and notification information through the application dashboard.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React, Vite, JavaScript |
| UI Styling | CSS, Tailwind CSS (where implemented) |
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Validation | Pydantic |
| Optimization | Google OR-Tools (where implemented) |
| API Communication | REST APIs, Axios |
| Authentication | JWT, email OTP verification |
| Version Control | Git, GitHub |

## System Architecture

```text
React Frontend
      |
      | REST API Requests
      v
FastAPI Backend
      |
      +---- Authentication & Validation
      |
      +---- Hospital Resource Management
      |
      +---- Recommendation Services
      |
      +---- Optimization & What-If Simulation
      |
      v
PostgreSQL Database
```

## What-If Simulation Workflow

1. Configure a hypothetical hospital scenario.
2. Specify patient demand and changes in resource availability.
3. Submit the scenario to the backend API.
4. Calculate simulated resource allocation and identify potential bottlenecks.
5. Generate recommendations with reasons and expected impact.
6. Review the results without committing the hypothetical allocation to the database.

## Safety and Responsible Use

- This project focuses on hospital operations and resource coordination, not medical diagnosis or treatment.
- It does not prescribe medication or recommend clinical treatment.
- Synthetic or simulated data is intended for development and demonstration.
- Recommendations support operational review; authorized human decision-makers retain responsibility for real-world decisions.
- What-If simulation is intended to evaluate hypothetical scenarios and should not be treated as a substitute for a validated hospital management system.

## Local Setup

### Prerequisites

- Python and a virtual environment
- Node.js and npm
- PostgreSQL
- Git

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd hospital-resource-ai
```

### 2. Configure the backend

Activate or use the project's existing virtual environment and install the dependencies listed in the backend requirements file.

Create or update the environment configuration with your PostgreSQL connection string and other required application settings. Do not commit passwords, JWT secrets, email credentials, or other secrets to GitHub.

### 3. Start the backend

From the project root, run:

```powershell
.\venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

When the server is running, open:

- API documentation: `http://127.0.0.1:8000/docs`

### 4. Start the frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL displayed by Vite in your terminal.

## Project Status

This project is developed as a simulated hospital resource coordination system. Features should be evaluated against the current implementation and tested with synthetic data before being used in any operational environment.

## Future Improvements

- Expand automated unit and integration test coverage.
- Add role-based access control and audit trails for operational decisions.
- Improve optimization evaluation with measurable performance indicators.
- Add scenario comparison reports and resource utilization analytics.
- Strengthen deployment, monitoring, and security configuration.

## Disclaimer

This is an educational and software engineering project. It is not a certified clinical decision-support system and must not be used to make real-world patient care decisions.
