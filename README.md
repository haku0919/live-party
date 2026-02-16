<div align="center">

  # 🎮 Live Party
  
  **실시간 게임 파티 매칭 & 채팅 플랫폼**
  <br>
  *기다림 없는 매칭, 끊김 없는 소통.*

  <br>

  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white">
  <img src="https://img.shields.io/badge/Django_Channels-092E20?style=for-the-badge&logo=django&logoColor=white">
  <br>
  <img src="https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white">
  <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white">
  
</div>

<br>

## 📸 Preview
![Main Screen](https://via.placeholder.com/800x400?text=Place+Your+Screenshot+Here)

<br>

## 📝 Introduction
**Live Party**는 게이머들이 원하는 조건의 팀원을 **실시간(Real-time)**으로 찾고, 즉시 대화를 나누며 게임을 시작할 수 있도록 돕는 웹 애플리케이션입니다. 

Django Channels와 WebSocket 기술을 활용하여 **페이지 새로고침 없이** 파티 생성부터 모집, 채팅, 게임 시작까지의 모든 과정을 끊김 없이 제공합니다.

<br>

## ✨ Key Features

| Feature | Description | Tech Key |
| :--- | :--- | :---: |
| **⚡️ Live Lobby** | 웹소켓을 통해 파티 생성, 삭제, 인원 변동이 **실시간**으로 반영됩니다. | `WebSocket` |
| **💬 Private Chat** | 파티원들만 입장 가능한 **비공개 실시간 채팅방**을 제공합니다. | `Channels` |
| **🎙️ Custom Matching** | 마이크 사용 여부, 게임 모드, 티어 등을 고려한 **정밀 매칭**을 지원합니다. | `MySQL` |
| **👑 Party Management** | 방장은 비매너 유저를 **강퇴**하거나 차단(Blacklist)할 수 있습니다. | `Signals` |

<br>

## 📂 Project Structure
```bash
live-party
├── 📂 accounts           # 유저 인증, 프로필 관리, 어댑터
├── 📂 chat               # 실시간 채팅 (Consumers, Routing)
├── 📂 core               # 메인 로비, 공통 템플릿, 가이드
├── 📂 parties            # 파티 생성/참가 로직, 시그널(Signals)
├── 📂 websocket_project  # 설정(Settings), ASGI/WSGI
└── 📜 manage.py