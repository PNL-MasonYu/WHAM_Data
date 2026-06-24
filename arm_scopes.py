from redpitaya_scpi import scpi
import argparse
import time

SIGLENT_PORT = 5025
RIGOL_PORT = 5555

DEFAULT_SCOPE_IPS = [
    "192.168.130.231",
    "192.168.130.78",
    "192.168.130.80",
    "192.168.130.81",
    "192.168.140.225",
    "192.168.140.228",
    "192.168.140.229",
    "192.168.140.230",
    "192.168.140.227",
    "192.168.140.251",
    "192.168.140.238",
    "192.168.140.150",
]

KNOWN_SCOPE_PORTS = {
    "192.168.140.227": SIGLENT_PORT,
    "192.168.140.238": SIGLENT_PORT,
    "192.168.140.150": SIGLENT_PORT,
    "192.168.130.231": RIGOL_PORT,
    "192.168.130.78": RIGOL_PORT,
    "192.168.130.80": RIGOL_PORT,
    "192.168.130.81": RIGOL_PORT,
    "192.168.140.225": RIGOL_PORT,
    "192.168.140.228": RIGOL_PORT,
    "192.168.140.229": RIGOL_PORT,
    "192.168.140.230": RIGOL_PORT,
    "192.168.140.251": RIGOL_PORT,
}


def candidate_ports(ip, forced_port=None):
    if forced_port is not None:
        return [forced_port]

    if ip in KNOWN_SCOPE_PORTS:
        return [KNOWN_SCOPE_PORTS[ip]]

    return [SIGLENT_PORT, RIGOL_PORT]


def arm_scope(ip, timeout=2.0, forced_port=None, settle_seconds=0.05):
    last_error = None

    for port in candidate_ports(ip, forced_port=forced_port):
        device = None
        try:
            device = scpi(ip, timeout=timeout, port=port)
            device.delimiter = '\n'

            device.tx_txt(":TRIGger:MODE NORMal")
            time.sleep(settle_seconds)

            device.tx_txt("TRIG:RUN")
            time.sleep(settle_seconds)

            device.tx_txt(":RUN")
            time.sleep(settle_seconds)

            print(f"OK {ip}:{port} -> :TRIGger:MODE NORMal, RUN")
            return True, port, None
        except Exception as error:
            last_error = error
        finally:
            if device is not None:
                try:
                    device.close()
                except Exception:
                    pass

    return False, None, last_error


def parse_args():
    parser = argparse.ArgumentParser(
        description="Arm scopes by forcing Trigger Mode NORMal and RUN state."
    )
    parser.add_argument(
        "ips",
        nargs="*",
        help="Scope IPs to arm. If omitted, uses built-in default scope list.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Force a single SCPI port for all IPs (e.g., 5025 or 5555).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="Socket timeout in seconds for each scope connection.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    ips = args.ips if args.ips else DEFAULT_SCOPE_IPS

    print(f"Arming {len(ips)} scope(s)...")

    successes = 0
    failures = 0

    for ip in ips:
        ok, port, error = arm_scope(
            ip,
            timeout=args.timeout,
            forced_port=args.port,
        )
        if ok:
            successes += 1
        else:
            failures += 1
            print(f"FAIL {ip}: {error}")

    print(f"Done. Success: {successes}, Fail: {failures}")


if __name__ == "__main__":
    main()
