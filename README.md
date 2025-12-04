# Vortex

Vortex is a zero-configuration file sharing server for local networks. It lets
you quickly share files between devices on the same Wi-Fi network through a
clean, responsive web interface.

No accounts, no cloud, no complicated setup. Just run the command and share the
URL with anyone on your network.


## Features

- Zero configuration required - works out of the box
- Upload and download files from any device with a web browser
- No file size limits - streaming transfers handle files of any size
- HTTP Range support for video/audio seeking and resumable downloads
- Download entire directories as ZIP archives
- Parallel multi-file uploads with progress tracking
- Cross-platform: Windows, macOS, Linux
- Mobile-friendly responsive design
- No external dependencies - pure Python standard library


## Requirements

- Python 3.8 or higher


## Installation

Clone the repository and install in development mode:

```sh
git clone https://github.com/colvyn01/vortex.git
cd vortex
pip install -e .
```

Or install directly:

```sh
pip install .
```


## Quick Start

Start the server in the current directory:

```sh
vortex --start
```

The server will display a URL like `http://192.168.1.100:8000/` that you can
share with other devices on your network.

To stop the server:

```sh
vortex --stop
```


## Usage

### Command Reference

| Command | Description |
|---------|-------------|
| `vortex --start` | Start the server in the current directory |
| `vortex --start --dir PATH` | Share a specific directory |
| `vortex --start --port 3000` | Use a custom port (default: 8000) |
| `vortex --stop` | Stop the running server |
| `vortex --help` | Show all available options |

### Examples

Share your Downloads folder on port 3000:

```sh
vortex --start --dir ~/Downloads --port 3000
```

Share the current directory with default settings:

```sh
vortex --start
```

### Web Interface

Once the server is running, open the displayed URL in any web browser:

- Browse files and directories
- Click any file to download it
- Click "Download All" to get all files in the current directory as a ZIP
- Use the upload panel to send files to the server


## Updating

To update Vortex to the latest version:

```sh
cd vortex
git pull
pip install -e .
```

Or if installed without `-e`:

```sh
cd vortex
git pull
pip install .
```


## Security Considerations

Vortex is designed for trusted local networks only. Keep the following in mind:

- **No encryption**: All traffic is plain HTTP. Do not use over untrusted networks.
- **No authentication**: Anyone with the URL can access and upload files.
- **LAN only**: The server binds to all interfaces but is intended for local use.
- **Path protection**: Directory traversal attacks are blocked, but only serve
  directories you trust.

For use cases requiring security, consider running behind a reverse proxy with
HTTPS and authentication, or use a different tool designed for public networks.


## Project Structure

```
vortex/
  src/
    __init__.py      # Package exports and version
    cli.py           # Command-line interface
    server.py        # HTTP server and request handler
    ui.py            # HTML template rendering
    upload.py        # Multipart upload parsing
    utils.py         # Utility functions
    constants.py     # Configuration constants
    styles.py        # CSS stylesheet
    scripts.py       # JavaScript for uploads
  vortex.py          # Entry point
  pyproject.toml     # Package configuration
  LICENSE            # MIT License
  README.md          # This file
```


## License

MIT License. See [LICENSE](LICENSE) for details.
