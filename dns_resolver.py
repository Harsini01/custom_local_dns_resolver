# -*- coding: utf-8 -*-
"""
Created on Tue Mar 18 16:20:21 2025

@author: harsi
"""

import socket
import threading
import time
from dnslib import DNSRecord
from concurrent.futures import ThreadPoolExecutor

# Upstream DNS server (Cloudflare DNS)
UPSTREAM_DNS = "1.1.1.1"
UPSTREAM_PORT = 53
CACHE_TTL = 60  # Cache time-to-live in seconds

# Dictionary to store cache entries manually
cache = {}
lock = threading.Lock()

# Thread pool for better resource management
executor = ThreadPoolExecutor(max_workers=10)

def resolve_upstream(query_data):
    """Forwards the DNS request to the upstream DNS server via UDP."""
    upstream_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    upstream_socket.settimeout(3)  # Added timeout to prevent hanging connections
    try:
        upstream_socket.sendto(query_data, (UPSTREAM_DNS, UPSTREAM_PORT))
        response_data, _ = upstream_socket.recvfrom(512)
    except socket.timeout:
        print("[TIMEOUT] Upstream DNS server did not respond in time.")
        return b""  # Empty response to avoid crashes
    finally:
        upstream_socket.close()
    return response_data


def resolve_upstream_tcp(query_data):
    """Fallback to TCP for large DNS responses."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
        tcp_socket.settimeout(3)
        try:
            tcp_socket.connect((UPSTREAM_DNS, 53))
            tcp_socket.send(b"\x00" + bytes([len(query_data)]) + query_data)
            response_data = tcp_socket.recv(4096)
            return response_data[2:]  # Remove TCP prefix
        except Exception as e:
            print(f"[TCP FALLBACK ERROR] {e}")
            return b""

def get_cached_response(query_key):
    """Checks if a query response is in cache and still valid."""
    with lock:
        if query_key in cache:
            response, timestamp = cache[query_key]
            if time.time() - timestamp < CACHE_TTL:
                print(f"[CACHE HIT] Returning cached response for {query_key}")
                return response
            else:
                print(f"[CACHE EXPIRED] Removing {query_key} from cache")
                del cache[query_key]
    return None

def cache_response(query_key, response_data):
    """Stores the DNS response in cache."""
    with lock:
        cache[query_key] = (response_data, time.time())
        print(f"[CACHE STORE] Cached response for {query_key}")

def handle_dns_request(data, client_addr, server_socket):
    try:
        start_time = time.time()  # Start timing

        dns_request = DNSRecord.parse(data)
        query_key = str(dns_request.q)
        print(f"Received DNS request: {dns_request.q}")

        # Check if response is in cache
        cached_response = get_cached_response(query_key)
        if cached_response:
            elapsed_time = time.time() - start_time
            print(f"[CACHE HIT] Response time: {elapsed_time:.6f} seconds")
            server_socket.sendto(cached_response, client_addr)
            return

        # Fetch from Cloudflare (start new timing for upstream query)
        upstream_start_time = time.time()
        response_data = resolve_upstream(data)
        if not response_data:  # Attempt TCP fallback if UDP fails
            response_data = resolve_upstream_tcp(data)
        
        if response_data:
            upstream_elapsed_time = time.time() - upstream_start_time
            print(f"[UPSTREAM QUERY] Response time: {upstream_elapsed_time:.6f} seconds")
            
            cache_response(query_key, response_data)
            server_socket.sendto(response_data, client_addr)

    except ConnectionResetError as e:
        print(f"[CONNECTION RESET] Client forcibly closed connection: {e}")
    except Exception as e:
        print(f"Error handling request from {client_addr}: {e}")

def dns_resolver():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(("127.0.0.1", 53))
    print("DNS Resolver with Caching is running on port 53")

    try:
        while True:
            try:
                data, client_addr = server_socket.recvfrom(512)
                executor.submit(handle_dns_request, data, client_addr, server_socket)
            except ConnectionResetError as e:
                print(f"[CONNECTION RESET] Client forcibly closed connection: {e}")
    except Exception as e:
        print(f"Error: {e}")

# Start the DNS resolver thread
resolver_thread = threading.Thread(target=dns_resolver, daemon=True)
resolver_thread.start()
