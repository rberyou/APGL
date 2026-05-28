# Product Design

## Goal

APGL helps individual self-learners turn a skill goal or learning material into an AI-guided learning loop: learn a small unit, answer checks, correct misunderstandings, and review weak points.

## MVP Audience

The first version targets personal self-learners using the product locally or in a single-user hosted setup. It does not include cohorts, teachers, enterprise reporting, community features, or mobile apps.

## Core Flow

1. User registers or logs in.
2. User creates a learning project from either a skill goal or uploaded material.
3. Backend creates a generation job.
4. AI generates knowledge points, lessons, and quiz items.
5. User studies a lesson and answers quiz prompts.
6. Incorrect answers become mistake records and review tasks.
7. Dashboard shows projects, due reviews, and weak points.

## MVP Inputs

- Skill goal: title, goal, current level, session time.
- Material: PDF, Markdown, or plain text.

## MVP Exclusions

- Video subtitles
- Web page ingestion
- Third-party login
- Multi-user teams or classrooms
- Mobile app or WeChat mini program
- Payments, pricing, or admin console

