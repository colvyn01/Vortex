# Vortex - Local File Gateway

Vortex is a modern, production-ready file sharing server for local networks. Share files instantly between any devices on the same WiFi network without configuration, cloud services, or external dependencies.

## Overview

Vortex is designed for users who need to quickly and reliably share files across devices on a trusted local network. Whether you're transferring files between your laptop, phone, and tablet, or sharing files with colleagues in the same office, Vortex provides a simple, secure, and fast solution.

**Built with:** Python standard library only (no external dependencies)
**Supports:** Python 3.8+
**Platforms:** Windows, macOS, Linux
**License:** MIT

## Key Features

- **Zero Configuration** - Works out of the box with no setup required
- **Universal Access** - Open any web browser to upload, download, and manage files
- **No File Limits** - Stream files of any size without loading into memory
- **Mobile Friendly** - Fully responsive design works seamlessly on phones and tablets
- **Parallel Uploads** - Upload multiple files simultaneously with real-time progress tracking
- **Batch Download** - Download entire directories as ZIP archives
- **HTTP Range Support** - Resume interrupted downloads and seek in video/audio streams
- **Cross Platform** - Same interface and functionality on Windows, macOS, and Linux
- **No Dependencies** - Uses Python standard library only—no external packages to install
- **Security Ready** - Optional HTTPS, token authentication, and rate limiting for public networks

## Requirements

- Python 3.8 or higher
- pip (Python package installer)
- Git (for cloning the repository)

Optional: OpenSSL (required for HTTPS support on Windows)

## Installation

### Using Git (Recommended)

```bash
git clone https://github.com/colvyn01/vortex.git
cd vortex
pip install -e .
```

The `-e` flag installs Vortex in editable mode, so changes to the source code are reflected immediately.

### Direct Installation

```bash
cd vortex
pip install .
```

### Verify Installation

```bash
vortex --help
```

This should display the available commands and options.

## Quick Start

### Starting the Server

Open a terminal and run:

```bash
vortex --start
```

The server will start in the current directory and display a URL like:

```
Vortex active
Serving directory: /Users/you/Desktop
Share this on your network: http://192.168.1.100:8000
Max concurrent connections: 10
Press Ctrl+C to stop.
```

Copy this URL and open it in any web browser on another device connected to the same WiFi network. You can now upload and download files.

### Stopping the Server

```bash
vortex --stop
```

### Basic Examples

Share your current directory (default):
```bash
vortex --start
```

Share a specific directory:
```bash
vortex --start --dir ~/Downloads
```

Use a custom port (useful if port 8000 is already in use):
```bash
vortex --start --port 3000
```

Combine options:
```bash
vortex --start --dir ~/Documents --port 9000
```

## Advanced Usage

### Network Address Selection

The `--mode` flag controls how Vortex detects and displays the network address:

```bash
vortex --start --mode auto
```

**Modes:**
- `auto` (default) - Automatically detects your LAN IP address. Falls back to localhost if no LAN is available.
- `localhost` - Binds to 127.0.0.1 (localhost only). Use this to restrict access to the local machine.
- `lan` - Requires a LAN IP address. Fails if no LAN network is detected.

Example:
```bash
vortex --start --mode localhost  # Only accessible from this computer
vortex --start --mode lan        # Only works if on a local network
```

### Secure Mode (Public Networks)

For use on public or untrusted networks, enable security features:

#### Token Authentication

Add token-based authentication to restrict access:

```bash
vortex --start --secure
```

The server will generate a unique token and display it:

```
Vortex active
Authentication enabled. Access token: a1b2c3d4e5f6g7h8
Share this on your network: http://192.168.1.100:8000?token=a1b2c3d4e5f6g7h8
```

**How it works:**
- The token persists to `~/.vortex/token.txt` across server restarts
- Clients must include the token in the URL query string: `?token=a1b2c3d4e5f6g7h8`
- Alternatively, include the token in the HTTP header: `X-Token: a1b2c3d4e5f6g7h8`
- Requests without a valid token receive a 403 Unauthorized error

