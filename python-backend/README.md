# Gemini Conversational AI Python Backend

This directory contains the Python backend for the Gemini Conversational AI application. It is a FastAPI server responsible for handling business logic, processing AI tasks, and managing database interactions.

## Overview

The backend is built with:
- FastAPI for the web server and API endpoints.
- Google Generative AI SDK (`google-genai`) to interact with Gemini models.
- Supabase for database access and JWT verification.

It provides endpoints for text generation, audio processing, image analysis, and chat history management.

## Directory Structure

- **`api/`**: Contains the FastAPI route handlers for different API endpoints.
- **`services/`**: Business logic for services like Text-to-Speech (TTS) and Speech-to-Text (STT).
- **`tools/`**: Defines tools that can be used by the Gemini model.
- **`utils/`**: Utility functions for common tasks like audio processing and model interactions.
- **`personas/`**: Contains persona files (e.g., `aria.txt`) that define the system prompts for the AI. This folder is in `.gitignore` and needs to be created manually.

## Main Documentation

For a complete project overview, architecture details, and full setup instructions, please see the [main README.md file](../../README.md) in the root directory.
