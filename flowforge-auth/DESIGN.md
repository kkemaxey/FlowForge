# FlowForge — Design Doc (Project 1, initial stages)

**Team:** [team name] · **Members:** [list all contributing members]
**Author of this slice:** Brock Caston Jr. — Auth + Backend Support
**Version:** 0.1.0

> This is the *started* design doc required for Project 1: MVP, stack, API
> contract examples, and a features list. It focuses on the authentication /
> supervisor-role slice that this deliverable implements.

## Problem

Maria, a warehouse shift supervisor, runs the floor manually — walking the
aisles, radioing pickers, and hand-updating a spreadsheet. She only finds out
about late orders and empty bins *after* they have already put an order behind
schedule. FlowForge is a warehouse **control tower** that automates order intake,
task assignment, and live monitoring so she can react before an order misses its
window.

## Minimum Viable Product (MVP)

A supervisor can log in and see a live console where incoming orders have been
turned into pick tasks, tasks are assigned to workers, and bottlenecks/stockouts
are visible in real time, with the ability to reassign or expedite a task.

**MVP boundary for the auth slice (this deliverable):** a user can authenticate
with Firebase, the backend resolves whether they are a **supervisor**, and every
protected endpoint sits behind that check. Only supervisors may perform
supervisor actions.

## Tech Stack

- **Frontend:** Next.js + TypeScript (the console)
- **Backend:** FastAPI + Python
- **Database:** MySQL on Google Cloud SQL, via SQLAlchemy
- **Auth:** Firebase Authentication; the custom supervisor role is modeled in
  application code (not natively understood by Firebase)
- **Hosting:** Vercel (frontend) + Google Cloud Run (backend)

## API Contract Examples

### `POST /auth/login`
Verifies the Firebase token, assigns a role, records the login.

Request:
```
POST /auth/login
Authorization: Bearer <firebase-id-token>
```
Response `200 OK`:
```json
{
  "message": "Login recorded",
  "user": {
    "uid": "abc123",
    "email": "maria@flowforge.example",
    "role": "supervisor",
    "is_supervisor": true
  }
}
```
Errors: `401 Unauthorized` (missing/invalid token).

### `GET /auth/me`
Returns the current authenticated user and supervisor status.

Request:
```
GET /auth/me
Authorization: Bearer <firebase-id-token>
```
Response `200 OK`:
```json
{
  "uid": "abc123",
  "email": "maria@flowforge.example",
  "role": "supervisor",
  "is_supervisor": true
}
```
Errors: `401 Unauthorized` (missing/invalid token), `404 Not Found`
(authenticated but no user record yet — call `/auth/login` first).

## Features considered (not all in this deliverable)

- Firebase login + session handling
- Supervisor role check as reusable auth middleware behind every protected route
- Order intake → pick-task generation
- Task assignment / scheduling state machine
- Reassign and expedite a task
- Live console: throughput, work-in-progress, bottlenecks, stockouts
- Exception / event stream and metrics
- Worker (workforce) CRUD
- Request logging and audit of auth events

## Out of scope for Project 1

Full console UI, the complete assignment state machine, and real-time metrics —
this milestone delivers the authentication slice plus its two integrated
endpoints, database integration, and tests.
