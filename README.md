# SmartFridge Backend

This repository hosts the backend for the SmartFridge project, a student-built platform that ingests camera snapshots from a Raspberry Pi-powered fridge, enriches them with AI, and exposes the results to companion apps.

## Stack Overview

- **Flask** – Lightweight Python framework handling HTTP endpoints for image uploads, inventory queries, and business logic orchestration.
- **Caddy** – Front-door web server and reverse proxy that terminates TLS, handles automatic Let’s Encrypt certificates, and forwards requests to the Flask app.
- **Docker** – Containerizes the entire stack so the Raspberry Pi client and server share reproducible environments, simplifying deployment to a small cloud VPS.

## Project Goals

1. Receive and store fridge images uploaded from the Raspberry Pi.
2. Run AI-backed analysis (LLM/computer vision) on the images to identify items and status.
3. Serve REST endpoints that the mobile or web SmartFridge app can call for real-time updates and notifications.
4. Stay lean enough for student infrastructure: one VPS, Docker Compose, and a straightforward deployment pipeline.

## Status

The repository is at the initial scaffolding stage; code, Docker tooling, and deployment scripts will follow as the prototype solidifies.
