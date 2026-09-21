# tablo-web

[![CI](https://img.shields.io/github/actions/workflow/status/trevor-viljoen/tablo-web/ci.yml?branch=main&label=CI&style=flat-square)](https://github.com/trevor-viljoen/tablo-web/actions/workflows/ci.yml)
[![Latest Release](https://img.shields.io/github/v/release/trevor-viljoen/tablo-web?style=flat-square)](https://github.com/trevor-viljoen/tablo-web/releases)
[![Top Language](https://img.shields.io/github/languages/top/trevor-viljoen/tablo-web?style=flat-square)](https://github.com/trevor-viljoen/tablo-web)
[![Language Count](https://img.shields.io/github/languages/count/trevor-viljoen/tablo-web?style=flat-square)](https://github.com/trevor-viljoen/tablo-web)
[![Repo Size](https://img.shields.io/github/repo-size/trevor-viljoen/tablo-web?style=flat-square)](https://github.com/trevor-viljoen/tablo-web)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)

> **Warning**  
> This is an unofficial web interface for Tablo devices. It is not affiliated with Nuvyyo Inc. or Tablo. Use at your own risk.

A modern, responsive web application for your Tablo (Gen 4) devices. Built with React, TypeScript, FastAPI, and FFmpeg for seamless live TV streaming and library management.

> **This is a fork** of [trevor-viljoen/tablo-web](https://github.com/trevor-viljoen/tablo-web)
> adding three things: [transcode quality settings](#transcode-quality), support for
> [Docker secrets](#credentials), and a fix for accounts with
> [more than one Tablo](#choosing-a-device).

---

## Screenshots

| Live TV | TV Guide |
|---|---|
| ![Live TV](docs/screenshots/live-tv.png) | ![TV Guide](docs/screenshots/guide.png) |

| Login | Profile |
|---|---|
| ![Login](docs/screenshots/login.png) | ![Profile menu](docs/screenshots/profile-menu.png) |

---

## Features

- **Live TV Streaming:** Smart transcoding (via FFmpeg) for high-compatibility browser playback.
- **Traditional Guide:** A full timeline/grid view of upcoming programs.
- **Library Management:** Browse and watch your recordings directly in the browser.
- **Auto-Discovery:** Automatically finds and connects to your Tablo devices on the local network.
- **Plex & Jellyfin Live TV:** HDHomeRun emulation — add tablo-web as a Live TV tuner in Plex or Jellyfin with full XMLTV EPG.
- **Containerized:** Easy deployment using Docker or Podman, with pre-built images on GHCR.

---

## Prerequisites

- **Tablo Gen 4 Device** (with an active account).
- **Docker** or **Podman** with **Docker Compose / Podman Compose**.
- **FFmpeg** (included in the backend container).

---

## Quick Start

### Option A — Pre-built images (recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/trevor-viljoen/tablo-web.git
   cd tablo-web
   ```

2. **Launch the stack:**
   ```bash
   # Using Docker
   docker-compose up -d

   # Using Podman
   podman-compose up -d
   ```

3. **Access the app:**
   Open `http://localhost:7070` in your browser.

4. **Login:**
   Use your Tablo account email and password to authenticate.

### Option B — Build from source

```bash
# Using Docker
docker-compose up -d --build

# Using Podman
podman-compose up -d --build
```

> **Local Dockerfile tweaks:** create a `docker-compose.override.yml` to test changes before committing — it is gitignored and automatically merged by Compose.

---

## Plex & Jellyfin Live TV

tablo-web exposes an HDHomeRun-compatible tuner interface so Plex and Jellyfin can use your Tablo as a Live TV source with a full multi-day EPG.

### Plex

1. Go to **Settings → Live TV & DVR → Set Up Plex DVR**.
2. Plex will auto-discover the tuner at `http://<host>:7070`. If not, enter it manually.
3. EPG data loads automatically — no Gracenote subscription needed.

### Jellyfin

1. Go to **Dashboard → Live TV → Add Tuner Device** → choose **M3U Tuner**.
   - URL: `http://<host>:7070/api/iptv/playlist.m3u`
2. Go to **Dashboard → Live TV → Add TV Guide Data Provider** → choose **XMLTV**.
   - URL: `http://<host>:7070/api/iptv/epg.xml`
3. Refresh guide data and browse **Live TV**.

> See [GitHub Issues](https://github.com/trevor-viljoen/tablo-web/issues) for known limitations with OTT channels and EPG matching.

---

## Configuration

All of these are environment variables on the `backend` service. The shipped
`docker-compose.yml` lists them with the defaults.

### Transcode quality

The browser player has to re-encode, because no browser decodes MPEG-2 video
or AC-3 audio — which is what over-the-air broadcast actually is. That
re-encode is the only place picture quality can be lost, and upstream's
settings target low CPU: `-preset ultrafast -crf 28 -maxrate 2000k`. Broadcast
1080i is 12–19 Mbit/s, so squeezing it to 2 Mbit/s is why a browser stream can
look softer than the same channel on a TV.

| Variable | Default | Upstream | Notes |
|---|---|---|---|
| `TABLO_CRF` | `21` | 28 | Quality. Lower is better; ~18 is visually lossless. Each −6 roughly doubles the bitrate. |
| `TABLO_PRESET` | `veryfast` | ultrafast | Slower presets get more quality per bit, at more CPU. |
| `TABLO_MAXRATE` | `8000k` | 2000k | Ceiling. Raise for quality, lower for a thin network link. |
| `TABLO_BUFSIZE` | `16000k` | 4000k | Rate-control window; conventionally 2× `TABLO_MAXRATE`. |
| `TABLO_DEINTERLACE` | `0` | 0 | yadif mode. `1` emits a frame per field (~59.94 fps, smoother motion) for roughly double the CPU. |
| `TABLO_AUDIO_BITRATE` | `192k` | 128k | |
| `TABLO_AUDIO_CHANNELS` | `2` | 2 | The source is 5.1; browsers handle multichannel AAC inconsistently, so stereo is the safe default. |

Measured on a 1080i CBS feed, the defaults above produce **6.9 Mbit/s** against
upstream's 2.0 Mbit/s cap, at 1920×1080 with 192 kbit/s stereo audio.

**None of this affects the IPTV endpoint**, which is a straight `-c copy` — VLC,
Plex and Jellyfin receive the broadcast unmodified, so they are always better
than the browser player and cost almost no CPU. If picture quality matters more
than watching in a tab, point VLC at `http://<host>:7070/api/iptv/playlist.m3u`.

### Credentials

By default the email and password are saved to `/data/config.json` in plain
text. To keep the password out of that file — and out of `docker-compose.yml` —
supply it as a Docker secret:

```yaml
services:
  backend:
    environment:
      - TABLO_EMAIL=you@example.com
      - TABLO_PASSWORD_FILE=/run/secrets/tablo_password
    secrets:
      - tablo_password

secrets:
  tablo_password:
    file: ./secrets/tablo_password
```

Write the secret by typing it, not from the clipboard — if you copied the
command above to run it, the clipboard holds the *command*, and `pbpaste`
would write that into the file:

```bash
read -rs -p "Tablo password: " pw && printf '%s' "$pw" > secrets/tablo_password
unset pw && chmod 600 secrets/tablo_password
```

Resolution order is `TABLO_PASSWORD_FILE` → `/run/secrets/tablo_password` →
`TABLO_PASSWORD`. A password that arrives by any of these is used but never
written to `config.json`. A password already stored by an earlier version keeps
working, so upgrading does not log you out.

### Choosing a device

If the account has exactly one Tablo, it is selected automatically. If it has
more than one, the backend cannot guess, and every request fails with
`No active device` — which surfaces as a 502 and looks like a broken login.
Name the one you want:

```yaml
      - TABLO_SID=SID_5087B8546D56   # or any unique suffix, e.g. 5087B8546D56
```

The device picker in the UI still works; this just makes the choice survive a
restart.

---

## Architecture

- **Frontend:** React + Vite + Tailwind CSS + hls.js.
- **Backend:** FastAPI (Python) + FFmpeg for transcoding + [tablo-api](https://github.com/trevor-viljoen/tablo-api).
- **Proxy:** Nginx handles routing between the frontend and backend containers.

---

## Security

- This application proxies sensitive requests to your local Tablo device.
- Credentials (email/password) are stored locally in a `data/config.json` volume and are only used for authentication with the Tablo cloud API.
- To avoid storing the password at all, supply it as a Docker secret — see [Credentials](#credentials).
- Live streams are proxied and transcoded locally on your server.

---

## Reporting Bugs

If you encounter a bug, please follow these steps to help us diagnose the issue:

1. **Generate a debug report** — click the profile icon in the top-right corner of the app, then choose **Download Debug Report**. This creates a `tablo-debug-<timestamp>.json` file containing server diagnostics and browser info. It contains no passwords or personal information.

2. **Open an issue** on [GitHub Issues](https://github.com/trevor-viljoen/tablo-web/issues) and include:
   - A clear description of what happened and what you expected.
   - Steps to reproduce the issue.
   - Your browser and OS version.
   - The debug report JSON file attached to the issue.

3. **Browser console logs** — if the app shows an error, open your browser's developer tools (F12), go to the **Console** tab, and copy any red error messages into the issue.

---

## Support & Donations

If you find this project useful and would like to support its development, you can buy me a coffee!

[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/trevorviljoen)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsors-EA4AAA?style=for-the-badge&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/trevor-viljoen)

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

> Tablo and the Tablo logo are trademarks of Nuvyyo Inc.
marks of Nuvyyo Inc.
