
import concurrent.futures
import ipaddress
import re
import socket
import urllib.request
from pathlib import Path

SOURCE_URL = (
    "https://raw.githubusercontent.com/"
    "NiREvil/vless/main/sub/ProxyIP-Daily.md"
)

OUTPUT = Path("proxy-ips.txt")
TIMEOUT = 2.5
MAX_WORKERS = 100


def download_source():
    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "ProxyIP-Daily-Monitor"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def extract_endpoints(content):
    # Match IPv4 addresses, optionally followed by a port.
    pattern = r'(?<![\d.])((?:\d{1,3}\.){3}\d{1,3})(?::(\d{1,5}))?(?![\d.])'
    endpoints = set()

    for ip, port in re.findall(pattern, content):
        try:
            ipaddress.IPv4Address(ip)
            port_number = int(port) if port else 443
            if 1 <= port_number <= 65535:
                endpoints.add((ip, port_number))
        except ValueError:
            continue

    return endpoints


def is_reachable(endpoint):
    ip, port = endpoint
    try:
        with socket.create_connection((ip, port), timeout=TIMEOUT):
            return ip
    except (OSError, TimeoutError):
        return None


def main():
    content = download_source()
    endpoints = extract_endpoints(content)

    if not endpoints:
        raise RuntimeError("Source contained no valid endpoints.")

    print(f"Testing {len(endpoints)} unique IP/port endpoints...")

    working_ips = set()
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as pool:
        for result in pool.map(is_reachable, endpoints):
            if result:
                working_ips.add(result)

    if not working_ips:
        raise RuntimeError(
            "No reachable proxies found; existing output preserved."
        )

    # Sort for stable output and predictable Git diffs.
    result = "\n".join(
        sorted(working_ips, key=lambda ip: tuple(
            int(part) for part in ip.split(".")
        ))
    ) + "\n"

    OUTPUT.write_text(result, encoding="utf-8")
    print(f"Reachable IPs saved: {len(working_ips)}")


if __name__ == "__main__":
    main()
