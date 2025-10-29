from zeroconf import Zeroconf, ServiceBrowser, ServiceListener
import socket
import time


class DeviceDiscovery(ServiceListener):
    def __init__(self):
        self.ip = None

    def add_service(self, zeroconf, service_type, name):
        info = zeroconf.get_service_info(service_type, name)
        if info and info.addresses:
            # Use zeroconf's built-in parser for IPs
            self.ip = info.parsed_addresses()[0]


def discover_soundtouch_ip():
    zeroconf = Zeroconf()
    listener = DeviceDiscovery()
    browser = ServiceBrowser(zeroconf, "_soundtouch._tcp.local.", listener)
    time.sleep(5)
    zeroconf.close()
    return listener.ip


# main.py
if __name__ == "__main__":
    ip = discover_soundtouch_ip()
    print(f"Bose SoundTouch IP: {ip}")
    # Use `ip` for further interactions