**Regenerate Token:**
```bash
vortex --start --secure --new-token
```

This generates a new token and saves it to `~/.vortex/token.txt`. The new token is required for all future connections.

#### HTTPS (Encrypted Connections)

Enable HTTPS with a self-signed certificate:

```bash
vortex --start --https
```

The server will generate a self-signed certificate and display:

```
Vortex active
HTTPS enabled. Your browser will show a security warning -
this is normal for local servers using self-signed certificates.
Share this on your network: https://192.168.1.100:8000
```

**How it works:**
- The certificate is generated once and stored in `~/.vortex/certificate.pem`
- Subsequent restarts reuse the same certificate
- Your browser will display a security warning (expected and safe for local networks)
- Traffic is encrypted even though the certificate is not from a trusted authority
- Requires OpenSSL to be installed (see below)

**OpenSSL Installation:**

- **macOS:** `brew install openssl`
- **Linux:** `sudo apt-get install openssl` (Debian/Ubuntu) or equivalent for your distribution
- **Windows:** Download from [slproweb.com/products/Win32OpenSSL.html](https://slproweb.com/products/Win32OpenSSL.html)

#### Rate Limiting

Rate limiting is automatically enabled to protect against abuse:

```
Rate limiting: 200 requests/minute per IP
```

This threshold is set automatically and cannot be changed via CLI flags. It's designed to:
- Prevent brute force attacks
- Protect against accidental DoS
- Allow normal file sharing to work without interruption (200 requests/minute is generous)

If an IP exceeds the limit, requests receive a 429 Too Many Requests error.

### Combining Security Options

For maximum security on public networks:

```bash
vortex --start --https --secure
```

This enables:
- HTTPS encryption (encrypted connection)
- Token authentication (access control)
- Rate limiting (automatic protection against abuse)

Output:
```
Vortex active
HTTPS enabled. Your browser will show a security warning -
this is normal for local servers using self-signed certificates.
Token authentication ENABLED
Access URL: https://192.168.1.100:8000?token=a1b2c3d4e5f6g7h8
Share this access token with authorized users only.
Max concurrent connections: 10
```

## Command Reference

```
vortex --start [OPTIONS]           Start the file sharing server
  --dir PATH                       Directory to serve (default: current directory)
  --port NUMBER                    Port to listen on (default: 8000)
  --mode [auto|localhost|lan]      Address detection mode (default: auto)
  --https                          Enable HTTPS with self-signed certificate
  --secure                         Enable token-based authentication
  --new-token                      Generate a new authentication token

vortex --stop                      Stop the running server

vortex --help                      Show this help message

vortex --version                   Show version information
```

## Web Interface

Once the server is running, open the displayed URL in your browser. The interface provides:

### File Browsing
- Navigate through directories
- View file sizes and modification dates
- Parent directory link (..) to move up one level

### Downloading Files
- Click any file name to download it
- Use "Download All" button to download the entire current directory as a ZIP file

### Uploading Files
- Use the "Choose files" button to select files
- Select multiple files at once
- Click "Send" to upload
- Real-time progress bar shows upload status
- Uploaded files appear immediately in the file list

## Performance Characteristics

- **Concurrent Uploads:** Up to 4 parallel uploads per browser session
- **File Size:** No practical limit (streamed, not buffered)
- **Network Speed:** Limited by your WiFi connection speed, not Vortex
- **Mobile:** Optimized for iOS and Android devices; tested on iPhone Safari and Chrome Mobile
- **Memory:** Constant memory usage regardless of file size (streaming implementation)

## Security Considerations

### Trusted Networks Only

Vortex is designed for trusted local networks. By default, it provides:

- **No encryption** - All traffic is plain HTTP unless `--https` is used
- **No authentication** - Anyone with the URL can upload and download files
- **No authorization** - All files in the served directory are accessible

**Use cases requiring enhanced security:**

1. **Public WiFi Networks** - Use `--https` and `--secure` flags together
2. **Untrusted Guests** - Use `--secure` flag to require token authentication
3. **Sensitive Data** - Consider encrypting files before sharing or using a different tool
4. **Production Deployment** - Run behind a reverse proxy (nginx, Apache) with professional HTTPS certificates

### Best Practices

- Only serve directories containing files you're comfortable sharing
- Monitor the server while it's running on untrusted networks
- Regenerate the token periodically with `--new-token`
- Use strong WiFi passwords to limit network access
- Disable the server when not actively sharing files

## Project Structure

```
vortex/
├── src/
│   ├── __init__.py           Package initialization
│   ├── cli.py                Command-line interface and main entry point
│   ├── server.py             HTTP server, request handler, and core server logic
│   ├── upload.py             Multipart form data parsing for file uploads
│   ├── ui.py                 HTML template rendering for web interface
│   ├── styles.py             CSS stylesheet (embedded in HTML)
│   ├── scripts.py            JavaScript for upload progress tracking
│   ├── utils.py              Utility functions (path validation, sanitization)
│   ├── constants.py          Configuration constants and MIME type mappings
│   └── security.py           Security features (rate limiting, auth, HTTPS)
├── vortex.py                 Entry point script
├── pyproject.toml            Package configuration and metadata
├── LICENSE                   MIT License
└── README.md                 This file
```

## Configuration Files

Vortex stores security-related data in the user's home directory:

- `~/.vortex/token.txt` - Authentication token (created with `--secure` flag)
- `~/.vortex/certificate.pem` - Self-signed certificate and private key (created with `--https` flag)

These directories and files are created automatically when needed. You can delete them to reset security settings.

## Troubleshooting

### Port Already in Use

**Error:** `Address already in use`

**Solution:** Use a different port:
```bash
vortex --start --port 9000
```

### Cannot Access from Another Device

**Possible causes:**
1. Device not on the same WiFi network
2. Firewall blocking port 8000
3. Using `--mode localhost` (restricts to local access)

**Solution:**
```bash
vortex --start --mode auto  # Ensures LAN IP is used
```

### Firewall Permission (First Run)

**On macOS/Windows:** You may see a firewall permission prompt. Click "Allow" to permit network access.

### OpenSSL Not Found (HTTPS)

**Error:** `OpenSSL not found`

**Solution:**
- **macOS:** `brew install openssl`
- **Linux:** `sudo apt-get install openssl`
- **Windows:** Download from [slproweb.com/products/Win32OpenSSL.html](https://slproweb.com/products/Win32OpenSSL.html)

### Browser Shows Security Warning (HTTPS)

This is expected with self-signed certificates. Click "Proceed anyway" or "Accept risk" to continue. The connection is encrypted.

### Slow Performance

**Possible causes:**
1. WiFi interference or weak signal
2. Large file size
3. Multiple parallel uploads

**Optimization:**
- Get closer to the WiFi router
- Upload files one at a time
- Check your WiFi connection speed with a speed test

### iPhone Freezes When Selecting Many Files

This was fixed in recent versions. If you experience this:
1. Update to the latest version: `pip install --upgrade vortex`
2. Try selecting fewer files at once (file selection is batched automatically for >10 files)

## Updating

### From Git

```bash
cd vortex
git pull
pip install -e .
```

### From Package

```bash
pip install --upgrade vortex
```

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues, questions, or feature requests, visit the GitHub repository:
https://github.com/colvyn01/vortex

## License

Vortex is released under the MIT License. See the LICENSE file for full details.

## About

Vortex was created to solve a simple problem: quickly sharing files between devices on a local network without dealing with cloud services, complex setup, or unnecessary dependencies.

The project prioritizes simplicity, reliability, and performance while maintaining zero external dependencies—using only Python's standard library for maximum portability and ease of installation.

**Version:** 1.0.0  
**Python:** 3.8+  
**Status:** Production Ready

---

**Last Updated:** December 2025
