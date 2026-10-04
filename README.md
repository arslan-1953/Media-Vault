# Media-Vault
A cross-platform PyQt6 desktop application for encrypting images and videos into secure vault containers with built-in media playback and extraction.
## 🛠️ Prerequisites & Installation

This application requires Python 3.8+ and the following external libraries:
### Install Dependencies

Run the following command in your terminal or command prompt to install all required dependencies:

```bash
pip install PyQt6 PyQt6-Multimedia cryptography


* **[PyQt6](https://pypi.org/project/PyQt6/)** — Desktop GUI framework for user interface components, layouts, and SVG icon rendering.
* **[PyQt6-Multimedia](https://pypi.org/project/PyQt6-Multimedia/)** — Provides video rendering (`QVideoWidget`) and audio controls (`QMediaPlayer`) for in-app media viewing.
* **[cryptography](https://pypi.org/project/cryptography/)** — Secure key derivation using PBKDF2-HMAC-SHA256 (200,000 iterations) and 256-bit Fernet AES file encryption.

> **Note:** Standard library modules (`sys`, `os`, `json`, `base64`) come pre-installed with Python.

