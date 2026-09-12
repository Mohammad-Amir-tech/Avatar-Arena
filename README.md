<div align="center">

# ⚔️ AvatarArena

### Three AI avatars. One topic. Live debate in 20+ languages.

[![Live Demo](https://img.shields.io/badge/🌐_Live_Demo-avatar--arena.onrender.com-667eea?style=for-the-badge)](https://avatar-arena.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

<img src="screenshot.png" alt="AvatarArena Demo" width="800"/>

**Made by [Mohammad Amir](https://github.com/Mohammad-Amir-tech)**

</div>

---

## 🎯 What is AvatarArena?

AvatarArena is a **multi-agent AI debate platform** where three AI-powered avatars — **Alex (Pro)**, **Maya (Con)**, and a **Judge** — engage in structured, live debates on any topic you choose.

Unlike simple chatbots, AvatarArena creates **a real conversation** with distinct personalities, voices, and animated mouth movements — all in **20+ languages**.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎭 **3 AI Personalities** | Alex (optimistic), Maya (skeptical), Judge (neutral) |
| 🌍 **20+ Languages** | English, Hindi, Urdu, Bengali, Tamil, Telugu, Marathi, Spanish, French, Japanese & more |
| 🗣️ **Native Voices** | Each language uses its own native TTS voice (via Microsoft edge-tts) |
| 🎬 **Animated Avatars** | Real-time mouth movement synced with audio |
| 🎨 **Custom Avatars** | Upload your photo, set personality — join the debate! |
| ⚡ **Live Streaming** | SSE (Server-Sent Events) for word-by-word output |
| 🌓 **Dark/Light Mode** | Theme preference saved in localStorage |
| 📱 **Responsive** | Works on desktop, tablet, and mobile |

---

## 🚀 Live Demo

👉 **[https://avatar-arena.onrender.com](https://avatar-arena.onrender.com)**

> ⏱️ **Note:** Free tier sleeps after 15 min of inactivity. First load may take 30-50 seconds.

**Try these topics:**
- `AI in education` (English)
- `शिक्षा में AI` (Hindi)
- `تعلیم میں AI` (Urdu)
- `AI en la educación` (Spanish)

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** — Modern async Python web framework
- **Groq AI** (`openai/gpt-oss-120b`) — Free, ultra-fast LLM inference
- **edge-tts** — Microsoft neural text-to-speech (free, 20+ languages)
- **SQLite** — Persistent storage for custom avatars

### Frontend
- **Vanilla HTML/CSS/JS** — No framework, lightning fast
- **Web Audio API** — Real-time amplitude analysis for mouth animation
- **Server-Sent Events (SSE)** — Live streaming debate responses

---

## 🏗️ Architecture
