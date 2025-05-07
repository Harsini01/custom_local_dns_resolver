This project is a lightweight DNS resolver built in Python that supports caching and fallback to TCP for large responses. 
It acts as a local DNS server, forwarding client queries to Cloudflare's DNS (1.1.1.1) and caching the results to reduce redundant requests.

🔧 Features
✅ Resolves DNS queries over UDP

🗃️ In-memory cache with TTL (default: 60 seconds)

📉 Reduces DNS lookup times with cache hits

🧵 Handles multiple client requests using threads (via ThreadPoolExecutor)

🔁 Automatic TCP fallback for large DNS responses

🔐 Thread-safe cache access with locking

📍 Listens locally on 127.0.0.1:53
