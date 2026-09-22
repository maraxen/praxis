# Browser Mode Installation

Browser Mode is the simplest way to get started with Praxis. It runs entirely within your web browser using [Pyodide](https://pyodide.org/) (Python in WASM) and [WebSerial](https://developer.mozilla.org/en-US/docs/Web/API/Web_Serial_API)/[WebUSB](https://developer.mozilla.org/en-US/docs/Web/API/WebUSB_API) for hardware communication.

## Zero Setup (Online)

You can visit our hosted instance to evaluate Praxis immediately:

[**Launch Praxis Browser Mode**](https://praxis.pylabrobot.org)

## Local Setup

If you want to run the browser client from your own machine:

### Prerequisites

- **Node.js 20+**

### Steps

1. **Clone the Repository**

   ```bash
   git clone https://github.com/maraxen/praxis.git
   cd praxis
   ```

2. **Install Frontend Dependencies**

   ```bash
   cd praxis/web-client
   bun install
   ```

3. **Start Browser Mode**

   ```bash
   bun run start:browser
   ```

4. **Access Praxis**
   Open [http://localhost:4200](http://localhost:4200) in a modern browser (Chrome or Edge recommended for WebSerial/WebUSB support).

## Key Features

- **No Backend**: No Python, PostgreSQL, or Redis required on your host.
- **Hardware Control**: Direct control of USB/Serial lab robots.
- **Portability**: Perfect for field research or quick demonstrations.
